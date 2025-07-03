import os
import random
import argparse
import logging
from source.config import Config
from source.suite_id import SuiteID
from source.case_generator import CaseGenerator
from source.task_generator import TaskGenerator
from source.task_dataset import TaskDataset
from source.task_suite import TaskSuite


def configure_logger_with_name(name: str, log_file_path: str):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    handler = logging.FileHandler(log_file_path)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
    return logger

def generate_demo(config: Config):
    case_generator = CaseGenerator(config)
    task_generator = TaskGenerator(config)
    case = case_generator.generate_case()
    task = task_generator.generate_task(case)
    return case, task

def generate_dataset(config: Config):
    # Setup dataset directory
    assert not os.path.exists(config.dataset_directory), 'Dataset with this name already exist.'
    os.mkdir(config.dataset_directory)
    config.copy_config_file_to_dataset_directory()

    # Setup logging
    logger = configure_logger_with_name(config.dataset_name, config.log_file_path)
    if not config.verbose:
        logger.disabled = True
    logger.info('OpenExempt initialized.')

    # Create dataset as specified in config file
    logger.info('Begin dataset generation.')
    dataset = TaskDataset(config.dataset_name, config.dataset_id, config.dataset_directory)
    case_generator = CaseGenerator(config)
    task_generator = TaskGenerator(config)
    for _ in range(config.dataset_size):
        case = case_generator.generate_case()
        task = task_generator.generate_task(case)
        dataset.add_task(task, case)
    logger.info('Finished dataset generation.')
    logger.info('OpenExempt finished.')
    return dataset

def generate_suite(suite_id: SuiteID, verbose: bool = True):
    # Setup suite directory
    default_config_file = suite_id.get_default_suite_config_file()
    suite_directory = default_config_file['suite_directory']
    assert not os.path.exists(suite_directory), 'Suite with this name already exists.'
    os.makedirs(suite_directory)

    # Setup logging
    suite_name = default_config_file['suite_name']
    log_file_path = os.path.join(suite_directory, 'log.log')
    logger = configure_logger_with_name(suite_name, log_file_path)
    if not verbose:
        logger.disabled = True
    logger.info('OpenExempt initialized.')

    # Create all datasets in suite
    logger.info('Begin suite generation.')
    suite = TaskSuite(suite_id, suite_directory)
    for dataset_config in suite_id.create_suite_configs():
        logger.info(f'Begin generating dataset: {dataset_config.dataset_name}.')
        dataset = generate_dataset(dataset_config)
        logger.info(f'Finished generating dataset: {dataset_config.dataset_name}.')
        suite.add_dataset(dataset)
    logger.info('Finished suite generation.')
    logger.info('OpenExempt finished.')
    return suite

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--mode', choices=['dataset', 'suite'], default='dataset', help='Select dataset or suite generation.')
    parser.add_argument('-n', '--name', required=True, help='Dataset name or suite ID being created.')
    parser.add_argument('-c', '--config_path', default='config.json', help='Path to configuration file (dataset mode only).')
    parser.add_argument('-s', '--seed', type=int, default=17, help='Random seed for reproducibility.')
    parser.add_argument('-v', '--verbose', action='store_true')
    args = parser.parse_args()
    random.seed(args.seed)
    if args.mode == 'dataset':
        config = Config.from_path(args.config_path, args.name, args.verbose)
        dataset = generate_dataset(config)
        dataset.save()
    elif args.mode == 'suite':
        suite_id = SuiteID(args.name)
        suite = generate_suite(suite_id, args.verbose)
        suite.save()