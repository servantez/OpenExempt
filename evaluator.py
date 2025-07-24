import re
import numpy as np
from copy import deepcopy
from logging import Logger
from typing import List, Dict, Set
from rapidfuzz import process, fuzz
from langchain_core.exceptions import OutputParserException
from source.jurisdiction import Jurisdiction
from source.task_id import TaskID
from source.model_id import ModelID
from source.case import Case
from source.solver import Solver
from source.statute_set import StatuteSet
from source.pydantic_response import (
    Claim,
    ExemptionClassificationResponse, 
    ExemptionValuationResponse, 
    NonExemptAssetsResponse, 
    OptimalExemptionsResponse
    )


# The Evaluator class is responsible for evaluating model predictions on OpenExempt tasks.
# Note: evaluating solutions requires the statutes and cases used to generate the dataset.
class Evaluator:
    def __init__(self, statute_sets: List[StatuteSet]):
        self.statute_set_map = {statute_set.jurisdiction: statute_set for statute_set in statute_sets}
        self.solver = self._init_solver(statute_sets)
        self.citation_map = {statute_set.jurisdiction: statute_set.exemption_citations() for statute_set in statute_sets}
        self.normalized_citation_map = {
            jurisdiction: [citation.strip().lower() for citation in citations]
            for jurisdiction, citations in self.citation_map.items()
        }
        self.logger = None # Set to dataset logger at time of evaluation

    # This is the only method needed for evaluation - all evaluation logic is handled by evaluator.
    def evaluate(self, task_id: TaskID, predictions: List[Dict[str, str]], targets: List[Dict[str, str | Dict]], cases: List[Case], model_id: ModelID, logger: Logger):
        self.logger = logger
        assert len(predictions) == len(targets), f'Number of predictions ({len(predictions)}) and targets ({len(targets)}) must be the same.'
        assert len(targets) == len(cases), f'Number of targets ({len(targets)}) and cases ({len(cases)}) must be the same.'
        uid_sanity_check = all(prediction['uid'] == target['uid'] for prediction, target in zip(predictions, targets))
        assert uid_sanity_check, 'Prediction and target lists contain mismatched UIDs (prediction UID != target UID).'
        parsed_predictions = self._parse_predictions(predictions, task_id, model_id)
        extracted_targets = [target_dict['target'] for target_dict in targets]
        match task_id:
            case TaskID.ALLOWABLE_EXEMPTIONS:
                return self._evaluate_allowable_exemptions(parsed_predictions, extracted_targets)
            case TaskID.EXEMPTION_CLASSIFICATION:
                return self._evaluate_exemption_classification(parsed_predictions, extracted_targets)
            case TaskID.EXEMPTION_VALUATION:
                return self._evaluate_exemption_valuation(parsed_predictions, extracted_targets)
            case TaskID.NONEXEMPT_ASSETS:
                return self._evaluate_nonexempt_assets(parsed_predictions, extracted_targets)
            case TaskID.OPTIMAL_EXEMPTIONS:
                return self._evaluate_optimal_exemptions(parsed_predictions, extracted_targets, cases)
            case _:
                raise NotImplementedError(f'Evaluation not implemented for task ID: {task_id}')
            
    def _parse_predictions(self, predictions: List[Dict[str, str]], task_id: TaskID, model_id: ModelID):
        parser = task_id.response_parser()
        parsed_predictions = []
        for prediction_dict in predictions:
            parsed_prediction = prediction_dict['prediction']
            if model_id == ModelID.DEEPSEEK_R1: # Remove think tags
                parsed_prediction = re.sub(r'<think>.*?</think>', '', parsed_prediction, count=1, flags=re.DOTALL)
            if not parser: # No parsing needed
                parsed_predictions.append(parsed_prediction)
                continue
            try:
                parsed_prediction = parser.parse(parsed_prediction)
            except OutputParserException as parser_exception: # Invalid response format
                uid = prediction_dict['uid']
                self.logger.info(f'Encountered invalid response format for task: {uid}.')
                parsed_predictions.append(None)
            except Exception as exception: # Encountered an unexpected error
                raise exception
            else:
                parsed_predictions.append(parsed_prediction)
        return parsed_predictions
    
    def _init_solver(self, statute_sets: List[StatuteSet]):
        normalized_statute_sets = deepcopy(statute_sets)
        for statute_set in normalized_statute_sets:
            for exemption in statute_set.exemptions():
                exemption.citation = exemption.citation.strip().lower()
                if exemption.fallback_relationship:
                    exemption.fallback_relationship = exemption.fallback_relationship.strip().lower()
                if exemption.mutual_exclusion:
                    exemption.mutual_exclusion = exemption.mutual_exclusion.strip().lower()
        return Solver({statute_set.jurisdiction: statute_set for statute_set in normalized_statute_sets})
    
    # Parse comma-separated multi-label string into a set of labels
    def _parse_multi_label_string(self, label_string: str):
        labels = [label.strip() for label in label_string.split(',')]
        return set(filter(None, labels))
    
    def _precision_recall_f1_from_outcomes(self, tp: int, fp: int, fn: int):
        precision = tp / (tp + fp) if tp + fp > 0 else 0
        recall = tp / (tp + fn) if tp + fn > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if precision + recall > 0 else 0
        return precision, recall, f1
    
    def _compute_precision_recall_f1_scores(self, prediction: Set[str], target: Set[str]):
        normalized_prediction = set(label.strip().lower() for label in prediction)
        normalized_target = set(label.strip().lower() for label in target)
        tp = len(normalized_prediction & normalized_target)
        fp = len(normalized_prediction - normalized_target)
        fn = len(normalized_target - normalized_prediction)
        return self._precision_recall_f1_from_outcomes(tp, fp, fn)
        
    def _compute_precision_recall_f1_mare_scores(self, prediction: List[Claim], target: List[Claim]):
        # Calculate true positives, false positives, false negatives and relative errors
        tp, fp, fn = 0, 0, 0
        relative_errors = []
        target_map = {claim.normalized_citation: claim for claim in target}
        for predicted_claim in prediction:
            matching_claim, relative_error = self._find_matching_claim(predicted_claim, list(target_map.values()))
            if relative_error is not None: # Record relative error for all matching claims
                relative_errors.append(relative_error)
            if matching_claim and relative_error < 0.05:
                target_map.pop(matching_claim.normalized_citation)
                tp += 1
            else:
                fp += 1
        fn = len(target_map)
        # Calculate precision, recall, f1 and mean absolute relative error
        precision, recall, f1 = self._precision_recall_f1_from_outcomes(tp, fp, fn)
        mare = np.mean(relative_errors) if relative_errors else np.nan
        return precision, recall, f1, mare
    
    def _find_matching_asset_description(self, asset_description: str, candidates: List[str]):
        if not candidates:
            return None
        # If exact match exists, return asset description
        if asset_description in candidates:
            return asset_description
        # Use rapidfuzz to check for near identical asset description
        score_threshold = 90
        best_match, score, index = process.extractOne(asset_description, candidates, scorer=fuzz.partial_ratio)
        return best_match if score > score_threshold else None
    
    def _find_matching_claim(self, prediction: Claim, targets: List[Claim]):
        for target in targets:
            if prediction.normalized_citation == target.normalized_citation:
                return target, self._absolute_relative_error(prediction.claim_value, target.claim_value)
        return None, None
    
    # Compute absolute relative error with an epsilon constant to avoid division by zero
    # Relative error values explode for target values at or near zero
    # We address this limitation by setting epsilon to 1, allowing us to approximate absolute error for values at or near zero
    def _absolute_relative_error(self, prediction: float, target: float, epsilon: float = 1):
        if prediction == target:
            return 0.0
        return abs((prediction / (target + epsilon)) - 1.0)
    
    def _detect_jurisdiction(self, claim_map: Dict[str, List[Claim]], normalized: bool = False):
        # Jurisdiction is determined by first valid exemption citation
        citation_map = self.normalized_citation_map if normalized else self.citation_map
        for claims in claim_map.values():
            for claim in claims:
                for jurisdiction, citations in citation_map.items():
                    citation = claim.normalized_citation if normalized else claim.citation
                    if citation in citations:
                        return jurisdiction
        return None # No valid exemption citations
    
    def _case_asset_map_for_jurisdiction(self, case: Case, jurisdiction: Jurisdiction, normalized: bool = False):
        asset_map = {}
        citation_map = self.normalized_citation_map if normalized else self.citation_map
        jurisdiction_citations = citation_map[jurisdiction]
        for asset in deepcopy(case.assets):
            description = asset.description.strip().lower() if normalized else asset.description
            asset.description = description
            if normalized:
                asset.applicable_exemptions = [citation.strip().lower() for citation in asset.applicable_exemptions]
            asset.applicable_exemptions = [citation for citation in asset.applicable_exemptions if citation in jurisdiction_citations]
            asset_map[description] = asset
        return asset_map
        
    # Evaluate TaskID.ALLOWABLE_EXEMPTIONS
    def _evaluate_allowable_exemptions(self, predictions: List[str], targets: List[str]):
        prediction_sets = [self._parse_multi_label_string(prediction) for prediction in predictions]
        target_sets = [self._parse_multi_label_string(target) for target in targets]
        score_array = np.array([self._compute_precision_recall_f1_scores(prediction_set, target_set) for prediction_set, target_set in zip(prediction_sets, target_sets)])
        scores = score_array.mean(axis=0)
        precision, recall, f1 = scores
        return {'precision': float(precision), 'recall': float(recall), 'f1': float(f1)}
    
    # Evaluate TaskID.EXEMPTION_CLASSIFICATION
    def _evaluate_exemption_classification(self, predictions: List[ExemptionClassificationResponse], targets: List[Dict]):
        score_array = np.zeros((len(targets), 3)) # 3 columns for precision, recall, f1
        invalid_format_count = 0
        for sample_index, (prediction, target) in enumerate(zip(predictions, targets)):
            if prediction is None: # Invalid response format
                score_array[sample_index, :] = 0
                invalid_format_count += 1
                continue
            normalized_prediction = {key.strip().lower(): value for key, value in prediction.root.items()}
            normalized_target = {key.strip().lower(): value for key, value in target.items()}
            asset_score_array = np.zeros((len(normalized_target), 3))
            for asset_index, (asset_description, citations) in enumerate(normalized_target.items()):
                matching_asset_description = self._find_matching_asset_description(asset_description, list(normalized_prediction.keys()))
                if matching_asset_description is None:
                    asset_score_array[asset_index, :] = 0
                    continue
                predicted_citations = normalized_prediction[matching_asset_description]
                precision, recall, f1 = self._compute_precision_recall_f1_scores(set(predicted_citations), set(citations))
                asset_score_array[asset_index] = [precision, recall, f1]
            score_array[sample_index, :] = asset_score_array.mean(axis=0) # Macro averaged across assets
        # Compute precision, recall and f1 scores across all samples
        precision, recall, f1 = score_array.mean(axis=0)
        return {'precision': float(precision), 
                'recall': float(recall), 
                'f1': float(f1), 
                'invalid_format': invalid_format_count}
    
    # Evaluate TaskID.EXEMPTION_VALUATION
    def _evaluate_exemption_valuation(self, predictions: List[ExemptionValuationResponse], targets: List[Dict]):
        score_array = np.zeros((len(targets), 4)) # 4 columns for precision, recall, f1, mare
        invalid_format_count = 0
        for sample_index, (prediction, target) in enumerate(zip(predictions, targets)):
            if prediction is None: # Invalid response format
                score_array[sample_index] = [0, 0, 0, np.nan]
                invalid_format_count += 1
                continue
            normalized_prediction = {key.strip().lower(): value for key, value in prediction.root.items()}
            normalized_target = {
                asset_description.strip().lower(): [Claim(**claim_dict) for claim_dict in claim_dicts]
                for asset_description, claim_dicts in target.items()
            }
            asset_score_array = np.zeros((len(normalized_target), 4))
            for asset_index, (asset_description, claims) in enumerate(normalized_target.items()):
                matching_asset_description = self._find_matching_asset_description(asset_description, list(normalized_prediction.keys()))
                if matching_asset_description is None:
                    asset_score_array[asset_index] = [0, 0, 0, np.nan]
                    continue
                predicted_claims = normalized_prediction[matching_asset_description]
                precision, recall, f1, mare = self._compute_precision_recall_f1_mare_scores(predicted_claims, claims)
                asset_score_array[asset_index] = [precision, recall, f1, mare]
            score_array[sample_index, :] = np.nanmean(asset_score_array, axis=0) # Macro averaged across assets
        # Compute precision, recall, f1 and MARE scores across all samples
        precision, recall, f1, mare = np.nanmean(score_array, axis=0)
        mare = None if np.isnan(mare) else float(mare)
        return {'precision': float(precision), 
                'recall': float(recall), 
                'f1': float(f1), 
                'mare': mare,
                'invalid_format': invalid_format_count}
    
    # Evaluate TaskID.NONEXEMPT_ASSETS
    def _evaluate_nonexempt_assets(self, predictions: List[NonExemptAssetsResponse], targets: List[Dict]):
        score_array = np.zeros((len(targets), 4)) # 4 columns for precision, recall, f1, mare
        invalid_format_count = 0
        for sample_index, (prediction, target) in enumerate(zip(predictions, targets)):
            if prediction is None: # Invalid response format
                score_array[sample_index] = [0, 0, 0, np.nan]
                invalid_format_count += 1
                continue
            normalized_prediction = {key.strip().lower(): value for key, value in prediction.root.items()}
            normalized_target = {key.strip().lower(): value for key, value in target.items()}
            tp, fp, fn = 0, 0, 0
            relative_errors = []
            for jurisdiction, predicted_dollar_value in normalized_prediction.items():
                if jurisdiction not in normalized_target:
                    relative_errors.append(np.nan)
                    fp += 1
                else:
                    dollar_value = normalized_target[jurisdiction]
                    relative_error = self._absolute_relative_error(predicted_dollar_value, dollar_value)
                    relative_errors.append(relative_error)
                    if relative_error < 0.05:
                        normalized_target.pop(jurisdiction)
                        tp += 1
                    else:
                        fp += 1
            fn = len(normalized_target)
            precision, recall, f1 = self._precision_recall_f1_from_outcomes(tp, fp, fn)
            score_array[sample_index] = [precision, recall, f1, np.nanmean(relative_errors)]
        # Compute precision, recall, f1 and MARE scores across all samples
        precision, recall, f1, mare = np.nanmean(score_array, axis=0)
        mare = None if np.isnan(mare) else float(mare)
        return {'precision': float(precision), 
                'recall': float(recall), 
                'f1': float(f1), 
                'mare': mare,
                'invalid_format': invalid_format_count}
    
    # Evaluate TaskID.OPTIMAL_EXEMPTIONS
    def _evaluate_optimal_exemptions(self, predictions: List[OptimalExemptionsResponse], targets: List[Dict], cases: List[Case]):
        error_array = np.zeros((len(targets), 2)) # 2 columns for relative error, invalid claim ratio
        invalid_format_count = 0
        tp, fp, fn = 0, 0, 0
        for sample_index, (prediction, target, case) in enumerate(zip(predictions, targets, cases)):
            if prediction is None: # Invalid response format
                error_array[sample_index] = [np.nan, 1]
                invalid_format_count += 1
                fn += 1
                continue
            elif (not prediction.root) and (not target): # Edge case: optimal solution contains no claims
                error_array[sample_index] = [0, 0]
                tp += 1
                continue
            elif not target: # Optimal solution contains no claims, but prediction does
                error_array[sample_index] = [np.nan, 1]
                fn += 1
                continue
            # Validate predicted solution
            normalized_prediction = {key.strip().lower(): value for key, value in prediction.root.items()}
            predicted_jurisdiction = self._detect_jurisdiction(normalized_prediction, normalized=True)
            allowable_jurisdictions = self.statute_set_map[case.state_jurisdiction].allowable_exemption_jurisdictions()
            if predicted_jurisdiction is None or predicted_jurisdiction not in allowable_jurisdictions:
                error_array[sample_index] = [np.nan, 1]
                fn += 1
                continue
            # Initialize predicted solution and validate claims
            invalid_claim_count = 0
            total_claim_count = 0
            predicted_solution = self.solver.init_solution(case, predicted_jurisdiction)
            case_asset_map = self._case_asset_map_for_jurisdiction(case, predicted_jurisdiction, normalized=True)
            for asset_description, claims in normalized_prediction.items():
                total_claim_count += len(claims)
                matching_asset_description = self._find_matching_asset_description(asset_description, list(case_asset_map.keys()))
                if matching_asset_description is None:
                    invalid_claim_count += len(claims)
                    continue
                case_asset = case_asset_map[matching_asset_description]
                deduped_claim_map = {}
                for claim in claims:
                    if claim.normalized_citation not in deduped_claim_map:
                        deduped_claim_map[claim.normalized_citation] = 0
                    deduped_claim_map[claim.normalized_citation] += claim.claim_value
                deduped_claims = [Claim(citation=citation, claim_value=value) for citation, value in deduped_claim_map.items()]
                for claim in deduped_claims:
                    if (claim.normalized_citation not in case_asset.applicable_exemptions or 
                        claim.claim_value > case_asset.dollar_value):
                        invalid_claim_count += 1
                    else:
                        # Create checkpoint so we may revert if claim is invalid.
                        solution_checkpoint = deepcopy(predicted_solution)
                        allocated_amount = predicted_solution.allocate_claim_amount(claim.normalized_citation, claim.claim_value)
                        # If remaining claim value, check for additional item claims
                        while ((claim.claim_value - allocated_amount) > 0 and 
                               predicted_solution.item_claim_exists(claim.normalized_citation)):
                            allocated_amount += predicted_solution.allocate_claim_amount(claim.normalized_citation, claim.claim_value - allocated_amount)
                        # Over-allocated claims are treated as invalid.
                        # Over-allocation occurs whenever claim value exceeds the maximum value allowed by law (allocated amount).
                        if claim.claim_value > allocated_amount:
                            invalid_claim_count += 1
                            predicted_solution = solution_checkpoint
                        elif allocated_amount > 0:
                            case_asset.dollar_value -= allocated_amount
                            predicted_solution.claim_exemption(claim.normalized_citation, case_asset.description, allocated_amount)
            # All claims have been processed, any remaining dollar value is non-exempt
            for case_asset in case_asset_map.values():
                if case_asset.dollar_value > 0:
                    predicted_solution.non_exempt_assets[case_asset.description] = case_asset.dollar_value
            # Compute invalid claim ratio
            invalid_claim_ratio = invalid_claim_count / total_claim_count if total_claim_count > 0 else 0
            # Perform sanity checks on optimal solution
            # These checks will always pass if the same statutes and cases used to generate dataset are used for evaluation.
            normalized_target = {
                asset_description: [Claim(**claim_dict) for claim_dict in claim_dicts]
                for asset_description, claim_dicts in target.items()
            }
            optimal_jurisdiction = self._detect_jurisdiction(normalized_target)
            assert optimal_jurisdiction in allowable_jurisdictions, (
                f'Unexpected error: jurisdiction for target solution ({optimal_jurisdiction}) is not an allowable jurisdiction: {allowable_jurisdictions}'
            )
            # Initialize optimal solution and process claims (with sanity checks)
            optimal_solution = self.solver.init_solution(case, optimal_jurisdiction)
            case_asset_map = self._case_asset_map_for_jurisdiction(case, optimal_jurisdiction)
            for asset_description, claims in normalized_target.items():
                assert asset_description in case_asset_map, (
                    f'Unexpected error: target solution contains asset description ({asset_description}) not found in case assets: {list(case_asset_map.keys())}'
                )
                case_asset = case_asset_map[asset_description]
                for claim in claims:
                    assert claim.citation in case_asset.applicable_exemptions, (
                        f'Unexpected error: exemption citation in target solution ({claim.citation}) is not an allowable exemption: {case_asset.applicable_exemptions}'
                    )
                    allocated_amount = optimal_solution.allocate_claim_amount(claim.normalized_citation, claim.claim_value)
                    # If remaining claim value, check for additional item claims
                    while ((claim.claim_value - allocated_amount) > 0 and 
                            optimal_solution.item_claim_exists(claim.normalized_citation)):
                        allocated_amount += optimal_solution.allocate_claim_amount(claim.normalized_citation, claim.claim_value - allocated_amount)
                    
                    assert allocated_amount == claim.claim_value, (
                        f'Unexpected error: claim in target solution ({claim}) is over-allocated (allocated amount: {allocated_amount})'
                    )
                    case_asset.dollar_value -= allocated_amount
                    optimal_solution.claim_exemption(claim.normalized_citation, case_asset.description, allocated_amount)
            # All claims have been processed, any remaining dollar value is non-exempt
            for case_asset in case_asset_map.values():
                if case_asset.dollar_value > 0:
                    optimal_solution.non_exempt_assets[case_asset.description] = case_asset.dollar_value
            # Compare predicted and optimal solutions
            predicted_non_exempt_total = predicted_solution.total_non_exempt_value()
            optimal_non_exempt_total = optimal_solution.total_non_exempt_value()
            assert optimal_non_exempt_total <= predicted_non_exempt_total, (
                f'Unexpected error: encountered predicted solution which outperforms optimal solution (predicted: {predicted_non_exempt_total}, optimal: {optimal_non_exempt_total})'
            )
            relative_error = self._absolute_relative_error(predicted_non_exempt_total, optimal_non_exempt_total)
            error_array[sample_index] = [relative_error, invalid_claim_ratio]
            if relative_error < 0.05 and invalid_claim_ratio == 0:
                tp += 1
            else:
                fp += 1
        # Compute precision, recall, f1 and MARE scores across all samples
        precision, recall, f1 = self._precision_recall_f1_from_outcomes(tp, fp, fn)
        mare, invalid_claim_ratio = np.nanmean(error_array, axis=0)
        mare = None if np.isnan(mare) else float(mare)
        invalid_claim_ratio = None if np.isnan(invalid_claim_ratio) else float(invalid_claim_ratio)
        return {'precision': float(precision), 
                'recall': float(recall), 
                'f1': float(f1), 
                'mare': mare,
                'invalid_claim_ratio': invalid_claim_ratio,
                'invalid_format': invalid_format_count}