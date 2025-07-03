from enum import Enum, unique
from langchain_core.output_parsers import PydanticOutputParser
from .pydantic_response import (
    AssetExemptionClassificationResponse, 
    AssetExemptionDollarValueResponse, 
    NonExemptAssetsResponse, 
    OptimalExemptionsResponse
    )


@unique
class TaskID(Enum):
    GOVERNING_JURISDICTION = 1
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
    
    def solution_type(self):
        match self:
            case TaskID.GOVERNING_JURISDICTION:
                return str
            case TaskID.ASSET_EXEMPTION_CLASSIFICATION | TaskID.ASSET_EXEMPTION_DOLLAR_VALUE | TaskID.NON_EXEMPT_ASSETS | TaskID.OPTIMAL_EXEMPTIONS:
                return dict
            case _:
                raise NotImplementedError(f'Response type not implemented for task: {self}.')
    
    def response_parser(self):
        response_class_registry = {
            TaskID.ASSET_EXEMPTION_CLASSIFICATION: AssetExemptionClassificationResponse,
            TaskID.ASSET_EXEMPTION_DOLLAR_VALUE: AssetExemptionDollarValueResponse,
            TaskID.NON_EXEMPT_ASSETS: NonExemptAssetsResponse,
            TaskID.OPTIMAL_EXEMPTIONS: OptimalExemptionsResponse
        }
        if self.solution_type() == str:
            return None
        response_class = response_class_registry[self] if self in response_class_registry else None
        if response_class:
            return PydanticOutputParser(pydantic_object=response_class)
        else:
            raise NotImplementedError(f'Response parser not implemented for task: {self}.')