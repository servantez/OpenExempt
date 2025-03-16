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
    single_max_claim_count: int = None
    married_max_claim_count: int = None
    unused_relationship: str = None # Citation to other exemption where unused portion can be used by this exemption (see 11 U.S.C. Section 522(d)(5) for example)
    unused_single_limit: int = None
    unused_married_limit: int = None

    def __post_init__(self):
        if self.unused_relationship:
            assert self.unused_single_limit and self.unused_married_limit, 'If an unused relationship exists, exemption limits must also be provided for the relationship'

    def to_dict(self):
        return {key: value for key, value in vars(self).items() if value is not None or key == 'single_limit' or key == 'married_limit'}