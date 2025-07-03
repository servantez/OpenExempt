import os
from typing import Dict, Any
from enum import Enum, unique
from .task_id import TaskID
from .config import Config


@unique
class SuiteID(Enum):
    TEMPORAL_REASONING = 'tr'

    def __init__(self, value):
        self.dataset_index_counter = {member: 0 for member in TaskID}

    def display_name(self):
        return self.name.lower()
    
    def display_value(self):
        return self.value.lower()

    def config_handler(self):
        handler_registry = {
            SuiteID.TEMPORAL_REASONING: self.create_tr_config_files
        }
        return handler_registry[self] if self in handler_registry else None
    
    def create_suite_configs(self, verbose: bool = True):
        handler = self.config_handler()
        default_config_file = self.get_default_suite_config_file()
        if handler:
            return [Config(config_file, dataset_name, verbose) for config_file, dataset_name in handler(default_config_file)]
        else:
            raise NotImplementedError(f'Config file handler not implemented for suite: {self.name}')
        
    def config_file_name(self):
        return f'{self.value.lower()}_config.json'
    
    def config_file_path(self):
        return os.path.join('data/configs', self.config_file_name())
    
    def get_dataset_name_with_task_id(self, task_id: TaskID):
        dataset_index = self.dataset_index_counter[task_id]
        self.dataset_index_counter[task_id] += 1
        return f'{task_id.name.lower()}_{dataset_index}'
        
    def get_default_suite_config_file(self):
        suite_config = Config.load_config_file(self.config_file_path())
        suite_name = self.display_name()
        suite_id = self.display_value()
        suite_directory = os.path.join(suite_config['output_directory'], suite_name)
        suite_config['output_directory'] = suite_directory
        suite_config = {'suite_name': suite_name, 
                        'suite_id': suite_id,
                        'suite_directory': suite_directory, 
                        **suite_config}
        return suite_config
    
    def dataset_config_file_with_update(self, default_config_file: Dict[str, Any], update_dict: Dict[str, Any]):
        dataset_config_file = default_config_file.copy()
        dataset_config_file.update(update_dict)
        terminal_task_id = TaskID(dataset_config_file['terminal_task_id'])
        dataset_name = self.get_dataset_name_with_task_id(terminal_task_id)
        return dataset_config_file, dataset_name
        
    def create_tr_config_files(self, default_config_file: Dict[str, Any]):
        config_files = []
        for count in range(1, 4):
            updates = {'state_jurisdictions': ["ILLINOIS", "WISCONSIN"], 
                       'asset_count_max': 2}
            config_file, dataset_name = self.dataset_config_file_with_update(default_config_file, updates)
            config_files.append((config_file, dataset_name))
        return config_files