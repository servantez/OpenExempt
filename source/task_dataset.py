import os
import json
import logging
from typing import Dict
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
        self._tasks = []
        self._cases = []
        self.logger = logging.getLogger(self.name)

    def task_file_path(self):
        return os.path.join(self.dataset_directory, 'tasks.jsonl')
    
    def case_file_path(self):
        return os.path.join(self.dataset_directory, 'cases.jsonl')
    
    def targets(self):
        return [task.to_target() for task in self.get_data()]

    def add_task(self, task: Task, case: Case):
        self.logger.info(f'Adding task to dataset: {self.name}')
        task.uid = f'{self.dataset_id}_task_{len(self._tasks)}'
        if not task.is_valid():
            raise ValueError(f'Task arguments must not be empty (task: {task})')
        self._tasks.append(task)
        self._cases.append(case)

    def save(self, save_cases: bool = True):
        self.save_to_path(self.task_file_path(), self.case_file_path() if save_cases else None)

    def save_to_path(self, path: str, case_file_path: str = None):
        self.logger.info(f'Begin saving dataset: {self.name} to path: {path}')
        serialized_tasks = list(map(lambda task: task.serialize(), self._tasks))
        write_jsonl_file(path, serialized_tasks)
        if case_file_path:
            assert len(self._cases) == len(self._tasks), f"Failed to save dataset: {self.name} due to task count {len(self._tasks)} not being equal to case count {len(self._cases)}."
            serialized_cases = list(map(lambda case: case.serialize(), self._cases))
            write_jsonl_file(case_file_path, serialized_cases)
        self.logger.info('Finished saving dataset.')

    def _load_data(self):
        task_dicts = read_jsonl_file(self.task_file_path())
        return list(map(lambda task_dict: Task.create_task(**task_dict), task_dicts))
    
    def _load_cases(self):
        case_dicts = read_jsonl_file(self.case_file_path())
        return list(map(lambda case_dict: Case.create_case(**case_dict), case_dicts))

    def get_data(self):
        self._tasks = self._tasks or self._load_data()
        yield from self._tasks

    def get_cases(self):
        self._cases = self._cases or self._load_cases()
        yield from self._cases

    def get_data_with_cases(self):
        self._tasks = self._tasks or self._load_data()
        self._cases = self._cases or self._load_cases()
        yield from zip(self._tasks, self._cases)