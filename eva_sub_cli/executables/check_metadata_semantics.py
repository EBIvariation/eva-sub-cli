import argparse
import json

import yaml

from eva_sub_cli.semantic_metadata import SemanticMetadataChecker


def main():
    arg_parser = argparse.ArgumentParser(description='Perform semantic checks on the metadata')
    arg_parser.add_argument('--metadata_json', required=True, dest='metadata_json', help='EVA metadata json file')
    arg_parser.add_argument('--evidence_type_results', required=True, dest='evidence_type_results', help='Results of the evidence check')
    arg_parser.add_argument('--output_yaml', required=True, dest='output_yaml',
                            help='Path to the location of the results')
    args = arg_parser.parse_args()

    with open(args.metadata_json) as open_json:
        metadata = json.load(open_json)
    with open(args.evidence_type_results) as open_yaml:
        evidence_type_results = yaml.safe_load(open_yaml)
    checker = SemanticMetadataChecker(metadata, evidence_type_results)
    checker.check_all()
    checker.write_result_yaml(args.output_yaml)
