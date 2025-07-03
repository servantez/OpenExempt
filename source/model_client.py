from typing import List
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.chat_models import ChatHuggingFace
from langchain_community.llms import HuggingFaceEndpoint
from langchain_core.output_parsers import JsonOutputParser
from .model_id import ModelID, ModelHost


class ModelClient:
    _retries = 3
    _timeout = 60

    def __init__(self, model_id: ModelID, temperature=None):
        self.model_id = model_id
        self.temperature = temperature or 0
        self.model = self._init_model()
        self.json_output_parser = JsonOutputParser()
        self.messages: List[BaseMessage] = []

    def _init_model(self):
        api_key = self.model_id.get_api_key()
        match self.model_id.host():
            case ModelHost.OPENAI:
                return ChatOpenAI(model=self.model_id.value,
                                  temperature=self.temperature,
                                  timeout=ModelClient._timeout,
                                  max_retries=ModelClient._retries,
                                  api_key=api_key)
            case ModelHost.ANTHROPIC:
                return ChatAnthropic(model=self.model_id.value,
                                     temperature=self.temperature,
                                     timeout=ModelClient._timeout,
                                     max_retries=ModelClient._retries,
                                     api_key=api_key)
            case ModelHost.GOOGLE:
                return ChatGoogleGenerativeAI(model=self.model_id.value,
                                              temperature=self.temperature,
                                              timeout=ModelClient._timeout,
                                              max_retries=ModelClient._retries,
                                              api_key=api_key)
            case ModelHost.HUGGINGFACE:
                return ChatHuggingFace(api_key)
    
    def __call__(self, prompt: str):
        self.messages.append(HumanMessage(content=prompt))
        response = self.model.invoke(self.messages)
        self.messages.append(response)
        return response.content
    
    def start_new_conversation(self, system_prompt: str = None):
        self.messages = [SystemMessage(content=system_prompt)] if system_prompt else []
    
    def invoke_with_json_output(self, prompt: str):
        content = self(prompt)
        try:
            return content, self.json_output_parser.parse(content)
        except:
            return content, None