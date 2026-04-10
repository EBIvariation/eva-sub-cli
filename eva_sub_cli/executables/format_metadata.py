#!/usr/bin/env python3
import argparse
import json
from ebi_eva_common_pyutils.logger import logging_config
logger = logging_config.get_logger(__name__)

def format_experiment_type_lowercase(json_file_input, json_file_output):
    with open(json_file_input, 'r') as input:
        json_data = json.load(input)

    for index in range(len(json_data["analysis"])):
        logger.info(f"Formatting metadata - experiment type to lower case - {json_data['analysis'][index]['experimentType']}")
        json_data["analysis"][index]["experimentType"] = json_data["analysis"][index]["experimentType"].lower()

    with open(json_file_output, 'w') as output:
        json.dump(json_data, output, indent=4)
    return json_file_output

def main():
    arg_parser = argparse.ArgumentParser(
        description='Formats experiment type for the metadata.')
    arg_parser.add_argument('--metadata_json_input', required=True, dest='metadata_json_input',
                            help='EVA metadata json file INPUT')
    arg_parser.add_argument('--metadata_json_output', required=True, dest='metadata_json_output',
                            help='EVA metadata json file OUTPUT')
    args = arg_parser.parse_args()
    format_experiment_type_lowercase(args.metadata_json_input, args.metadata_json_output)

if __name__ == "__main__":
    main()