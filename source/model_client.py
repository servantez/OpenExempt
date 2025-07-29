from typing import List
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from .model_id import ModelID, ModelHost


class ModelClient:
    _retries = 3
    _timeout = 600

    def __init__(self, model_id: ModelID):
        self.model_id = model_id
        self.model = self._init_model()
        self.messages: List[BaseMessage] = []

    def _init_model(self):
        api_key = self.model_id.get_api_key()
        parameters = {
            "model": self.model_id.value,
            "timeout": ModelClient._timeout,
            "api_key": api_key
        }
        parameters.update(self.model_id.model_parameters())
        match self.model_id.host:
            case ModelHost.OPENAI:
                model = ChatOpenAI(**parameters)
            case ModelHost.ANTHROPIC:
                model = ChatAnthropic(**parameters)
            case ModelHost.GOOGLE:
                model = ChatGoogleGenerativeAI(**parameters)
            case ModelHost.HUGGINGFACE:
                hf_parameters = {'repo_id': self.model_id.hf_repo_id, 
                                 "timeout": ModelClient._timeout,
                                 'huggingfacehub_api_token': api_key}
                hf_parameters.update(self.model_id.model_parameters())
                llm = HuggingFaceEndpoint(**hf_parameters)
                model = ChatHuggingFace(llm=llm, streaming=True) # Stream to prevent provider timeout
            case _:
                raise NotImplementedError(f'Model initialization not implemented for host: {self.model_id.host}')
        return model.with_retry(stop_after_attempt=ModelClient._retries + 1)
    
    def __call__(self, prompt: str):
        self.messages.append(HumanMessage(content=prompt))
        response = self.model.invoke(self.messages)
        self.messages.append(response)
        return response.content
    
    def start_new_conversation(self, system_prompt: str = None):
        self.messages = [SystemMessage(content=system_prompt)] if system_prompt else []