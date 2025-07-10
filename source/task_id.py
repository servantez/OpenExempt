from enum import Enum, unique
from langchain_core.output_parsers import PydanticOutputParser
from .pydantic_response import (
    ExemptionClassificationResponse, 
    ExemptionValuationResponse, 
    NonExemptAssetsResponse, 
    OptimalExemptionsResponse
    )


@unique
class TaskID(Enum):
    ALLOWABLE_EXEMPTIONS = 1
    EXEMPTION_CLASSIFICATION = 2
    EXEMPTION_VALUATION = 3
    NONEXEMPT_ASSETS = 4
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
            case TaskID.ALLOWABLE_EXEMPTIONS:
                return str
            case TaskID.EXEMPTION_CLASSIFICATION | TaskID.EXEMPTION_VALUATION | TaskID.NONEXEMPT_ASSETS | TaskID.OPTIMAL_EXEMPTIONS:
                return dict
            case _:
                raise NotImplementedError(f'Response type not implemented for task: {self}.')
    
    def response_parser(self):
        response_class_registry = {
            TaskID.EXEMPTION_CLASSIFICATION: ExemptionClassificationResponse,
            TaskID.EXEMPTION_VALUATION: ExemptionValuationResponse,
            TaskID.NONEXEMPT_ASSETS: NonExemptAssetsResponse,
            TaskID.OPTIMAL_EXEMPTIONS: OptimalExemptionsResponse
        }
        if self.solution_type() == str:
            return None
        response_class = response_class_registry[self] if self in response_class_registry else None
        if response_class:
            return PydanticOutputParser(pydantic_object=response_class)
        else:
            raise NotImplementedError(f'Response parser not implemented for task: {self}.')