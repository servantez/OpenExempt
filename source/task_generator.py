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
from .task_id import TaskID
from .task_dataset import Task
from .jurisdiction import Jurisdiction
from .statute_factory import StatuteFactory
from .template_manager import TemplateManager
from .solver import Solver
from .utils import infinite_sampler


class TaskGenerator:

    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(self.config.dataset_name)
        self.inflect_engine = inflect.engine()
        self.template_manager = TemplateManager(config)
        self.instructions = self.read_json_file_in_data_directory('instructions.json')
        self.snippets = self.read_json_file_in_data_directory('snippets.json')
        self.city_sampler = self.create_city_sampler()
        self.state_sampler = self.create_state_sampler()
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
        city_dict = self.read_json_file_in_data_directory('cities.json')
        for state, city_list in city_dict.items():
            if state.upper() in self.config.state_jurisdictions:
                jurisdiction = Jurisdiction(state.upper())
                city_sampler[jurisdiction] = infinite_sampler(city_list)
        return city_sampler
    
    def create_state_sampler(self):
        city_dict = self.read_json_file_in_data_directory('cities.json')
        return infinite_sampler(list(city_dict.keys()))
    
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
    
    def random_party_name_variant(self, case: Case):
        random_party = random.choice(case.parties())
        name_variant_sampler = self.create_name_variant_sampler(random_party)
        return next(name_variant_sampler)
    
    def sample_city_in_state(self, state: str):
        return next(self.city_sampler[state])
    
    def sample_state(self):
        return next(self.state_sampler)
    
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
        return Task.create_task(1, 5, 'WISCONSIN', 'instruction', 'meta_instruction', 'response_format', 'context', 'solution')
    
    def hydrate_party_name(self, template: str, name_variant: str):
        name = name_variant
        if template.startswith('{party}') and name_variant.startswith('the'):
            name = name[0].upper() + name[1:]
        return template.replace('{party}', name)

    def hydrate_domicile_template(self, template: str, date: datetime, state: Jurisdiction, name_variant: str = None):
        city = self.sample_city_in_state(state)
        hydrated = template.replace('{location}', f'{city}, {state.display_name()}', 1)
        date_format = self.template_manager.sample_date_format()
        formatted_date = self.format_date(date, date_format)
        hydrated = hydrated.replace('{date}', formatted_date, 1)
        if name_variant:
            hydrated = self.hydrate_party_name(hydrated, name_variant)
        return hydrated
    
    def hydrate_asset_template(self, template: str, asset: Asset, name_variant: str = None):
        hydrated = self.format_asset_description(asset, template)
        hydrated = hydrated.replace('{value}', asset.formatted_dollar_value(), 1)
        if name_variant:
            hydrated = self.hydrate_party_name(hydrated, name_variant)
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
    
    def add_asset_obfuscation(self, case: Case, asset_facts: List[str]):
        # Check if irrelevant asset facts should be added
        if self.config.irrelevant_asset_facts:
            # Sample an irrelevant asset fact and insert it at a random index
            template = self.template_manager.sample_irrelevant_asset_template()
            irrelevant_fact = self.hydrate_party_name(template, self.random_party_name_variant(case))
            random_index = random.randint(0, len(asset_facts))
            asset_facts.insert(random_index, irrelevant_fact)
        # Check if asset opinions should be added
        if self.config.asset_opinions:
            # Sample an asset opinion and insert it at a random index
            template = self.template_manager.sample_asset_opinion_template()
            opinion = self.hydrate_party_name(template, self.random_party_name_variant(case))
            random_index = random.randint(1, len(asset_facts)) # Opinions should not be at the beginning
            asset_facts.insert(random_index, opinion)
        return asset_facts

    def add_domicile_obfuscation(self, case: Case, domicile_facts: List[str]):
        # Check if irrelevant domicile facts should be added
        fact_insertion_index = None
        if self.config.irrelevant_domicile_facts:
            # Sample an irrelevant domicile fact and insert it at a random index
            template = self.template_manager.sample_irrelevant_domicile_template()
            irrelevant_fact = template.replace('{jurisdiction}', self.sample_state())
            irrelevant_fact = self.hydrate_party_name(irrelevant_fact, self.random_party_name_variant(case))
            fact_insertion_index = random.randint(1, len(domicile_facts)) # Irrelevant domicile facts should not be at the beginning
            domicile_facts.insert(fact_insertion_index, irrelevant_fact)
        # Check if domicile opinions should be added
        if self.config.domicile_opinions:
            # Sample a domicile opinion and insert it at a random index
            template = self.template_manager.sample_domicile_opinion_template()
            opinion = template.replace('{jurisdiction}', self.sample_state())
            opinion = self.hydrate_party_name(opinion, self.random_party_name_variant(case))
            # Ensure opinion is not inserted immediately before an irrelevant fact.
            valid_insertions = [index for index in range(0, len(domicile_facts) + 1) if index != fact_insertion_index]
            opinion_insertion_index = random.choice(valid_insertions)
            domicile_facts.insert(opinion_insertion_index, opinion)
        return domicile_facts
    
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
        domicile_facts = self.add_domicile_obfuscation(case, domicile_facts)
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
        asset_facts = self.add_asset_obfuscation(case, asset_facts)
        return asset_facts
    
    def create_solved_reasoning_steps(self, case_: Case, allowable_jurisdictions: List[Jurisdiction]):
        solved_steps = 'Solved Reasoning Steps:\n' + self.instructions['solved_steps'] + '\n'
        match TaskID(self.config.start_task_id):
            case TaskID.GOVERNING_JURISDICTION: # No solved reasoning steps
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
            case TaskID.GOVERNING_JURISDICTION:
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
        return Task.create_task(self.config.start_task_id,
                                       self.config.terminal_task_id,
                                       case.state_jurisdiction.value,
                                       instruction,
                                       meta_instruction,
                                       response_format,
                                       facts,
                                       solved_steps,
                                       statutes,
                                       solution)