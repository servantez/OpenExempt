from typing import Dict, List
from pydantic import BaseModel, RootModel


# Pydantic response classes are used to validate and parse task predictions into a structured format
class Claim(BaseModel):
    citation: str
    claim_value: float

    def __str__(self):
        return f'Claim(citation: {self.citation}, value: {self.claim_value:,})'
    
    @property
    def normalized_citation(self):
        return self.citation.strip().lower()

# TaskID.ASSET_EXEMPTION_CLASSIFICATION
class AssetExemptionClassificationResponse(RootModel):
    root: Dict[str, List[str]]

# TaskID.ASSET_EXEMPTION_DOLLAR_VALUE
class AssetExemptionDollarValueResponse(RootModel):
    root: Dict[str, List[Claim]]

# TaskID.NON_EXEMPT_ASSETS
class NonExemptAssetsResponse(RootModel):
    root: Dict[str, float]

# TaskID.OPTIMAL_EXEMPTIONS
class OptimalExemptionsResponse(RootModel):
    root: Dict[str, List[Claim]]