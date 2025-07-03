from typing import List
from .jurisdiction import Jurisdiction
from .statute import Statute, Exemption


class StatuteSet:
    
    def __init__(self,
                 jurisdiction: Jurisdiction,
                 authority: str,
                 has_opted_out: bool,
                 statutes: List[Statute]):
        self.jurisdiction = jurisdiction
        self.authority = authority
        self.has_opted_out = has_opted_out
        self.statutes = statutes # exemption and non-exemption statutes

    def __str__(self):
        return f'Statute Set(jurisdiction: {self.jurisdiction}, authority: {self.authority})'

    def to_dict(self):
        return {'jurisdiction': self.jurisdiction.value,
                'authority': self.authority,
                'has_opted_out': self.has_opted_out,
                'statutes': list(map(lambda statute: statute.to_dict(), self.statutes))}
    
    def exemptions(self):
        return list(filter(lambda statute: isinstance(statute, Exemption), self.statutes))
    
    def non_exemptions(self):
        return list(filter(lambda statute: isinstance(statute, Statute), self.statutes))
    
    def exemption_citations(self):
        return list(map(lambda exemption: exemption.citation, self.exemptions()))
    
    def allowable_exemption_jurisdictions(self):
        if self.has_opted_out:
            return [self.jurisdiction]
        return [Jurisdiction.FEDERAL, self.jurisdiction]
    
    def display_content(self):
        statute_content = list(map(lambda statute: statute.display_content(), self.statutes))
        body = '\n\n'.join(statute_content)
        return f'{self.authority}\n{body}'