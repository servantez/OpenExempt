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
    # Enum value must be official model name
    GPT_5 = 'gpt-5'
    GPT_4_1 = 'gpt-4.1'
    o3 = 'o3'
    o4_MINI = 'o4-mini'
    CLAUDE_SONNET_4 = 'claude-sonnet-4-0'
    CLAUDE_HAIKU_3_5 = 'claude-3-5-haiku-latest'
    GEMMA_3 = 'gemma-3-27b-it'
    GEMINI_2_5_PRO = 'gemini-2.5-pro'
    GEMINI_2_5_FLASH = 'gemini-2.5-flash'
    LLAMA_4_MAVERICK = 'Llama-4-Maverick-17B-128E-Instruct'
    LLAMA_4_SCOUT = 'Llama-4-Scout-17B-16E-Instruct'
    DEEPSEEK_R1 = 'DeepSeek-R1'
    DEEPSEEK_V3 = 'DeepSeek-V3'

    @property
    def host(self):
        match self:
            case ModelID.GPT_5 | ModelID.GPT_4_1 | ModelID.o3 | ModelID.o4_MINI:
                return ModelHost.OPENAI
            case ModelID.CLAUDE_SONNET_4 | ModelID.CLAUDE_HAIKU_3_5:
                return ModelHost.ANTHROPIC
            case ModelID.GEMINI_2_5_PRO | ModelID.GEMINI_2_5_FLASH:
                return ModelHost.GOOGLE
            case (ModelID.GEMMA_3 | ModelID.LLAMA_4_MAVERICK | ModelID.LLAMA_4_SCOUT | 
                  ModelID.DEEPSEEK_R1 | ModelID.DEEPSEEK_V3):
                return ModelHost.HUGGINGFACE
            case _:
                raise NotImplementedError(f'Model host not implemented for model: {self}')
    
    @property
    def hf_repo_id(self):
        match self:
            case ModelID.GEMMA_3:
                return f'google/{self.value}'
            case ModelID.LLAMA_4_MAVERICK | ModelID.LLAMA_4_SCOUT:
                return f'meta-llama/{self.value}'
            case ModelID.DEEPSEEK_R1 | ModelID.DEEPSEEK_V3:
                return f'deepseek-ai/{self.value}'
            case _:
                raise NotImplementedError(f'Hugging Face repo not defined for model: {self}')
    
    # Specific model checkpoints used for OpenExempt Benchmark evaluation
    # Return model checkpoint if defined, otherwise return official model name
    @property
    def checkpoint(self):
        match self:
            case ModelID.GPT_5:
                return 'gpt-5-2025-08-07'
            case ModelID.GPT_4_1:
                return 'gpt-4.1-2025-04-14'
            case ModelID.o3:
                return 'o3-2025-04-16'
            case ModelID.o4_MINI:
                return 'o4-mini-2025-04-16'
            case ModelID.CLAUDE_SONNET_4:
                return 'claude-sonnet-4-20250514'
            case ModelID.CLAUDE_HAIKU_3_5:
                return 'claude-3-5-haiku-20241022'
            case _: # No checkpoint identifiers for other models
                return self.value
    
    def env_variable(self):
        match self.host:
            case ModelHost.OPENAI:
                return 'OPENAI_API_KEY'
            case ModelHost.ANTHROPIC:
                return 'ANTHROPIC_API_KEY'
            case ModelHost.GOOGLE:
                return 'GOOGLE_API_KEY'
            case ModelHost.HUGGINGFACE:
                return 'HUGGINGFACEHUB_API_TOKEN'
            case _:
                raise NotImplementedError(f'Environment variable not implemented for host: {self.host}')
    
    def get_api_key(self):
        api_key = os.getenv(self.env_variable())
        if not api_key:
            raise ValueError(f'API key not found for environment variable: {self.env_variable()}')
        return api_key
    
    def supports_temperature(self):
        return self.temperature() is not None
    
    # We use a zero temperature for all supporting models, unless the developer recommends otherwise
    def temperature(self):
        match self:
            case ModelID.GPT_5 | ModelID.o4_MINI | ModelID.o3:
                return None # Does not support temperature
            case ModelID.DEEPSEEK_R1:
                return 0.6 # Recommended by developer (https://huggingface.co/deepseek-ai/DeepSeek-R1)
            case _:
                return 0
            
    def model_parameters(self):
        parameters = {'temperature': self.temperature()} if self.supports_temperature() else {}
        match self:
            case ModelID.CLAUDE_HAIKU_3_5:
                parameters['max_tokens'] = 8192 # Maximum length supported
            case (ModelID.GEMMA_3 | ModelID.LLAMA_4_MAVERICK | ModelID.LLAMA_4_SCOUT | 
                  ModelID.DEEPSEEK_R1 | ModelID.DEEPSEEK_V3):
                parameters['max_new_tokens'] = 16384
            case _:
                parameters['max_tokens'] = 16384
        return parameters