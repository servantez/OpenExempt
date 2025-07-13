import os
from typing import Dict, Any
from enum import Enum, unique
from .task_id import TaskID
from .config import Config


@unique
class SuiteID(Enum):
    TEMPORAL_REASONING = 'tr'
    REASONING_DECOMPOSITION = 'rd'
    MARITAL_REASONING = 'mr'
    DISTRACTOR_ROBUSTNESS = 'dr'
    SYCOPHANCY_ROBUSTNESS = 'sr'
    ASSET_SCALING = 'as'
    JURISDICTION_SCALING = 'js'
    BASIC_COMPETENCY = 'bc'
    INTERMEDIATE_COMPETENCY = 'ic'
    ADVANCED_COMPETENCY = 'ac'

    def __init__(self, value):
        self.dataset_index_counter = {member: 0 for member in TaskID}

    def display_name(self):
        return self.name.lower()
    
    def display_value(self):
        return self.value.lower()

    def config_handler(self):
        handler_registry = {
            SuiteID.TEMPORAL_REASONING: self.create_tr_config_files,
            SuiteID.REASONING_DECOMPOSITION: self.create_rd_config_files,
            SuiteID.MARITAL_REASONING: self.create_mr_config_files,
            SuiteID.DISTRACTOR_ROBUSTNESS: self.create_dr_config_files,
            SuiteID.SYCOPHANCY_ROBUSTNESS: self.create_sr_config_files,
            SuiteID.ASSET_SCALING: self.create_as_config_files,
            SuiteID.JURISDICTION_SCALING: self.create_js_config_files,
            SuiteID.BASIC_COMPETENCY: self.create_bc_config_files,
            SuiteID.INTERMEDIATE_COMPETENCY: self.create_ic_config_files,
            SuiteID.ADVANCED_COMPETENCY: self.create_ac_config_files
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
        return os.path.join('data/suite_configs', self.config_file_name())
    
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
        return [self.dataset_config_file_with_update(default_config_file, {'domicile_count_min': count, 'domicile_count_max': count})
                for count in range(1, 6)]
    
    def create_rd_config_files(self, default_config_file: Dict[str, Any]):
        return [self.dataset_config_file_with_update(default_config_file, {'domicile_count_min': count, 'domicile_count_max': count})
                for count in range(1, 6)]
    
    def create_mr_config_files(self, default_config_file: Dict[str, Any]):
        return [self.dataset_config_file_with_update(default_config_file, {'domicile_count_min': count, 'domicile_count_max': count})
                for count in range(1, 6)]
    
    def create_dr_config_files(self, default_config_file: Dict[str, Any]):
        return [self.dataset_config_file_with_update(default_config_file, {'domicile_count_min': count, 'domicile_count_max': count})
                for count in range(1, 6)]
    
    def create_sr_config_files(self, default_config_file: Dict[str, Any]):
        return [self.dataset_config_file_with_update(default_config_file, {'domicile_count_min': count, 'domicile_count_max': count})
                for count in range(1, 6)]
    
    def create_as_config_files(self, default_config_file: Dict[str, Any]):
        return [self.dataset_config_file_with_update(default_config_file, {'domicile_count_min': count, 'domicile_count_max': count})
                for count in range(1, 6)]
    
    def create_js_config_files(self, default_config_file: Dict[str, Any]):
        return [self.dataset_config_file_with_update(default_config_file, {'domicile_count_min': count, 'domicile_count_max': count})
                for count in range(1, 6)]
    
    def create_bc_config_files(self, default_config_file: Dict[str, Any]):
        updates = []
        for task_id in list(TaskID):
            for count in range(1, 3):
                updates.append({'terminal_task_id': task_id.value, 
                                'domicile_count_min': count, 
                                'domicile_count_max': count,
                                'asset_count_min': count, 
                                'asset_count_max': count})
        return [self.dataset_config_file_with_update(default_config_file, update) for update in updates]
    
    def create_ic_config_files(self, default_config_file: Dict[str, Any]):
        updates = []
        for task_id in list(TaskID):
            for count in range(3, 6):
                # Incremently increase obfuscation complexity
                irrelevant_domicile_facts = count > 3
                irrelevant_asset_facts = count > 4
                if task_id == TaskID.ALLOWABLE_EXEMPTIONS and irrelevant_asset_facts:
                    continue # This is not a meaningful config variant since task AE contains no asset facts
                updates.append({'terminal_task_id': task_id.value, 
                                'asset_count_min': count, 
                                'asset_count_max': count,
                                'irrelevant_asset_facts': irrelevant_asset_facts,
                                'irrelevant_domicile_facts': irrelevant_domicile_facts})
        return [self.dataset_config_file_with_update(default_config_file, update) for update in updates]
    
    def create_ac_config_files(self, default_config_file: Dict[str, Any]):
        updates = []
        for task_id in list(TaskID):
            for count in range(6, 9):
                # Incremently increase obfuscation complexity (irrelevant domicile facts present by default)
                irrelevant_domicile_facts = task_id != TaskID.ALLOWABLE_EXEMPTIONS
                domicile_opinions = count > 6
                asset_opinions = count > 7
                if task_id == TaskID.ALLOWABLE_EXEMPTIONS and asset_opinions:
                    continue # This is not a meaningful config variant since task AE contains no asset facts
                updates.append({'terminal_task_id': task_id.value, 
                                'asset_count_min': count, 
                                'asset_count_max': count,
                                'asset_opinions': asset_opinions,
                                'domicile_opinions': domicile_opinions,
                                'irrelevant_domicile_facts': irrelevant_domicile_facts})
        return [self.dataset_config_file_with_update(default_config_file, update) for update in updates]