import os
import json
from collections.abc import Generator
from .utils import infinite_sampler, infinite_sample


class TemplateManager:

    def __init__(self, config):
        self.template_directory = config.template_directory
        self.date_format_sampler = infinite_sampler(self.read_json_file_in_template_directory('date_formats.json'))
        self.domicile_templates = self.read_json_file_in_template_directory('domicile_templates.json')
        self.asset_templates = self.create_asset_templates()
        self.obfuscation_sampler_map = self.create_obfuscation_sampler_map()

    def read_json_file_in_template_directory(self, file_name: str):
        path = os.path.join(self.template_directory, file_name)
        with open(path, 'r') as file:
            return json.load(file)
        
    def create_asset_templates(self):
        asset_templates = {}
        template_map = self.read_json_file_in_template_directory('asset_templates.json')
        for key, templates in template_map.items():
            if key.endswith('single') or key.endswith('couple'):
                # Remove single or couple suffix to get base key
                index = key.rfind('_')
                base_key = key[:index]
                asset_templates[key] = template_map[key] + template_map[base_key]
        return asset_templates
        
    def create_domicile_template_sampler_map(self):
        return {key: infinite_sampler(template) for key, template in self.domicile_templates.items()}
    
    def create_asset_template_sampler_map(self):
        return {key: infinite_sampler(template) for key, template in self.asset_templates.items()}
    
    def create_obfuscation_sampler_map(self):
        sampler_map = {}
        obfuscation_templates = self.read_json_file_in_template_directory('obfuscation_templates.json')
        for obfuscation_type, fact_type_dict in obfuscation_templates.items():
            sampler_map[obfuscation_type] = {}
            for fact_type, templates in fact_type_dict.items():
                sampler_map[obfuscation_type][fact_type] = infinite_sampler(templates)
        return sampler_map

    def sample_date_format(self):
        return next(self.date_format_sampler)
    
    def sample_domicile_template(self, sampler_map: Generator, location_count: int):
        assert location_count == 1 or location_count == 2, 'Domicile templates only support one or two locations.'
        key = 'one_location' if location_count == 1 else 'two_locations'
        return next(sampler_map[key])
        
    def sample_asset_template(self, sampler_map: Generator, is_married: bool, asset_count: int):
        assert asset_count >= 1 and asset_count <= 3, 'Asset templates only support one to three assets.'
        if asset_count == 1:
            key = 'one_asset_couple' if is_married else 'one_asset_single'
        elif asset_count == 2:
            key = 'two_assets_couple' if is_married else 'two_assets_single'
        else:
            key = 'three_assets_couple' if is_married else 'three_assets_single'
        return next(sampler_map[key])
    
    def sample_irrelevant_asset_template(self):
        return next(self.obfuscation_sampler_map['irrelevant_facts']['asset'])

    def sample_irrelevant_domicile_template(self):
        return next(self.obfuscation_sampler_map['irrelevant_facts']['domicile'])

    def sample_asset_opinion_template(self):
        return next(self.obfuscation_sampler_map['opinions']['asset'])

    def sample_domicile_opinion_template(self):
        return next(self.obfuscation_sampler_map['opinions']['domicile'])