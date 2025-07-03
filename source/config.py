import os
import json
from typing import Dict


class Config:
    default_file_name = 'config.json'

    @staticmethod
    def load_config_file(config_path: str = None):
        config_path = config_path or Config.default_file_name
        with open(config_path, 'r') as file:
            return json.load(file)
        
    @staticmethod
    def load_config_file_in_directory(directory: str):
        return Config.load_config_file(os.path.join(directory, Config.default_file_name))
    
    @staticmethod
    def from_path(config_path: str, dataset_name: str, verbose: bool = True):
        config_file = Config.load_config_file(config_path)
        return Config(config_file, dataset_name, verbose)
    
    @staticmethod
    def from_default(dataset_name: str = 'temp', verbose: bool = True):
        return Config.from_path(Config.default_file_name, dataset_name, verbose)
    
    def __init__(self, config_file: Dict, dataset_name: str, verbose: bool = True):
        self.dataset_name = dataset_name
        if not self.dataset_name:
            raise ValueError('Dataset name must not be empty.')
        if ' ' in self.dataset_name:
            raise ValueError('Dataset name cannot contain spaces.')
        for key, value in config_file.items():
            setattr(self, key, value)
        self.verbose = verbose
        self.dataset_directory = config_file.get('dataset_directory', os.path.join(config_file['output_directory'], self.dataset_name))
        self.log_file_path = os.path.join(self.dataset_directory, 'log.log')
        suite_id = config_file.get('suite_id')
        self.dataset_id = config_file.get('dataset_id', f'{suite_id}_{dataset_name}' if suite_id else dataset_name)
        self.config_file = {'dataset_name': self.dataset_name, 
                            'dataset_id': self.dataset_id, 
                            'dataset_directory': self.dataset_directory, 
                            **config_file}
        self.validate()

    def validate(self):
        if self.state_jurisdiction_count() < 1:
            raise ValueError('At least one state jurisdiction must be provided.')
        if 'FEDERAL' in self.state_jurisdictions:
            raise ValueError('Federal jurisdiction should not be included in state jurisdictions.')
        if self.domicile_count_min < 1 or self.domicile_count_min > 5:
            raise ValueError('Min domicile count must be at least one and at most five.')
        if self.domicile_count_max < 1 or self.domicile_count_max > 5:
            raise ValueError('Max domicile count must be at least one and at most five.')
        if  self.domicile_count_min > self.domicile_count_max:
            raise ValueError('Min domicile count must be less than or equal to max domicile count')
        if self.asset_count_min < 1 or self.asset_count_min > 8:
            raise ValueError('Min asset count must be at least one and at most eight.')
        if self.asset_count_max < 1 or self.asset_count_max > 8:
            raise ValueError('Max asset count must be at least one and at most eight.')
        if  self.asset_count_min > self.asset_count_max:
            raise ValueError('Min asset count must be less than or equal to max asset count')
        
    def state_jurisdiction_count(self):
        return len(self.state_jurisdictions)

    def copy_config_file_to_dataset_directory(self):
        with open(os.path.join(self.dataset_directory, Config.default_file_name), 'w') as file:
            json.dump(self.config_file, file, indent=4)