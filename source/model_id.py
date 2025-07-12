import os
from enum import Enum, unique


@unique
class ModelHost(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    HUGGINGFACE = "huggingface"


@unique
class ModelID(Enum):
    # Enum values must be official model names
    GPT_4_1 = 'gpt-4.1'
    o3 = 'o3'
    o4_mini = 'o4-mini'

    def host(self):
        match self:
            case ModelID.GPT_4_1 | ModelID.o3 | ModelID.o4_mini:
                return ModelHost.OPENAI
            case _:
                raise NotImplementedError(f'Model host not implemented for model: {self.name}')
            
    def env_variable(self):
        match self.host():
            case ModelHost.OPENAI:
                return "OPENAI_API_KEY"
            case ModelHost.ANTHROPIC:
                return "ANTHROPIC_API_KEY"
            case ModelHost.GOOGLE:
                return "GOOGLE_API_KEY"
            case ModelHost.HUGGINGFACE:
                return "HUGGINGFACEHUB_API_TOKEN"
            case _:
                raise NotImplementedError(f'Environment variable not implemented for model: {self.name}')
            
    def get_api_key(self):
        api_key = os.getenv(self.env_variable())
        if not api_key:
            raise ValueError(f'API key not found for environment variable: {self.env_variable()}')
        return api_key
    
    def supports_temperature(self):
        return self not in [ModelID.o3, ModelID.o4_mini]