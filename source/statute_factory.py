import os
import json
from typing import Dict, List, Any
from .jurisdiction import Jurisdiction
from .statute import Statute, Exemption
from .statute_set import StatuteSet
from .utils import file_names_with_extension


class StatuteFactory:
    
    @staticmethod
    def save_statute_set(statute_set: StatuteSet, directory: str):
        if not os.path.exists(directory):
            os.mkdir(directory)
        file_name = statute_set.jurisdiction.file_name()
        path = os.path.join(directory, file_name)

        # We do not overwrite statutes
        assert not os.path.exists(path), f'ERROR: statute set already exists at {path}.'
        with open(path, 'w') as file:
            json.dump(statute_set.to_dict(), file, indent=4)

    @staticmethod
    def create_statute(statute_dict: Dict[str, Any]):
        if 'single_limit' in statute_dict:
            return Exemption(**statute_dict)
        else:
            return Statute(**statute_dict)

    @staticmethod
    def load_statute_set(path: str):
        with open(path, 'r') as file:
            statute_set_dict = json.load(file)
        jurisdiction = Jurisdiction(statute_set_dict['jurisdiction'])
        statutes = list(map(StatuteFactory.create_statute, statute_set_dict['statutes']))
        return StatuteSet(jurisdiction,
                          statute_set_dict['authority'], 
                          statute_set_dict['has_opted_out'], 
                          statutes)
    
    @staticmethod
    def load_statute_sets(directory: str, jurisdictions: List[Jurisdiction]):
        statute_sets = []
        if jurisdictions:
            file_names = map(lambda jurisdiction: jurisdiction.file_name(), jurisdictions)
        else:
            file_names = file_names_with_extension(directory, 'json')
        for file_name in file_names:
            path = os.path.join(directory, file_name)
            statute_sets.append(StatuteFactory.load_statute_set(path))
        return statute_sets