import re
from typing import Dict, List
from pydantic import BaseModel, RootModel


# Pydantic response classes are used to validate and parse task predictions into a structured format
class Claim(BaseModel):
    citation: str
    claim_value: float

    @staticmethod
    def normalize_citation(citation: str):
        normalized = re.sub(r'§(?!\s)', '§ ', citation) # Ensure § is followed by a space
        return normalized.strip().lower()

    def __str__(self):
        return f'Claim(citation: {self.citation}, value: {self.claim_value:,})'
    
    @property
    def normalized_citation(self):
        return Claim.normalize_citation(self.citation)

# TaskID.EXEMPTION_CLASSIFICATION
class ExemptionClassificationResponse(RootModel):
    root: Dict[str, List[str]]

# TaskID.EXEMPTION_VALUATION
class ExemptionValuationResponse(RootModel):
    root: Dict[str, List[Claim]]

# TaskID.NONEXEMPT_ASSETS
class NonExemptAssetsResponse(RootModel):
    root: Dict[str, float]

# TaskID.OPTIMAL_EXEMPTIONS
class OptimalExemptionsResponse(RootModel):
    root: Dict[str, List[Claim]]