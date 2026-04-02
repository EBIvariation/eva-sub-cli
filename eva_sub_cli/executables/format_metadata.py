import argparse
import json
from ebi_eva_common_pyutils.logger import logging_config
logger = logging_config.get_logger(__name__)

def format_experiment_type_lowercase(json_file):
    with open(json_file, 'r') as file:
        json_data = json.load(file)

    for index in range(len(json_data["analysis"])):
        logger.info(f"Formatting metadata - experiment type to lower case - {json_data["analysis"][index]["experimentType"]}")
        json_data["analysis"][index]["experimentType"] = json_data["analysis"][index]["experimentType"].lower()

    with open(json_file, 'w') as file:
        json.dump(json_data, file, indent=4)
    return json_file

def main():
    arg_parser = argparse.ArgumentParser(
        description='Formats experiment type for the metadata.')
    arg_parser.add_argument('--metadata_json', required=True, dest='metadata_json',
                            help='EVA metadata json file')
    args = arg_parser.parse_args()
    format_experiment_type_lowercase(args.metadata_json)

if __name__ == "__main__":
    main()