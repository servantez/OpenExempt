import os
import argparse
import logging
from source.config import Config
from source.case_generator import CaseGenerator
from source.task_generator import TaskGenerator
from source.task_dataset import TaskDataset


def generate_dataset(config: Config):
    # Setup dataset directory
    assert not os.path.exists(config.dataset_directory), 'Dataset with this name already exists'
    os.mkdir(config.dataset_directory)
    config.copy_config_file_to_dataset_directory()

    # Configure logging
    logging.basicConfig(filename=config.log_file_path, 
                        level=logging.INFO, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    logger.info('OpenExempt initialized.')

    # Create dataset as specified in config file
    logger.info('Begin dataset generation.')
    cases = []
    dataset = TaskDataset(config.dataset_name, config.task_directory)
    case_generator = CaseGenerator(config)
    task_generator = TaskGenerator(config)
    for _ in range(config.dataset_size):
        case = case_generator.generate_case()
        cases.append(case)
        task = task_generator.generate_task(case)
        dataset.add_task(task)
    logger.info('Finished dataset generation.')

    # Save dataset to task directory
    logger.info('Begin saving dataset.')
    dataset.save()
    logger.info('Finished saving dataset.')

    logger.info('OpenExempt finished.')
    return cases, dataset

def generate_demo(config: Config):
    case_generator = CaseGenerator(config)
    task_generator = TaskGenerator(config)
    case = case_generator.generate_case()
    task = task_generator.generate_task(case)
    return case, task

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dataset_name', required=True, help='Name of dataset being created.')
    parser.add_argument('-c', '--config_path', default='config.json', help='Path to configuration file.')
    parser.add_argument('-v', '--verbose', action='store_true')
    args = parser.parse_args()
    config = Config(args.dataset_name, args.config_path, args.verbose)
    generate_dataset(config)