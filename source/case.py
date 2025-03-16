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
    
    def party_coreference(self):
        return 'Debtors' if self.has_married_couple() else 'Debtor'
    
    