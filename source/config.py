import os
import json


class Config:

    def __init__(self, dataset_name: str, config_path: str = 'config.json', verbose: bool = True):
        self.dataset_name = dataset_name
        if not self.dataset_name:
            raise ValueError('Dataset name must not be empty.')
        if ' ' in self.dataset_name:
            raise ValueError('Dataset name cannot contain spaces.')
        self.config_path = config_path
        self.verbose = verbose
        with open(self.config_path, 'r') as file:
            config = json.load(file)
        for key, value in config.items():
            setattr(self, key, value)
        self.dataset_directory = os.path.join(self.task_directory, self.dataset_name)
        self.log_file_path = os.path.join(self.dataset_directory, 'log.log')
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

    def state_jurisdiction_count(self):
        return len(self.state_jurisdictions)

    def copy_config_file_to_dataset_directory(self):
        with open(self.config_path, 'r') as file:
            config = json.load(file)
        with open(os.path.join(self.dataset_directory, 'config.json'), 'w') as file:
            json.dump(config, file, indent=4)