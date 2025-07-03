import os
import logging
from .suite_id import SuiteID
from .task_dataset import TaskDataset


# The TaskSuite class is responsible for reading and writing collections of task datasets
class TaskSuite:

    # For reading an existing dataset
    @staticmethod
    def from_directory(directory: str):
        suite_id = SuiteID[os.path.basename(directory).upper()]
        return TaskSuite(suite_id, directory)

    def __init__(self, suite_id: SuiteID, suite_directory: str):
        self.suite_id = suite_id
        self.name = suite_id.display_name()
        self.suite_directory = suite_directory
        self.datasets = []
        self.logger = logging.getLogger(self.name)

    def get_dataset_directories(self):
        # First verify suite directory exists
        assert os.path.isdir(self.suite_directory), f'Suite directory does not exist: {self.suite_directory}'
        # Iterate over every dataset directory in the suite
        dataset_directories = [directory for directory in os.listdir(self.suite_directory) if os.path.isdir(os.path.join(self.suite_directory, directory))]
        for directory_name in dataset_directories:
            yield os.path.join(self.suite_directory, directory_name)

    def get_data(self):
        # Iterate over every task in the suite
        for dataset_directory in self.get_dataset_directories():
            dataset = TaskDataset.from_directory(dataset_directory)
            for task in dataset.get_data():
                yield dataset.name, task

    def add_dataset(self, dataset: TaskDataset):
        self.logger.info(f'Adding dataset: {dataset.name} to suite: {self.name}')
        self.datasets.append(dataset)

    def save(self, save_cases: bool = True):
        self.save_to_directory(self.suite_directory, save_cases)

    def save_to_directory(self, directory: str, save_cases: bool = True):
        self.logger.info(f'Saving suite: {self.name} to directory: {directory}')
        for dataset in self.datasets:
            dataset.save(save_cases)