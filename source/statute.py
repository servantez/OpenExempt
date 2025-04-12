from dataclasses import dataclass


# Non-exemption statutes
@dataclass
class Statute:

    citation: str # citation should be a universal unique identifier
    description: str

    def to_dict(self):
        return vars(self)
    
    def display_content(self):
        return f'{self.citation}\n{self.description}'


# Exemption statutes
@dataclass
class Exemption(Statute):

    single_limit: int
    married_limit: int
    per_item_limit: int = None
    single_item_claim_count: int = None
    married_item_claim_count: int = None
    fallback_relationship: str = None # Citation to other exemption where unused portion can be used by this exemption (see 11 U.S.C. Section 522(d)(5) for example)
    single_fallback_limit: int = None
    married_fallback_limit: int = None
    mutual_exclusion: str = None # Citation to other exemption which cannot be claimed if this exemption is claimed

    def __post_init__(self):
        if self.fallback_relationship:
            assert self.single_fallback_limit and self.married_fallback_limit, 'If a fallback relationship exists, exemption limits must also be provided for the relationship'

    def to_dict(self):
        return {key: value for key, value in vars(self).items() if value is not None or key == 'single_limit' or key == 'married_limit'}