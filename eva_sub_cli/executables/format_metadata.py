import argparse
from ebi_eva_common_pyutils.logger import logging_config
logger = logging_config.get_logger(__name__)

def format_experiment_type_lowercase(json):
    for index in range(len(json["analysis"])):
        logger.info(f"Formating metadata - experiment type to lower case - {json["analysis"][index]["experimentType"]}")
        json["analysis"][index]["experimentType"] = json["analysis"][index]["experimentType"].lower()
    return json

def main():
    arg_parser = argparse.ArgumentParser(
        description='Formats experiment type for the metadata.')
    arg_parser.add_argument('--metadata_json', required=True, dest='metadata_json',
                            help='EVA metadata json file')
    args = arg_parser.parse_args()
    format_experiment_type_lowercase(args.metadata_json)

if __name__ == "__main__":
    main()