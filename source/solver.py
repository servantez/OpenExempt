from dataclasses import dataclass
from copy import deepcopy
from typing import List, Dict, Tuple
from .case import Case
from .asset import Asset
from .jurisdiction import Jurisdiction
from .statute import Exemption
from .statute_set import StatuteSet


# The solution class represents the solution state for a given case, in a given jurisdiction.
@dataclass
class Solution:
    exemptions: Dict[str, Exemption] # Citation to exemption map which is treated as an immutable copy of exemption values
    unclaimed_exemptions: Dict[str, float] # {citation: remaining balance}
    claimed_exemptions: Dict[str, List[Dict[str, float]]] # {asset description: [{citation, claim value}]}
    non_exempt_assets: Dict[str, float] # {asset description: value}
    remaining_item_claim_counts: Dict[str, int] # {citation: remaining count}
    item_claim_amounts: Dict[str, float] # {citation: claim amount per item}
    remaining_fallback_relationships: Dict[str, Tuple[str, float]] # {to citation: (from citation, remaining balance)}
    excluded_exemptions: List[str] # List of exemption citations where a mutual exclusion relationship has been triggered

    def __lt__(self, other):
        return self.total_non_exempt_value() < other.total_non_exempt_value()
    
    def __ge__(self, other):
        return self.total_non_exempt_value() >= other.total_non_exempt_value()

    def total_non_exempt_value(self):
        return sum(self.non_exempt_assets.values())
    
    # Attempt to allocate claim amount for the specified exemption and return the actual amount allocated.
    # Returned allocation amount represents min(claim amount, max remaining amount available under this exemption).
    # Exemptions with item claim counts will only return an allocation for a single item claim.
    def allocate_claim_amount(self, citation: str, claim_amount: float):
        if citation in self.excluded_exemptions: # Mutual exclusion relationship has been triggered for this exemption
            return 0
        remaining_item_claim_count = self.remaining_item_claim_counts[citation]
        item_claim_amount = None
        if remaining_item_claim_count is not None:
            if remaining_item_claim_count < 1: # No more claims remaining
                return 0
            self.remaining_item_claim_counts[citation] -= 1
            item_claim_amount = self.item_claim_amounts[citation]
        max_claim_amount = claim_amount if item_claim_amount is None else min(item_claim_amount, claim_amount)
        per_item_limit = self.exemptions[citation].per_item_limit
        max_claim_amount = max_claim_amount if per_item_limit is None else min(per_item_limit, max_claim_amount)
        amount_claimed = self._process_claim(citation, max_claim_amount)
        if amount_claimed < max_claim_amount:
            # Exemption has been exhausted, check for any fallback relationships
            from_citation, balance = self.remaining_fallback_relationships[citation]
            if from_citation is not None:
                remaining_claim_amount = min(balance, max_claim_amount - amount_claimed)
                fallback_relationship_amount = self._process_claim(from_citation, remaining_claim_amount)
                if fallback_relationship_amount > 0:
                    self.remaining_fallback_relationships[citation] = (from_citation, balance - fallback_relationship_amount)
                    amount_claimed += fallback_relationship_amount
        return amount_claimed

    # Internal method: should only be called by solution instance during claim allocation
    def _process_claim(self, citation: str, claim_amount: float):
        available_amount = self.unclaimed_exemptions[citation]
        if available_amount is None: # No exemption limit
            return claim_amount
        elif available_amount >= claim_amount:
            self.unclaimed_exemptions[citation] -= claim_amount
            return claim_amount
        if available_amount > 0:
            self.unclaimed_exemptions[citation] = 0
        return available_amount

    # This method should only be passed claim amounts allocated by allocate_claim_amount
    def claim_exemption(self, citation: str, asset_description: str, claim_amount: float):
        # Trigger mutual exclusion relationship if one exist
        exemption = self.exemptions[citation]
        if exemption.mutual_exclusion:
            self.excluded_exemptions.append(exemption.mutual_exclusion)
        if asset_description not in self.claimed_exemptions:
            self.claimed_exemptions[asset_description] = []
        citation_exists = False
        for citation_dict in self.claimed_exemptions[asset_description]:
            if citation_dict.get('citation') == citation:
                citation_dict['claim_value'] += claim_amount
                citation_exists = True
                break
        if not citation_exists:
            self.claimed_exemptions[asset_description].append({'citation': citation, 'claim_value': claim_amount})

    # Check if a given exemption has item claims still available
    def item_claim_exists(self, citation: str):
        remaining_item_claim_count = self.remaining_item_claim_counts[citation]
        return remaining_item_claim_count is not None and remaining_item_claim_count > 0


class Solver:

    def __init__(self, statute_set_map: Dict[Jurisdiction, StatuteSet]):
        self.statute_set_map = statute_set_map
        self.exemption_map = {}
        # Construct a collection of maps to track solution state and reduce problem complexity based on case properties.
        self.single_exemption_map = {}
        self.married_exemption_map = {}
        self.single_item_claim_count_map = {}
        self.married_item_claim_count_map = {}
        self.single_item_claim_amount_map = {}
        self.married_item_claim_amount_map = {}
        self.single_fallback_relationship_map = {}
        self.married_fallback_relationship_map = {}
        for jurisdiction, statute_set in statute_set_map.items():
            self.exemption_map[jurisdiction] = {}
            self.single_exemption_map[jurisdiction] = {}
            self.married_exemption_map[jurisdiction] = {}
            self.single_item_claim_count_map[jurisdiction] = {}
            self.married_item_claim_count_map[jurisdiction] = {}
            self.single_item_claim_amount_map[jurisdiction] = {}
            self.married_item_claim_amount_map[jurisdiction] = {}
            self.single_fallback_relationship_map[jurisdiction] = {}
            self.married_fallback_relationship_map[jurisdiction] = {}
            for exemption in statute_set.exemptions():
                self.exemption_map[jurisdiction][exemption.citation] = exemption
                self.single_exemption_map[jurisdiction][exemption.citation] = exemption.single_limit
                self.married_exemption_map[jurisdiction][exemption.citation] = exemption.married_limit
                self.single_item_claim_count_map[jurisdiction][exemption.citation] = exemption.single_item_claim_count
                self.married_item_claim_count_map[jurisdiction][exemption.citation] = exemption.married_item_claim_count
                self.single_item_claim_amount_map[jurisdiction][exemption.citation] = exemption.single_limit / exemption.single_item_claim_count if exemption.single_item_claim_count else None
                self.married_item_claim_amount_map[jurisdiction][exemption.citation] = exemption.married_limit / exemption.married_item_claim_count if exemption.married_item_claim_count else None
                self.single_fallback_relationship_map[jurisdiction][exemption.citation] = (exemption.fallback_relationship, exemption.single_fallback_limit)
                self.married_fallback_relationship_map[jurisdiction][exemption.citation] = (exemption.fallback_relationship, exemption.married_fallback_limit)

    def citations_for_jurisdictions(self, jurisdictions: List[Jurisdiction]):
        citations = []
        for jurisdiction in jurisdictions:
            statute_set = self.statute_set_map[jurisdiction]
            citations.extend(statute_set.exemption_citations())
        return citations
    
    def init_solution(self, case: Case, jurisdiction: Jurisdiction):
        exemptions = self.exemption_map[jurisdiction]
        unclaimed_exemptions = self.married_exemption_map[jurisdiction] if case.has_married_couple() else self.single_exemption_map[jurisdiction]
        remaining_item_claim_counts = self.married_item_claim_count_map[jurisdiction] if case.has_married_couple() else self.single_item_claim_count_map[jurisdiction]
        item_claim_amounts = self.married_item_claim_amount_map[jurisdiction] if case.has_married_couple() else self.single_item_claim_amount_map[jurisdiction]
        remaining_fallback_relationships = self.married_fallback_relationship_map[jurisdiction] if case.has_married_couple() else self.single_fallback_relationship_map[jurisdiction]
        return deepcopy(Solution(exemptions, unclaimed_exemptions, {}, {}, remaining_item_claim_counts, item_claim_amounts, remaining_fallback_relationships, []))
    
    def solve_case_for_jurisdiction(self, case: Case, jurisdiction: Jurisdiction):
        solution = self.init_solution(case, jurisdiction)
        assets = deepcopy(case.assets)
        jurisdiction_citations = self.citations_for_jurisdictions([jurisdiction])
        for asset in assets:
            asset.applicable_exemptions = [citation for citation in asset.applicable_exemptions if citation in jurisdiction_citations]
        # Sort assets such that those with fewer applicable exemptions are exempted first.
        assets = sorted(assets, key=lambda asset: len(asset.applicable_exemptions))
        return self.recursive_optimal_exemption_search(assets, solution)

    # Branch and bound algorithm for determining optimal exemptions
    def recursive_optimal_exemption_search(self, assets: List[Asset], solution: Solution, optimal: Solution = None):
        if not assets:
            return solution if optimal is None else min(solution, optimal)
        asset = assets[0]
        if not asset.applicable_exemptions: # No applicable exemptions remain
            new_solution = deepcopy(solution)
            new_solution.non_exempt_assets[asset.description] = asset.dollar_value
            # If current solution already has a greater total value of non-exempt assets, prune this branch
            if optimal and (new_solution >= optimal):
                return optimal
            return self.recursive_optimal_exemption_search(assets[1:], new_solution, optimal)
        
        # Check every permutation of exemption application, including claiming no exemptions for the current asset
        new_optimal = optimal
        for citation in asset.applicable_exemptions:
            new_solution = deepcopy(solution)
            allocated_amount = new_solution.allocate_claim_amount(citation, asset.dollar_value)
            if allocated_amount > 0:
                new_solution.claim_exemption(citation, asset.description, allocated_amount)
            if allocated_amount == asset.dollar_value: # Asset is completely exempt
                new_solution = self.recursive_optimal_exemption_search(assets[1:], new_solution, new_optimal)
            else: # Asset is not completely protected under current exemption
                updated_assets = assets[:]
                updated_assets[0] = deepcopy(assets[0])
                updated_asset = updated_assets[0]
                updated_asset.dollar_value -= allocated_amount
                if new_solution.item_claim_exists(citation):
                    # We've just used an item claim, but additional item claims still exist for this exemption.
                    # Leave the citation in the applicable exemptions, so we may check the solution where additional item claims are used on this asset.
                    new_solution = self.recursive_optimal_exemption_search(updated_assets, new_solution, new_optimal)
                else:
                    updated_exemptions = [exemption for exemption in updated_asset.applicable_exemptions if exemption != citation]
                    updated_asset.applicable_exemptions = updated_exemptions
                    new_solution = self.recursive_optimal_exemption_search(updated_assets, new_solution, new_optimal)
            new_optimal = new_solution if new_optimal is None else min(new_solution, new_optimal)

        # Check solution where we claim no exemptions for this asset
        updated_assets = assets[:]
        updated_assets[0] = deepcopy(assets[0])
        updated_assets[0].applicable_exemptions = []
        new_solution = deepcopy(solution)
        new_solution = self.recursive_optimal_exemption_search(updated_assets, new_solution, new_optimal)
        new_optimal = new_solution if new_optimal is None else min(new_solution, new_optimal)
        return new_optimal
    
    # Solve TaskID.EXEMPTION_CLASSIFICATION
    def solve_exemption_classification(self, case: Case, allowable_jurisdictions: List[Jurisdiction]):
        solution = {}
        allowable_exemptions = self.citations_for_jurisdictions(allowable_jurisdictions)
        for asset in case.assets:
            solution[asset.description] = list(filter(lambda exemption: exemption in allowable_exemptions, asset.applicable_exemptions))
        return solution
    
    # Solve TaskID.EXEMPTION_VALUATION
    def solve_exemption_valuation(self, case: Case, allowable_jurisdictions: List[Jurisdiction]):
        solution = {}
        for jurisdiction in allowable_jurisdictions:
            # This object represents the solution state prior to exempting any assets. We will use it to calculate solutions at the asset level (without considering aggregate values).
            unprocessed_solution = self.init_solution(case, jurisdiction)
            allowable_exemptions = self.statute_set_map[jurisdiction].exemption_citations()
            for asset in case.assets:
                filtered_exemptions = list(filter(lambda exemption: exemption in allowable_exemptions, asset.applicable_exemptions))
                for citation in filtered_exemptions:
                    solution_copy = deepcopy(unprocessed_solution)
                    claim_amount = solution_copy.allocate_claim_amount(citation, asset.dollar_value)
                    if claim_amount > 0:
                        if asset.description not in solution:
                            solution[asset.description] = []
                        solution[asset.description].append({'citation': citation, 'claim_value': claim_amount})
        return solution
    
    # Solve TaskID.NONEXEMPT_ASSETS
    def solve_nonexempt_assets(self, case: Case, allowable_jurisdictions: List[Jurisdiction]):
        solution = {}
        for jurisdiction in allowable_jurisdictions:
            jurisdiction_solution = self.solve_case_for_jurisdiction(case, jurisdiction)
            solution[jurisdiction.display_name()] = jurisdiction_solution.total_non_exempt_value()
        return solution
    
    # Solve TaskID.OPTIMAL_EXEMPTIONS
    def solve_optimal_exemptions(self, case: Case, allowable_jurisdictions: List[Jurisdiction]):
        solutions = [self.solve_case_for_jurisdiction(case, jurisdiction) for jurisdiction in allowable_jurisdictions]
        solution = min(solutions)
        return solution.claimed_exemptions