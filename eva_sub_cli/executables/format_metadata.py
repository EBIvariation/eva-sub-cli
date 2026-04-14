#!/usr/bin/env python3
import argparse
import json
import shutil

from ebi_eva_common_pyutils.logger import logging_config
logger = logging_config.get_logger(__name__)

def format_experiment_type(json_file_input, json_file_output):
    try:
        with open(json_file_input, 'r') as input:
            json_data = json.load(input)

        for analysis_item in json_data.get("analysis", []):
            original_experiment_type = analysis_item.get("experimentType", "")
            logger.info(f"Formatting metadata - experiment type to capitalized - {original_experiment_type}")
            experiment_type_capital = original_experiment_type.capitalize()
            analysis_item["experimentType"] = experiment_type_capital or ""

        with open(json_file_output, 'w') as output:
            json.dump(json_data, output, indent=4)
        return json_file_output

    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        # if the try block fails, copy the input file (because nextflow is expecting the output file).
        logger.error(f"Failed to process JSON: {e}")
        shutil.copy(json_file_input, json_file_output)
        return None


def main():
    arg_parser = argparse.ArgumentParser(
        description='Formats experiment type for the metadata.')
    arg_parser.add_argument('--metadata_json_input', required=True, dest='metadata_json_input',
                            help='EVA metadata json file INPUT')
    arg_parser.add_argument('--metadata_json_output', required=True, dest='metadata_json_output',
                            help='EVA metadata json file OUTPUT')
    args = arg_parser.parse_args()
    format_experiment_type(args.metadata_json_input, args.metadata_json_output)

if __name__ == "__main__":
    main()