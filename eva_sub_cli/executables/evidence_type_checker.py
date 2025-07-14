import argparse

import yaml
from ebi_eva_common_pyutils.logger import logging_config

from eva_sub_cli.file_utils import detect_vcf_evidence_type
from eva_sub_cli.metadata import EvaMetadataJson

logger = logging_config.get_logger(__name__)


def check_evidence_type(metadata_json, output_yaml):
    metadata = EvaMetadataJson(metadata_json)
    results_per_analysis_alias = {}

    for analysis_alias, vcf_file_set in metadata.files_per_analysis.items():
        results_per_analysis_alias[analysis_alias] = {
            'evidence_type': None,
            'errors': None
        }
        vcf_files = list(vcf_file_set)
        aggregations = [detect_vcf_evidence_type(vcf_file) for vcf_file in vcf_files]

        if len(set(aggregations)) == 1 and None not in aggregations:
            results_per_analysis_alias[analysis_alias]['evidence_type'] = set(aggregations).pop()
        elif None in aggregations:
            indices = [i for i, x in enumerate(aggregations) if x is None]
            results_per_analysis_alias[analysis_alias][
                'errors'] = f'VCF file evidence type could not be determined: {", ".join([vcf_files[i] for i in indices])}'
        else:
            results_per_analysis_alias[analysis_alias][
                'errors'] = f'Multiple evidence types found: {", ".join(set(aggregations))}'

    write_result_yaml(output_yaml, results_per_analysis_alias)


def write_result_yaml(output_yaml, results_per_analysis_alias):
    with open(output_yaml, 'w') as open_yaml:
        yaml.safe_dump(data=results_per_analysis_alias, stream=open_yaml, default_flow_style=False)


def main():
    arg_parser = argparse.ArgumentParser(description='Check the evidence type in the VCF files for all analysis')
    arg_parser.add_argument('--metadata_json', required=True, dest='metadata_json',
                            help='EVA metadata json file')
    arg_parser.add_argument('--output_yaml', required=True, dest='output_yaml',
                            help='Path to the location of the results')

    args = arg_parser.parse_args()
    logging_config.add_stdout_handler()
    check_evidence_type(args.metadata_json, args.output_yaml)
