import os
import json
import random
from collections.abc import Sequence, Generator
from typing import List, Dict, Any


def read_jsonl_file(path: str):
    with open(path, 'r') as file:
        return [json.loads(line) for line in file]
    
def write_jsonl_file(path: str, items: List[Dict]):
    with open(path, 'w') as file:
        for item in items:
            line = json.dumps(item)
            file.write(line + '\n')

def file_names_with_extension(directory: str, extension: str):
    directory_contents = os.listdir(directory)
    return list(filter(lambda file_name: file_name.endswith(extension), directory_contents))

# Creates a generator capable of producing samples of arbitrary length
# Yields all items in the sequence before yielding any item again
# Ensures equal distribution across many cycles through the sequence
def infinite_sampler(items: Sequence[Any]):
    while True:
        shuffled = random.sample(items, len(items))
        yield from shuffled

# Generator argument should be created using infinite_sampler function
def infinite_sample(generator: Generator, size: int):
    return [next(generator) for _ in range(size)]