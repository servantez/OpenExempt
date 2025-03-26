from dataclasses import dataclass
from copy import deepcopy
from typing import List, Dict, Tuple
from .case import Case
from .asset import Asset
from .jurisdiction import Jurisdiction
from .statute_set import StatuteSet


# The solution class represents the solution state for a given case, in a given jurisdiction.
@dataclass
class Solution:
    unclaimed_exemptions: Dict[str, float] # {citation: remaining balance}
    claimed_exemptions: Dict[str, List[Dict[str, float]]] # {asset description: [{citation, claim value}]}
    non_exempt_assets: Dict[str, float] # {asset description: value}
    remaining_claim_counts: Dict[str, int] # {citation: remaining count}
    remaining_unused_relationships: Dict[str, Tuple[str, float]] # {to citation: (from citation, remaining balance)}
    per_item_limits: Dict[str, float] # {citation: per item limit}

    def __lt__(self, other):
        return self.total_non_exempt_value() < other.total_non_exempt_value()
    
    def __ge__(self, other):
        return self.total_non_exempt_value() >= other.total_non_exempt_value()

    def total_non_exempt_value(self):
        return sum(self.non_exempt_assets.values())
    
    # Attempt to allocate the claim amount for the specified exemption and return the actual amount allocated
    def allocate_claim_amount(self, citation: str, claim_amount: float):
        remaining_claim_count = self.remaining_claim_counts[citation]
        if remaining_claim_count is not None:
            if remaining_claim_count < 1: # No more claims remaining
                return 0
            self.remaining_claim_counts[citation] -= 1
        per_item_limit = self.per_item_limits[citation]
        max_claim_amount = claim_amount if per_item_limit is None else min(per_item_limit, claim_amount)
        amount_claimed = self._process_claim(citation, max_claim_amount)
        if amount_claimed < max_claim_amount:
            # Exemption has been exhausted, check for any unused relationships
            from_citation, balance = self.remaining_unused_relationships[citation]
            if from_citation is not None:
                remaining_claim_amount = min(balance, max_claim_amount - amount_claimed)
                unused_relationship_amount = self._process_claim(from_citation, remaining_claim_amount)
                if unused_relationship_amount > 0:
                    self.remaining_unused_relationships[citation] = (from_citation, balance - unused_relationship_amount)
                    amount_claimed += unused_relationship_amount
        return amount_claimed

    # Internal method: should only be called after a claim has been validated
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
        if asset_description not in self.claimed_exemptions:
            self.claimed_exemptions[asset_description] = []
        self.claimed_exemptions[asset_description].append({'citation': citation, 'claim_value': claim_amount})


class Solver:

    def __init__(self, statute_set_map: Dict[Jurisdiction, StatuteSet]):
        self.statute_set_map = statute_set_map
        # Construct a collection of maps to track solution state and reduce problem complexity based on case properties.
        self.single_exemption_map = {}
        self.married_exemption_map = {}
        self.single_max_claim_count_map = {}
        self.married_max_claim_count_map = {}
        self.single_unused_relationship_map = {}
        self.married_unused_relationship_map = {}
        self.per_item_limit_map = {}
        for jurisdiction, statute_set in statute_set_map.items():
            self.single_exemption_map[jurisdiction] = {}
            self.married_exemption_map[jurisdiction] = {}
            self.single_max_claim_count_map[jurisdiction] = {}
            self.married_max_claim_count_map[jurisdiction] = {}
            self.single_unused_relationship_map[jurisdiction] = {}
            self.married_unused_relationship_map[jurisdiction] = {}
            self.per_item_limit_map[jurisdiction] = {}
            for exemption in statute_set.exemptions():
                self.single_exemption_map[jurisdiction][exemption.citation] = exemption.single_limit
                self.married_exemption_map[jurisdiction][exemption.citation] = exemption.married_limit
                self.single_max_claim_count_map[jurisdiction][exemption.citation] = exemption.single_max_claim_count
                self.married_max_claim_count_map[jurisdiction][exemption.citation] = exemption.married_max_claim_count
                self.single_unused_relationship_map[jurisdiction][exemption.citation] = (exemption.unused_relationship, exemption.unused_single_limit)
                self.married_unused_relationship_map[jurisdiction][exemption.citation] = (exemption.unused_relationship, exemption.unused_married_limit)
                self.per_item_limit_map[jurisdiction][exemption.citation] = exemption.per_item_limit

    def citations_for_jurisdictions(self, jurisdictions: List[Jurisdiction]):
        citations = []
        for jurisdiction in jurisdictions:
            statute_set = self.statute_set_map[jurisdiction]
            citations.extend(statute_set.exemption_citations())
        return citations
    
    def init_solution(self, case: Case, jurisdiction: Jurisdiction):
        exemption_map = self.married_exemption_map if case.has_married_couple() else self.single_exemption_map
        unclaimed_exemptions = exemption_map[jurisdiction]
        claim_count_map = self.married_max_claim_count_map if case.has_married_couple() else self.single_max_claim_count_map
        remaining_claim_counts = claim_count_map[jurisdiction]
        unused_relationship_map = self.married_unused_relationship_map if case.has_married_couple() else self.single_unused_relationship_map
        remaining_unused_relationships = unused_relationship_map[jurisdiction]
        per_item_limits = self.per_item_limit_map[jurisdiction]
        return Solution(unclaimed_exemptions, {}, {}, remaining_claim_counts, remaining_unused_relationships, per_item_limits)
    
    def solve_case_for_jurisdiction(self, case: Case, jurisdiction: Jurisdiction):
        solution = self.init_solution(case, jurisdiction)
        assets = deepcopy(case.assets)
        for asset in assets:
            asset.applicable_exemptions = [citation for citation in asset.applicable_exemptions if citation in self.citations_for_jurisdictions([jurisdiction])]
        # Sort assets such that those with fewer applicable exemptions are exempted first.
        assets = sorted(assets, key=lambda asset: len(asset.applicable_exemptions))
        return self.recursive_optimal_exemption_search(assets, solution)

    # Branch and bound algorithm for determining optimal exemptions
    def recursive_optimal_exemption_search(self, assets: List[Asset], solution: Solution, optimal: Solution = None):
        if not assets:
            return solution if optimal is None else min(solution, optimal)
        new_solution = deepcopy(solution)
        asset = assets[0]
        if not asset.applicable_exemptions: # No applicable exemptions remain
            new_solution.non_exempt_assets[asset.description] = asset.dollar_value
            # If current solution already has a greater total value of non-exempt assets, prune this branch
            if optimal and (new_solution >= optimal):
                return optimal
            return self.recursive_optimal_exemption_search(assets[1:], new_solution, optimal)
        
        new_optimal = optimal
        for citation in asset.applicable_exemptions:
            allocated_amount = new_solution.allocate_claim_amount(citation, asset.dollar_value)
            if allocated_amount > 0:
                new_solution.claim_exemption(citation, asset.description, allocated_amount)
            if allocated_amount == asset.dollar_value: # Asset is completely exempt
                new_solution = self.recursive_optimal_exemption_search(assets[1:], new_solution, new_optimal)
            else: # Asset is not completely protected under current exemption
                assets_copy = deepcopy(assets)
                asset = assets_copy[0]
                asset.applicable_exemptions.remove(citation)
                new_solution = self.recursive_optimal_exemption_search(assets_copy, new_solution, new_optimal)
            new_optimal = new_solution if new_optimal is None else min(new_solution, new_optimal)
            return new_optimal
        
    # Solve TaskID.ASSET_EXEMPTION_CLASSIFICATION
    def solve_asset_exemption_classification(self, case: Case, allowable_jurisdictions: List[Jurisdiction]):
        solution = {}
        allowable_exemptions = self.citations_for_jurisdictions(allowable_jurisdictions)
        for asset in case.assets:
            solution[asset.description] = list(filter(lambda exemption: exemption in allowable_exemptions, asset.applicable_exemptions))
        return solution
    
    # Solve TaskID.ASSET_EXEMPTION_DOLLAR_VALUE
    def solve_asset_exemption_dollar_value(self, case: Case, allowable_jurisdictions: List[Jurisdiction]):
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
    
    # Solve TaskID.NON_EXEMPT_ASSETS
    def solve_non_exempt_assets(self, case: Case, allowable_jurisdictions: List[Jurisdiction]):
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
