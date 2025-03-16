from enum import Enum, unique


@unique
class Jurisdiction(Enum):
    FEDERAL = 'FEDERAL'
    WI = 'WISCONSIN'
    IL = 'ILLINOIS'

    @staticmethod
    def supported_jurisdictions():
        return [member.display_name() for member in Jurisdiction]
    
    def display_name(self):
        return self.value.title()
    
    def file_name(self):
        return self.value.lower() + '.json'

    def is_federal(self):
        return self == Jurisdiction.FEDERAL