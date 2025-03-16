import os
import json
from typing import List
from .asset import Asset
from .utils import file_names_with_extension, read_jsonl_file, write_jsonl_file


class AssetFactory:

    # Save all assets to a single jsonl file
    @staticmethod
    def save_assets(assets: List[Asset], directory: str, file_name: str = 'assets.jsonl'):
        if not os.path.exists(directory):
            os.mkdir(directory)
        file_path = os.path.join(directory, file_name)
        # We do not overwrite assets
        assert not os.path.exists(file_path), f'Asset file with this name already exists: {file_path}'
        asset_dicts = [asset.to_dict() for asset in assets]
        write_jsonl_file(file_path, asset_dicts)

    # Save each asset as its own json file
    @staticmethod
    def save_assets_files(assets: List[Asset], directory: str):
        if not os.path.exists(directory):
            os.mkdir(directory)
        file_names = file_names_with_extension(directory, 'json')
        existing_assets = list(map(lambda file_name: os.path.splitext(file_name)[0], file_names))

        asset_index = 0
        for asset in assets:
            # We do not overwrite assets
            asset_name = f'asset_{asset_index}'
            while asset_name in existing_assets:
                asset_index += 1
                asset_name = f'asset_{asset_index}'
            asset_path = os.path.join(directory, asset_name + '.json')
            with open(asset_path, 'w') as file:
                json.dump(asset.to_dict(), file, indent=4)
            asset_index += 1

    # Load a jsonl file containing multiple assets
    @staticmethod
    def load_assets(directory: str, file_name: str = 'assets.jsonl'):
        file_path = os.path.join(directory, file_name)
        asset_dicts = read_jsonl_file(file_path)
        return [Asset(**asset_dict) for asset_dict in asset_dicts]

    # Load all assets from a directory where each asset is stored as its own json file
    @staticmethod
    def load_asset_files(directory: str):
        assets = []
        for file_name in file_names_with_extension(directory, 'json'):
            asset_path = os.path.join(directory, file_name)
            with open(asset_path, 'r') as file:
                asset_dict = json.load(file)
            assets.append(Asset(**asset_dict))
        return assets
