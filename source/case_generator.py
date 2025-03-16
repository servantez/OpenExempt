import os
import string
import random
from math import ceil
from typing import Dict
from datetime import datetime, timedelta
from .config import Config
from .jurisdiction import Jurisdiction
from .party import Party
from .case import Case
from .asset_factory import AssetFactory
from .utils import read_jsonl_file, infinite_sampler, infinite_sample


class CaseGenerator:

    def __init__(self, config: Config):
        self.config = config
        self.party_sampler = infinite_sampler(self.load_parties(self.config.data_directory))
        self.asset_sampler = infinite_sampler(AssetFactory.load_assets(self.config.asset_directory))
        self.jurisdiction_sampler = self.create_jurisdiction_sampler()
        self.is_married_sampler = self.create_is_married_sampler()
        self.residence_count_sampler = self.create_domicile_count_sampler()

    def load_parties(self, data_directory: str):
        file_path = os.path.join(data_directory, 'parties.jsonl')
        party_dicts = read_jsonl_file(file_path)
        return list(map(lambda party_dict: Party(**party_dict), party_dicts))
    
    def create_jurisdiction_sampler(self):
        count_per_jurisdiction = ceil(self.config.dataset_size / self.config.state_jurisdiction_count())
        jurisdiction_list = []
        for jurisdiction in self.config.state_jurisdictions:
            jurisdiction_list.extend([jurisdiction] * count_per_jurisdiction)
        return infinite_sampler(jurisdiction_list)
    
    def create_is_married_sampler(self):
        married_count = round(self.config.dataset_size * self.config.married_percentage)
        is_married_list = [True] * married_count + [False] * (self.config.dataset_size - married_count)
        return infinite_sampler(is_married_list)
    
    def create_domicile_count_sampler(self):
        lower = self.config.domicile_count_min
        upper = self.config.domicile_count_max + 1 # Plus one to make upper bound inclusive
        domicile_count_list = [count for count in range(lower, upper)]
        domicile_count_list = domicile_count_list * (self.config.dataset_size // len(domicile_count_list))
        return infinite_sampler(domicile_count_list)
    
    def sample_party(self):
        return next(self.party_sampler)
    
    def sample_assets(self, asset_count: int):
        return infinite_sample(self.asset_sampler, asset_count)
    
    def sample_is_married(self):
        return next(self.is_married_sampler)
    
    def sample_jurisdiction(self):
        return next(self.jurisdiction_sampler)
    
    def sample_domicile_count(self):
        return next(self.residence_count_sampler)
    
    def sample_petition_date(self):
        first_day = datetime(2024, 1, 1)
        last_day = datetime(2024, 12, 31)
        total_days = (last_day - first_day).days
        random_day = random.randint(0, total_days)
        return first_day + timedelta(days=random_day)
    
    def sample_domicile_dates(self, petition_date: datetime, domicile_count: int):
        # Create first domicile date which occurred before (730 + 180) day period (see 11 U.S.C. 522(b)(3)(A))
        lookback_period = 730 + 180 + 1
        twenty_years_prior = petition_date.replace(year=2004)
        total_days = (petition_date - twenty_years_prior).days
        random_day = random.randint(lookback_period, total_days)
        first_date = petition_date - timedelta(days=random_day)

        # Create remaining domicile dates within (730 + 180) day period
        remaining_days = random.sample(range(lookback_period), domicile_count - 1)
        remaining_days.sort(reverse=True)
        remaining_dates = [petition_date - timedelta(days=days) for days in remaining_days]
        return [first_date] + remaining_dates
    
    def create_domicile_dates(self, petition_date: datetime, domicile_count: int, state_jurisdiction: Jurisdiction):
        applicable_state_placeholder = None
        # Its possible (albeit rare) for the applicable state jurisdiction to be ambiguous
        # This occurs when two states are tied for most days domiciled
        # When this happens, we simply reroll
        while applicable_state_placeholder == None:
            dates = self.sample_domicile_dates(petition_date, domicile_count)
            # Randomly assign placeholders to each date
            # Placeholders are used to ensure applicable state matches jurisdiction argument
            placeholders = list(string.ascii_lowercase[:self.config.state_jurisdiction_count()])
            assignments = random.choices(placeholders, k=len(dates))
            placeholder_dates = dict(zip(dates, assignments))
            applicable_state_placeholder = self.determine_applicable_state_jurisdiction(petition_date, placeholder_dates)

        # Create final domicile dates by replacing placeholders with state jurisdictions
        states = self.config.state_jurisdictions.copy()
        states.remove(state_jurisdiction.value)
        random.shuffle(states)
        state_index = 0
        assigned_placeholders = {applicable_state_placeholder: state_jurisdiction}
        domicile_dates = {}
        for date, placeholder in placeholder_dates.items():
            if placeholder not in assigned_placeholders:
                assigned_placeholders[placeholder] = Jurisdiction(states[state_index])
                state_index += 1
            domicile_dates[date] = assigned_placeholders[placeholder]
        return domicile_dates

    def determine_applicable_state_jurisdiction(self, petition_date: datetime, domicile_dates: Dict[datetime, str]):
        # Evaluate 730-day period prior to petition date
        two_years_prior = petition_date - timedelta(days=730)
        domicile_count = len(domicile_dates)
        dates = list(domicile_dates.keys())
        days_per_state = {}
        for index, (date, label) in enumerate(domicile_dates.items()):
            current_date = max(date, two_years_prior) # Only consider past two years
            if index < (domicile_count - 1):
                next_date = max(dates[index + 1], two_years_prior)
            else: # Last date
                next_date = petition_date
            delta = (next_date - current_date).days
            if delta > 0:
                if label not in days_per_state:
                    days_per_state[label] = 0
                days_per_state[label] += delta

        # If domiciled in a single state for 730-period, return that state
        if len(days_per_state) == 1:
            return next(iter(days_per_state))
        
        # Evaluate the 180 days prior to 730-day period
        two_and_half_years_prior = petition_date - timedelta(days=730 + 180)
        days_per_state = {}
        for index, (date, label) in enumerate(domicile_dates.items()):
            if date >= two_years_prior:
                continue
            current_date = max(date, two_and_half_years_prior)
            if index < (domicile_count - 1):
                next_date = min(dates[index + 1], two_years_prior)
            else: # Last date
                next_date = petition_date
            delta = (next_date - current_date).days
            if delta > 0:
                if label not in days_per_state:
                    days_per_state[label] = 0
                days_per_state[label] += delta

        # If domiciled in a single state for 180-period, return that state
        if len(days_per_state) == 1:
            return next(iter(days_per_state))
        
        sorted_days_per_state = dict(sorted(days_per_state.items(), key=lambda item: item[1]))
        sorted_iter = iter(sorted_days_per_state.items())
        first_state = next(sorted_iter)
        second_state = next(sorted_iter)

        # If two states are tied for most days domiciled, return None
        if first_state[1] == second_state[1]:
            return None
        return first_state[0]

    def generate_case(self):
        is_married = self.sample_is_married()
        asset_count = random.randint(self.config.asset_count_min, self.config.asset_count_max)
        state_jurisdiction = self.sample_jurisdiction()
        debtor = self.sample_party()
        if is_married:
            joint_debtor = self.sample_party()
            joint_debtor.last_name = debtor.last_name
        else:
            joint_debtor = None
        assets = self.sample_assets(asset_count)
        state_jurisdiction = Jurisdiction(self.sample_jurisdiction())
        petition_date = self.sample_petition_date()
        domicile_count = self.sample_domicile_count()
        domicile_dates = self.create_domicile_dates(petition_date, domicile_count, state_jurisdiction)
        return Case(debtor, 
                    joint_debtor, 
                    assets, 
                    state_jurisdiction, 
                    petition_date,
                    domicile_dates)