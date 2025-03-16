from enum import Enum, unique


@unique
class TaskID(Enum):
    GOVERNING_JURISDICTIONS = 1
    ASSET_EXEMPTION_CLASSIFICATION = 2
    ASSET_EXEMPTION_DOLLAR_VALUE = 3
    NON_EXEMPT_ASSETS = 4
    OPTIMAL_EXEMPTIONS = 5

    @classmethod
    def supported_tasks(cls):
        return [member.display_name() for member in TaskID]
    
    def display_name(self):
        return self.name.capitalize()