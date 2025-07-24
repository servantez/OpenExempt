import os
import json
import argparse
from dotenv import load_dotenv
from source.config import Config
from source.jurisdiction import Jurisdiction
from source.statute_factory import StatuteFactory
from source.task_dataset import TaskDataset
from source.task_suite import TaskSuite
from source.model_id import ModelID
from source.model_client import ModelClient
from source.utils import read_jsonl_file, write_jsonl_file
from open_exempt import configure_logger_with_name
from evaluator import Evaluator




# Load API keys from .env file
load_dotenv()

def run_dataset(dataset_directory: str, output_directory: str, model: ModelClient, evaluator: Evaluator, verbose: bool = True):
    # Load dataset
    config = Config.from_directory(dataset_directory)
    dataset = TaskDataset.from_config(config)

    # Setup dataset output directory
    prediction_directory = os.path.join(output_directory, dataset.dataset_id)
    prediction_file_path = os.path.join(prediction_directory, 'predictions.jsonl')
    result_file_path = os.path.join(prediction_directory, 'results.jsonl')
    os.makedirs(prediction_directory, exist_ok=True)

    # We don't overwrite files, so if predictions do not exist, neither should results.
    invalid_file_state = (not os.path.exists(prediction_file_path)) and os.path.exists(result_file_path)
    assert not invalid_file_state, f'Results already exist, but predictions do not for dataset: {dataset.dataset_id}.'

    # Setup logging
    log_file_path = os.path.join(prediction_directory, 'log.log')
    logger = configure_logger_with_name(dataset.name, log_file_path, verbose)
    if not verbose:
        logger.disabled = True
    logger.info('OpenExempt initialized.')

    # If predictions exist, load them and skip to evaluation
    if os.path.exists(prediction_file_path):
        logger.info(f'Predictions already exist for this dataset: {dataset.dataset_id}.')
        logger.info(f'Skipping inference and loading predictions at: {prediction_file_path}.')
        predictions = read_jsonl_file(prediction_file_path)
    else:
        # Run inference on dataset
        logger.info(f'Begin inference on dataset: {dataset.dataset_id}')
        predictions = []
        for task in dataset.get_data():
            logger.info(f'Begin inference on task: {task.uid}')
            model.start_new_conversation()
            
            prediction = model(task.prompt())
            predictions.append({'uid': task.uid, 'prediction': prediction})
            logger.info(f'Finished inference on task: {task.uid}')
        logger.info(f'Finished inference on dataset: {dataset.dataset_id}')

        # Save predictions
        logger.info(f'Begin saving predictions to path: {prediction_file_path}')
        write_jsonl_file(prediction_file_path, predictions)
        logger.info('Finished saving predictions.')
    
    # If results exist, skip evaluation
    if os.path.exists(result_file_path):
        logger.info(f'Skipping evaluation. Results for this dataset already exist at: {result_file_path}.')
        with open(result_file_path, 'r') as file:
            results = json.load(file)
    else:
        # Run evaluation on dataset
        logger.info(f'Begin evaluation on dataset: {dataset.dataset_id}')
        tasks = [task for task in dataset.get_data()]
        cases = [case for case in dataset.get_cases()]
        targets = [task.to_target() for task in tasks]
        task_id = tasks[0].terminal_task_id
        results = evaluator.evaluate(task_id, predictions, targets, cases, model.model_id, logger)
        logger.info(f'Finished evaluation on dataset: {dataset.dataset_id}')

        # Save results
        logger.info(f'Begin saving results to path: {result_file_path}')
        results = {'dataset_id': dataset.dataset_id, 'model_id': model.model_id.value, **results}
        with open(result_file_path, 'w') as file:
            json.dump(results, file, indent=4)
        logger.info('Finished saving results.')
    logger.info('OpenExempt finished.')
    return (config, predictions, results)

def run_suite(suite_directory: str, output_directory: str, model: ModelClient, evaluator: Evaluator, verbose: bool = True):
    # Load suite
    suite = TaskSuite.from_directory(suite_directory)

    # Setup suite output directory
    suite_output_directory = os.path.join(output_directory, suite.name)
    os.makedirs(suite_output_directory, exist_ok=True)

    # Setup logging
    log_file_path = os.path.join(suite_output_directory, 'log.log')
    logger = configure_logger_with_name(suite.name, log_file_path, verbose)
    if not verbose:
        logger.disabled = True
    logger.info('OpenExempt initialized.')

    # Run inference on suite
    experiments = []
    for dataset_directory in suite.get_dataset_directories():
        logger.info(f'Begin inference on dataset at: {dataset_directory}')
        experiment = run_dataset(dataset_directory, suite_output_directory, model, evaluator, verbose)
        experiments.append(experiment)
        logger.info(f'Finished inference on dataset at: {dataset_directory}')
    logger.info('OpenExempt finished.')
    return experiments

def run_inference(mode: str, model_id: ModelID, directory: str, output_directory: str, statute_directory: str, verbose: bool = True):
    model = ModelClient(model_id)
    model_output_directory = os.path.join(output_directory, model_id.value) # Each model has its own output directory
    statute_sets = StatuteFactory.load_statute_sets(statute_directory, list(Jurisdiction))
    evaluator = Evaluator(statute_sets)
    if mode == 'dataset':
        return run_dataset(directory, model_output_directory, model, evaluator, verbose)
    elif mode == 'suite':
        return run_suite(directory, model_output_directory, model, evaluator, verbose)
    else:
        raise ValueError(f'Invalid inference mode: {mode}')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run inference and evaluation on a dataset or suite.')
    parser.add_argument('--mode', choices=['dataset', 'suite'], default='dataset', help='Choose to run dataset or suite.')
    parser.add_argument('--model', required=True, help='Official model name used by provider.')
    parser.add_argument('-d', '--directory', required=True, help='Path to dataset or suite directory.')
    parser.add_argument('-o', '--output_directory', default='predictions', help='Path to root output directory.')
    parser.add_argument('-s', '--statute_directory', default='data/statutes', help='Path to statute directory.')
    parser.add_argument('-v', '--verbose', action='store_true')
    args = parser.parse_args()
    model_id = ModelID(args.model)
    run_inference(args.mode, model_id, args.directory, args.output_directory, args.statute_directory, args.verbose)