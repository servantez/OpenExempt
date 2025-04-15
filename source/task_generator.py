import os
import json
import random
import logging
import datetime
import inflect
from typing import List
from collections.abc import Generator
from .case import Case
from .asset import Asset
from .party import Party
from .jurisdiction import Jurisdiction
from .statute_factory import StatuteFactory
from .task_id import TaskID
from .task_dataset import TaskDataset
from .template_manager import TemplateManager
from .solver import Solver, Solution
from .utils import infinite_sampler


class TaskGenerator:

    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.inflect_engine = inflect.engine()
        self.template_manager = TemplateManager(config)
        self.instructions = self.read_json_file_in_data_directory('instructions.json')
        self.snippets = self.read_json_file_in_data_directory('snippets.json')
        self.city_sampler = self.create_city_sampler()
        self.statute_set_map = self.load_statute_set_map()
        self.solver = Solver(self.statute_set_map)

    def read_json_file_in_data_directory(self, file_name: str):
        path = os.path.join(self.config.data_directory, file_name)
        with open(path, 'r') as file:
            return json.load(file)
        
    def load_statute_set_map(self):
        jurisdiction_labels = ['FEDERAL'] + self.config.state_jurisdictions
        jurisdictions = list(map(lambda label: Jurisdiction(label), jurisdiction_labels))
        statute_sets = StatuteFactory.load_statute_sets(self.config.statute_directory, jurisdictions)
        return {statute_set.jurisdiction: statute_set for statute_set in statute_sets}
        
    def create_city_sampler(self):
        city_sampler = {}
        cities = self.read_json_file_in_data_directory('cities.json')
        for state, city_list in cities.items():
            if state.upper() in self.config.state_jurisdictions:
                jurisdiction = Jurisdiction(state.upper())
                city_sampler[jurisdiction] = infinite_sampler(city_list)
        return city_sampler
    
    def create_name_variant_sampler(self, debtor: Party, joint_debtor: Party = None):
        if joint_debtor:
            name_variants = [f'{debtor.first_name} and {joint_debtor.first_name}',
                             f'the {debtor.pluralize_last_name()}',
                             f'{debtor.first_name} and {joint_debtor.full_name()}',
                             'the Debtors']
        else:
            name_variants = [debtor.first_name, 
                             debtor.last_name, 
                             debtor.full_name(), 
                             'the Debtor']
        return infinite_sampler(name_variants)
    
    def sample_city_in_state(self, state: str):
        return next(self.city_sampler[state])
    
    # Sample a random integer (1 to upper bound) and reduce balance by sample value 
    def sample_and_exhaust(self, balance: int, upper_bound: int, weights: List[int] = None):
        upper = min(balance, upper_bound)
        choices = list(range(1, upper + 1))
        trimmed_weights = weights[:upper] if weights else None
        sample = random.choices(choices, weights=trimmed_weights, k=1)[0]
        return sample, balance - sample
    
    def format_date(self, date: datetime, template: str):
        day = date.day
        month = date.month
        year = date.year
        day_ordinal = self.inflect_engine.ordinal(day)
        weekday = date.strftime("%A")
        month_name = date.strftime("%B")
        return template.format(day=day,
                               month=month,
                               year=year,
                               day_ordinal=day_ordinal,
                               weekday=weekday,
                               month_name=month_name)
    
    def format_asset_description(self, asset: Asset, template: str):
        before, after = template.split('{asset}', 1)
        words_before = before.split()
        word_before = words_before[-1].lower() if words_before else None
        if word_before and (word_before == 'a' or word_before == 'an'):
            first_description_word = asset.description.split()[0]
            correct_article = self.inflect_engine.an(first_description_word).split()[0]
            words_before[-1] = correct_article.capitalize() if len(words_before) == 1 else correct_article
            formatted = ' '.join(words_before) + ' ' + asset.description + after
        else:
            formatted = template.replace('{asset}', asset.description, 1)
        return formatted
    
    # For testing purposes
    def create_dummy_task(self):
        return TaskDataset.create_task(1, 5, 'WISCONSIN', 'instruction', 'meta_instruction', 'response_format', 'context', 'solution')

    def hydrate_domicile_template(self, template: str, date: datetime, state: Jurisdiction, name_variant: str = None):
        city = self.sample_city_in_state(state)
        hydrated = template.replace('{location}', f'{city}, {state.display_name()}', 1)
        date_format = self.template_manager.sample_date_format()
        formatted_date = self.format_date(date, date_format)
        hydrated = hydrated.replace('{date}', formatted_date, 1)
        if name_variant:
            name = name_variant
            if hydrated.startswith('{party}') and name_variant.startswith('the'):
                name = name[0].upper() + name[1:]
            hydrated = hydrated.replace('{party}', name)
        return hydrated
    
    def hydrate_asset_template(self, template: str, asset: Asset, name_variant: str = None):
        hydrated = self.format_asset_description(asset, template)
        hydrated = hydrated.replace('{value}', asset.formatted_dollar_value(), 1)
        if name_variant:
            name = name_variant
            if hydrated.startswith('{party}') and name_variant.startswith('the'):
                name = name[0].upper() + name[1:]
            hydrated = hydrated.replace('{party}', name)
        return hydrated
    
    def create_preamble(self, debtor: Party, joint_debtor: Party, petition_date: datetime):
        preamble_template = self.snippets['preamble']
        full_party_names = debtor.full_name() if not joint_debtor else f'{debtor.first_name} and {joint_debtor.full_name()}'
        preamble = preamble_template.replace('{party}', full_party_names)
        coreference = 'the Debtors' if joint_debtor else 'the Debtor'
        preamble = preamble.replace('{coreference}', coreference)
        date_format = self.template_manager.sample_date_format()
        formatted_date = self.format_date(petition_date, date_format)
        preamble = preamble.replace('{petition_date}', formatted_date)
        return preamble
    
    def create_domicile_facts(self, case: Case, name_variant_sampler: Generator):
        # We shuffle templates for each case to ensure the same template does not appear twice
        domicile_template_sampler_map = self.template_manager.create_domicile_template_sampler_map()
        domicile_dates = iter(case.domicile_dates.keys())
        domicile_facts = []
        remaining_domicile_count = case.domicile_count()
        while remaining_domicile_count > 0:
            sample, remaining_domicile_count = self.sample_and_exhaust(remaining_domicile_count, 2, [0.67, 0.33]) # One location template twice as likely
            hydrated = self.template_manager.sample_domicile_template(domicile_template_sampler_map, sample)
            for index in range(sample):
                name_variant = next(name_variant_sampler) if index == 0 else None
                date = next(domicile_dates)
                state = case.domicile_dates[date]
                hydrated = self.hydrate_domicile_template(hydrated, date, state, name_variant)
            domicile_facts.append(hydrated)
        return domicile_facts
    
    def create_asset_facts(self, case: Case, name_variant_sampler: Generator):
        # We shuffle templates for each case to ensure the same template does not appear twice
        asset_template_sampler_map = self.template_manager.create_asset_template_sampler_map()
        assets = iter(case.assets)
        asset_facts = []
        remaining_asset_count = case.asset_count()
        while remaining_asset_count > 0:
            sample, remaining_asset_count = self.sample_and_exhaust(remaining_asset_count, 3, [0.65, 0.25, 0.1]) # Probability of one, two or three asset template, respectively
            hydrated = self.template_manager.sample_asset_template(asset_template_sampler_map, case.has_married_couple(), sample)
            for index in range(sample):
                name_variant = next(name_variant_sampler) if index == 0 else None
                asset = next(assets)
                hydrated = self.hydrate_asset_template(hydrated, asset, name_variant)
            asset_facts.append(hydrated)
        return asset_facts
    
    def create_solved_reasoning_steps(self, case_: Case, allowable_jurisdictions: List[Jurisdiction]):
        solved_steps = 'Solved Reasoning Steps:\n' + self.instructions['solved_steps'] + '\n'
        match TaskID(self.config.start_task_id):
            case TaskID.GOVERNING_JURISDICTIONS: # No solved reasoning steps
                return None
            case TaskID.ASSET_EXEMPTION_CLASSIFICATION:
                jurisdiction_names = ' and '.join(map(lambda jurisdiction: jurisdiction.display_name(), allowable_jurisdictions))
                solved_steps += f'The {case_.party_coreference()} may claim property exemptions under {jurisdiction_names} statutes.'
            case TaskID.ASSET_EXEMPTION_DOLLAR_VALUE:
                solved_steps += self.snippets[str(self.config.start_task_id) + '_solved_steps']
                solution = self.solve_case(case_, TaskID.ASSET_EXEMPTION_CLASSIFICATION, allowable_jurisdictions)
                for asset_description, citations in solution.items():
                    if not citations:
                        solved_steps += f'\nThere are no applicable exemptions for the {asset_description}.'
                    else:
                        solved_steps += f'\nThe {asset_description} may be exempted under {self.inflect_engine.join(citations)}.'
            case TaskID.NON_EXEMPT_ASSETS:
                solved_steps += self.snippets[str(self.config.start_task_id) + '_solved_steps']
                solution = self.solve_case(case_, TaskID.ASSET_EXEMPTION_DOLLAR_VALUE, allowable_jurisdictions)
                for asset_description, exemption_dicts in solution.items():
                    if not exemption_dicts:
                        solved_steps += f'\nThere are no applicable exemptions for the {asset_description}.'
                    else:
                        citations_with_values = list(map(lambda exemption_dict: f'{exemption_dict["citation"]} (${exemption_dict["claim_value"]:,})', exemption_dicts))
                        solved_steps += f'\nThe {asset_description} may be exempted under {self.inflect_engine.join(citations_with_values)}.'
            case TaskID.OPTIMAL_EXEMPTIONS:
                solved_steps += self.snippets[str(self.config.start_task_id) + '_solved_steps']
                solution = self.solve_case(case_, TaskID.NON_EXEMPT_ASSETS, allowable_jurisdictions)
                for jurisdiction, non_exempt_dollar_amount in solution.items():
                    solved_steps += f'\nUnder {jurisdiction} exemptions, the minimal total dollar value of non-exempt assets is ${non_exempt_dollar_amount:,}.'
            case _:
                raise ValueError(f'Encountered unsupported task ID: {self.config.start_task_id}')
        return solved_steps
    
    def solve_case(self, case_: Case, task_id: TaskID, allowable_jurisdictions: List[Jurisdiction]):
        match task_id:
            case TaskID.GOVERNING_JURISDICTIONS:
                return ', '.join(map(lambda jurisdiction: jurisdiction.display_name(), allowable_jurisdictions))
            case TaskID.ASSET_EXEMPTION_CLASSIFICATION:
                return self.solver.solve_asset_exemption_classification(case_, allowable_jurisdictions)
            case TaskID.ASSET_EXEMPTION_DOLLAR_VALUE:
                return self.solver.solve_asset_exemption_dollar_value(case_, allowable_jurisdictions)
            case TaskID.NON_EXEMPT_ASSETS:
                return self.solver.solve_non_exempt_assets(case_, allowable_jurisdictions)
            case TaskID.OPTIMAL_EXEMPTIONS:
                return self.solver.solve_optimal_exemptions(case_, allowable_jurisdictions)
            case _:
                raise ValueError(f'Encountered unsupported task ID: {task_id}')

    def generate_task(self, case: Case):
        instruction = self.instructions[str(self.config.terminal_task_id)]
        meta_instruction = self.instructions['meta']
        response_format = 'Response Format: ' + self.instructions[str(self.config.terminal_task_id) + '_response_format']
        name_variant_sampler = self.create_name_variant_sampler(case.debtor, case.joint_debtor)
        state_statute_set = self.statute_set_map[case.state_jurisdiction]
        allowable_jurisdictions = state_statute_set.allowable_exemption_jurisdictions()

        facts = 'Facts:\n' + self.create_preamble(case.debtor, case.joint_debtor, case.petition_date)
        if self.config.start_task_id == 1:
            domicile_facts = self.create_domicile_facts(case, name_variant_sampler)
            facts += ' ' + ' '.join(domicile_facts)
        if self.config.terminal_task_id > 1:
            asset_facts = self.create_asset_facts(case, name_variant_sampler)
            facts += ' ' + ' '.join(asset_facts)

        solved_steps = self.create_solved_reasoning_steps(case, allowable_jurisdictions)
        statute_set_content = [statute_set.display_content() for statute_set in self.statute_set_map.values()]
        statutes = 'Statutes:\n' + '\n\n'.join(statute_set_content)
        solution = self.solve_case(case, TaskID(self.config.terminal_task_id), allowable_jurisdictions)
        return TaskDataset.create_task(self.config.start_task_id,
                                       self.config.terminal_task_id,
                                       case.state_jurisdiction.value,
                                       instruction,
                                       meta_instruction,
                                       response_format,
                                       facts,
                                       solved_steps,
                                       statutes,
                                       solution)