import os
import json
import logging
from typing import Dict
from dataclasses import dataclass
from .task_id import TaskID
from .jurisdiction import Jurisdiction
from .utils import read_jsonl_file, write_jsonl_file


@dataclass
class Task:

    start_task_id: TaskID
    end_task_id: TaskID
    jurisdiction: Jurisdiction
    instruction: str
    meta_instruction: str
    response_format: str
    facts: str
    solved_steps: str
    statutes: str
    solution: str | Dict
    
    def to_dict(self):
        return vars(self)
    
    def serialize(self):
        serialized = self.to_dict()
        serialized['start_task_id'] = serialized['start_task_id'].value
        serialized['end_task_id'] = serialized['end_task_id'].value
        serialized['jurisdiction'] = serialized['jurisdiction'].value
        return json.dumps(serialized)
    
    def is_valid(self):
        task_dict = self.to_dict()
        del task_dict['solved_steps'] # Solved steps can be empty
        return all(value is not None for value in task_dict.values())
    
    def prompt_inputs(self):
        return [self.instruction, self.meta_instruction, self.response_format, self.facts, self.solved_steps, self.statutes]
    
    def prompt(self):
        return '\n\n'.join(filter(None, self.prompt_inputs()))


class TaskDataset:

    @staticmethod
    def create_task(start_task_id: int, 
                    end_task_id: int, 
                    jurisdiction: str, 
                    instruction: str,
                    meta_instruction: str, 
                    response_format: str,  
                    facts: str,
                    solved_steps: str,
                    statutes: str, 
                    solution: str):
        
        task = Task(TaskID(start_task_id),
                    TaskID(end_task_id),
                    Jurisdiction(jurisdiction),
                    instruction,
                    meta_instruction,
                    response_format,
                    facts,
                    solved_steps,
                    statutes,
                    solution)
        
        if not task.is_valid():
            raise ValueError(f'Task arguments must not be empty (task: {task})')
        return task

    def __init__(self, name, task_directory):
        self.name = name
        self.task_directory = task_directory
        self.tasks = []
        self.logger = logging.getLogger(__name__)

    def file_path(self):
        return os.path.join(self.task_directory, self.name, 'tasks.jsonl')

    def add_task(self, task: Task):
        self.logger.info(f'Adding task to dataset: {self.name}')
        self.tasks.append(task)

    def save(self):
        self.save_to_path(self.file_path())

    def save_to_path(self, path: str):
        self.logger.info(f'Saving dataset: {self.name} to path: {path}')
        serialized_tasks = list(map(lambda task: task.serialize(), self.tasks))
        write_jsonl_file(path, serialized_tasks)

    def get_data(self):
        path = self.file_path()
        self.logger.info(f'Loading dataset from path: {path}')
        task_dicts = read_jsonl_file(path)
        self.tasks = list(map(lambda task_dict: TaskDataset.create_task(**task_dict), task_dicts))
        yield from self.tasks

    # TODO: load HF dataset
    def load_data(self, source):
        # load HF dataset from source then save to task directory
        # get data
        pass
