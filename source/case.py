from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict
from .party import Party
from .asset import Asset
from .jurisdiction import Jurisdiction


@dataclass
class Case:

    debtor: Party
    joint_debtor: Party
    assets: List[Asset]
    state_jurisdiction: Jurisdiction
    petition_date: datetime
    domicile_dates: Dict[datetime, str]

    def has_married_couple(self):
        return bool(self.joint_debtor)
    
    def domicile_count(self):
        return len(self.domicile_dates)
    
    def asset_count(self):
        return len(self.assets)
    
    def parties(self):
        return [self.debtor, self.joint_debtor] if self.has_married_couple() else [self.debtor]
    
    def party_coreference(self):
        return 'Debtors' if self.has_married_couple() else 'Debtor'
    
    def to_dict(self):
        return {
            'debtor': self.debtor.to_dict(),
            'joint_debtor': self.joint_debtor.to_dict() if self.joint_debtor else None,
            'assets': [asset.to_dict() for asset in self.assets],
            'state_jurisdiction': self.state_jurisdiction.value,
            'petition_date': self.petition_date.isoformat(),
            'domicile_dates': {date.isoformat(): state for date, state in self.domicile_dates.items()}
        }