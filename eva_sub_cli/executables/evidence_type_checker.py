import argparse

import yaml
from ebi_eva_common_pyutils.logger import logging_config

from eva_sub_cli.file_utils import detect_vcf_evidence_type, associate_vcf_path_with_analysis
from eva_sub_cli.metadata import EvaMetadataJson

logger = logging_config.get_logger(__name__)


def check_evidence_type(metadata_json, vcf_files, output_yaml):
    metadata = EvaMetadataJson(metadata_json)
    file_path_per_analysis = associate_vcf_path_with_analysis(metadata, vcf_files)

    results_per_analysis_alias = {}

    all_analysis_alias = set(metadata.files_per_analysis) | set(file_path_per_analysis)
    for analysis_alias in all_analysis_alias:
        results_per_analysis_alias[analysis_alias] = {
            'evidence_type': None,
            'errors': None
        }
        vcf_files = list(file_path_per_analysis.get(analysis_alias, []))

        if not vcf_files:
            results_per_analysis_alias[analysis_alias]['errors'] = f'No VCF file found for the analysis'
            continue

        evidence_types_for_vcf_files = [detect_vcf_evidence_type(vcf_file) for vcf_file in vcf_files]

        if len(set(evidence_types_for_vcf_files)) == 1 and None not in evidence_types_for_vcf_files:
            results_per_analysis_alias[analysis_alias]['evidence_type'] = set(evidence_types_for_vcf_files).pop()
        elif None in evidence_types_for_vcf_files:
            indices = [i for i, x in enumerate(evidence_types_for_vcf_files) if x is None]
            results_per_analysis_alias[analysis_alias][
                'errors'] = f'VCF file evidence type could not be determined: {", ".join([vcf_files[i] for i in indices])}'
        else:
            results_per_analysis_alias[analysis_alias][
                'errors'] = f'Multiple evidence types found: {", ".join(set(evidence_types_for_vcf_files))}'

    write_result_yaml(output_yaml, results_per_analysis_alias)


def write_result_yaml(output_yaml, results_per_analysis_alias):
    with open(output_yaml, 'w') as open_yaml:
        yaml.safe_dump(data=results_per_analysis_alias, stream=open_yaml, default_flow_style=False)


def main():
    arg_parser = argparse.ArgumentParser(description='Check the evidence type in the VCF files for all analysis')
    arg_parser.add_argument('--metadata_json', required=True, dest='metadata_json',
                            help='EVA metadata json file')
    arg_parser.add_argument('--vcf_files', dest='vcf_files', nargs='+',
                            help='Path to the vcf files to compare to the metadata')
    arg_parser.add_argument('--output_yaml', required=True, dest='output_yaml',
                            help='Path to the location of the results')

    args = arg_parser.parse_args()
    logging_config.add_stdout_handler()
    check_evidence_type(args.metadata_json, args.vcf_files, args.output_yaml)
