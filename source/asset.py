from dataclasses import dataclass
from typing import List


@dataclass
class Asset:

    description: str
    dollar_value: float
    applicable_exemptions: List[str] # List of exemption labels

    def to_dict(self):
        return vars(self)
    
    def __str__(self):
        exemptions = ','.join(self.applicable_exemptions) if self.applicable_exemptions else 'None'
        return f'Asset(description: {self.description}, value: {self.dollar_value:,}, exemptions: {exemptions})'
    
    def formatted_dollar_value(self):
        return '${:,.2f}'.format(self.dollar_value)
    
    