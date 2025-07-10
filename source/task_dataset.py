import os
import json
import logging
from typing import Dict, List
from dataclasses import dataclass
from .case import Case
from .config import Config
from .task_id import TaskID
from .jurisdiction import Jurisdiction
from .utils import read_jsonl_file, write_jsonl_file


@dataclass
class Task:
    uid: str
    start_task_id: TaskID
    terminal_task_id: TaskID
    jurisdiction: Jurisdiction
    instruction: str
    meta_instruction: str
    response_format: str
    facts: str
    solved_steps: str
    statutes: str
    solution: str | Dict

    @staticmethod
    def create_task(start_task_id: int, 
                    terminal_task_id: int, 
                    jurisdiction: str, 
                    instruction: str,
                    meta_instruction: str, 
                    response_format: str,  
                    facts: str,
                    solved_steps: str,
                    statutes: str, 
                    solution: str | Dict,
                    uid: str = None): # Task UID will exist only if task has been added to a dataset
        
        task = Task(uid, 
                    TaskID(start_task_id),
                    TaskID(terminal_task_id),
                    Jurisdiction(jurisdiction),
                    instruction,
                    meta_instruction,
                    response_format,
                    facts,
                    solved_steps,
                    statutes,
                    solution)
        
        if not task.is_valid(ignore_uid=True):
            raise ValueError(f'Task arguments must not be empty (task: {task})')
        return task

    def to_dict(self):
        return vars(self)
    
    # Expected format for evaluation
    def to_target(self):
        return {'uid': self.uid, 'target': self.solution}
    
    def serialize(self):
        serialized = self.to_dict()
        serialized['start_task_id'] = serialized['start_task_id'].value
        serialized['terminal_task_id'] = serialized['terminal_task_id'].value
        serialized['jurisdiction'] = serialized['jurisdiction'].value
        return serialized
    
    def is_valid(self, ignore_uid: bool = False):
        task_dict = self.to_dict().copy()
        del task_dict['solved_steps'] # Solved steps can be empty
        if ignore_uid:
            del task_dict['uid']
        return all(value is not None for value in task_dict.values())
    
    def prompt_inputs(self):
        return [self.instruction, self.meta_instruction, self.response_format, self.facts, self.solved_steps, self.statutes]
    
    def prompt(self):
        return '\n\n'.join(filter(None, self.prompt_inputs()))


class TaskDataset:
    
    # For reading an existing dataset
    @staticmethod
    def from_config(config: Config):
        dataset_name = config.dataset_name
        dataset_id = config.dataset_id
        dataset_directory = config.dataset_directory
        return TaskDataset(dataset_name, dataset_id, dataset_directory)
    
    # For reading an existing dataset
    @staticmethod
    def from_config_file_path(path: str, verbose: bool = True):
        assert os.path.exists(path), f'Config file does not exist at: {path}.'
        config_file = Config.load_config_file(path)
        return TaskDataset.from_config(Config(config_file, config_file['dataset_name'], verbose))
    
    # For reading an existing dataset
    @staticmethod
    def from_directory(directory: str):
        config_file_path = os.path.join(directory, Config.default_file_name)
        return TaskDataset.from_config_file_path(config_file_path)

    def __init__(self, name: str, dataset_id: str, dataset_directory: str):
        self.name = name
        self.dataset_id = dataset_id
        self.dataset_directory = dataset_directory
        self._tasks = {'test': [], 'dev': []}
        self._cases = {'test': [], 'dev': []}
        self.logger = logging.getLogger(self.name)

    def task_file_path(self, split: str = 'test'):
        return os.path.join(self.dataset_directory, f'{split}.jsonl')
    
    def case_file_path(self, split: str = 'test'):
        file_name = 'cases' if split == 'test' else f'{split}_cases'
        return os.path.join(self.dataset_directory, f'{file_name}.jsonl')
    
    @property
    def splits(self):
        return list(self._tasks.keys())
    
    def targets(self, split: str = 'test'):
        return [task.to_target() for task in self.get_data(split)]

    def add_task(self, task: Task, case: Case, split: str = 'test'):
        self.logger.info(f'Adding {split} task to dataset: {self.name}')
        task.uid = f'{self.dataset_id}_{split}_task_{len(self._tasks[split])}'
        if not task.is_valid():
            raise ValueError(f'Task arguments must not be empty (task: {task})')
        self._tasks[split].append(task)
        self._cases[split].append(case)

    def save(self, save_cases: bool = True, splits: List[str] = None):
        save_splits = splits or self.splits
        for split in save_splits:
            self.save_to_path(self.task_file_path(split), 
                              self.case_file_path(split) if save_cases else None, 
                              split)

    def save_to_path(self, path: str, case_file_path: str = None, split: str = 'test'):
        self.logger.info(f'Begin saving {split} dataset: {self.name} to path: {path}')
        serialized_tasks = list(map(lambda task: task.serialize(), self._tasks[split]))
        write_jsonl_file(path, serialized_tasks)
        if case_file_path:
            assert len(self._cases[split]) == len(self._tasks[split]), (
                f"Failed to save {split} dataset: {self.name} due to task count {len(self._tasks[split])} not being equal to case count {len(self._cases[split])}."
                )
            serialized_cases = list(map(lambda case: case.serialize(), self._cases[split]))
            write_jsonl_file(case_file_path, serialized_cases)
        self.logger.info(f'Finished saving {split} dataset.')

    def _load_data(self, split: str = 'test'):
        task_dicts = read_jsonl_file(self.task_file_path(split))
        return list(map(lambda task_dict: Task.create_task(**task_dict), task_dicts))
    
    def _load_cases(self, split: str = 'test'):
        case_dicts = read_jsonl_file(self.case_file_path(split))
        return list(map(lambda case_dict: Case.create_case(**case_dict), case_dicts))

    def get_data(self, split: str = 'test'):
        self._tasks[split] = self._tasks[split] or self._load_data(split)
        yield from self._tasks[split]

    def get_cases(self, split: str = 'test'):
        self._cases[split] = self._cases[split] or self._load_cases(split)
        yield from self._cases[split]

    def get_data_with_cases(self, split: str = 'test'):
        self._tasks[split] = self._tasks[split] or self._load_data(split)
        self._cases[split] = self._cases[split] or self._load_cases(split)
        yield from zip(self._tasks[split], self._cases[split])