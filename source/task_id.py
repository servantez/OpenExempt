from enum import Enum, unique


@unique
class TaskID(Enum):
    GOVERNING_JURISDICTIONS = 1
    ASSET_EXEMPTION_CLASSIFICATION = 2
    ASSET_EXEMPTION_DOLLAR_VALUE = 3
    NON_EXEMPT_ASSETS = 4
    OPTIMAL_EXEMPTIONS = 5

    @staticmethod
    def supported_tasks():
        return [member.display_name() for member in TaskID]
    
    @staticmethod
    def display_name_to_task_id(display_name: str):
        return TaskID[display_name.replace(' ', '_').upper()]
    
    def display_name(self):
        words = self.name.split('_')
        return ' '.join([word.capitalize() for word in words])