#!/usr/bin/env python
import argparse
import gzip
import json
import os
import pathlib

from collections import defaultdict
from ebi_eva_common_pyutils.logger import logging_config

import yaml


logger = logging_config.get_logger(__name__)


def open_gzip_if_required(input_file):
    if input_file.endswith('.gz'):
        return gzip.open(input_file, 'rt')
    else:
        return open(input_file, 'r')


def get_samples_from_vcf(vcf_file):
    """
    Get the list of samples present in a single VCF file
    """
    with open_gzip_if_required(vcf_file) as vcf_in:
        for line in vcf_in:
            if line.startswith('#CHROM'):
                sp_line = line.strip().split('\t')
                if len(sp_line) > 9:
                    return sp_line[9:]
                else:
                    logger.warning(f"No Sample names found in file {vcf_file}")
                    return []


def compare_names_in_files_and_samples(sample_name_in_analysis, sample_name_per_file):
    """
    Compare the sample names provided in vcf files and the one provided in a set of sample rows.
    This is meant to compare the samples and files provided for a single analysis.
    """
    has_difference = False
    sample_names_in_vcf = set(
        sample_name
        for sample_name_list in sample_name_per_file.values()
        for sample_name in sample_name_list
    )
    more_metadata_submitted_files = list(sample_name_in_analysis - sample_names_in_vcf)
    more_submitted_files_metadata = list(sample_names_in_vcf - sample_name_in_analysis)
    more_per_submitted_files_metadata = {}
    if more_submitted_files_metadata:
        for file_name in sample_name_per_file:
            more_per_submitted_files_metadata[os.path.basename(file_name)] = list(set(sample_name_per_file[file_name]) - set(sample_name_in_analysis))
        has_difference = True

    if more_metadata_submitted_files:
        has_difference = True

    return (has_difference, more_per_submitted_files_metadata, more_submitted_files_metadata,
            more_metadata_submitted_files)


def compare_all_analysis(samples_per_analysis, files_per_analysis):
    overall_differences = False
    results_per_analysis_alias = {}
    for analysis_alias in samples_per_analysis:
        sample_name_in_analysis = samples_per_analysis[analysis_alias]
        sample_name_per_file = {
            file_path: get_samples_from_vcf(file_path)
            for file_path in files_per_analysis[analysis_alias]
        }
        (
            has_difference, more_per_submitted_files_metadata,
            more_submitted_files_metadata, more_metadata_submitted_files
        ) = compare_names_in_files_and_samples(sample_name_in_analysis, sample_name_per_file)
        overall_differences = overall_differences or has_difference
        results_per_analysis_alias[analysis_alias] = {
            'difference': has_difference,
            'more_per_submitted_files_metadata': more_per_submitted_files_metadata,
            'more_submitted_files_metadata': more_submitted_files_metadata,
            'more_metadata_submitted_files': more_metadata_submitted_files
        }
    return overall_differences, results_per_analysis_alias


def read_metadata_json(json_file):
    with open(json_file) as open_json:
        metadata = json.load(open_json)
        samples_per_analysis = defaultdict(list)
        files_per_analysis = defaultdict(list)
        for sample_info in metadata['sample']:
            samples_per_analysis[sample_info.get('analysisAlias')].append(sample_info.get('sampleInVCF'))
        for file_info in metadata['file']:
            if file_info.get('fileType') == 'vcf':
                files_per_analysis[file_info.get('analysisAlias')].append(file_info.get('fileName'))
        return (
            {analysis_alias: set(samples) for analysis_alias, samples in samples_per_analysis.items()},
            {filepath: set(samples) for filepath, samples in files_per_analysis.items()}
        )


def resolve_vcf_file_location(vcf_dir_prefix, files_per_analysis):
    result_files_per_analysis = {}
    for analysis_alias in files_per_analysis:
        result_files_per_analysis[analysis_alias] = []
        for f in files_per_analysis[analysis_alias]:
            if vcf_dir_prefix:
                # Remove leading / to ensure Join concatenate the path
                if os.path.isabs(f):
                    file_path = os.path.join(vcf_dir_prefix, *pathlib.Path(f).parts[1:])
                else:
                    file_path = os.path.join(vcf_dir_prefix, f)
            else:
                file_path = os.path.abspath(f)
            print(f, vcf_dir_prefix, file_path)
            if os.path.exists(file_path):
                result_files_per_analysis[analysis_alias].append(file_path)
            else:
                raise FileNotFoundError(f'{file_path} cannot be resolved')
    return result_files_per_analysis


def write_result_yaml(output_yaml, overall_differences, results_per_analysis_alias):
    with open(output_yaml, 'w') as open_yaml:
        yaml.safe_dump(data={
            'overall_differences': overall_differences,
            'results_per_analysis': results_per_analysis_alias
        }, stream=open_yaml)


def check_sample_name_concordance(metadata_json, vcf_dir_prefix, output_yaml):
    """
    Take the metadata following EVA standard and  formatted in JSON then compare the sample names in it to the ones
    found in the VCF files
    """
    samples_per_analysis, files_per_analysis = read_metadata_json(metadata_json)
    files_per_analysis = resolve_vcf_file_location(vcf_dir_prefix, files_per_analysis)
    overall_differences, results_per_analysis_alias = compare_all_analysis(samples_per_analysis, files_per_analysis)
    write_result_yaml(output_yaml, overall_differences, results_per_analysis_alias)


def main():
    arg_parser = argparse.ArgumentParser(
        description='Compare the sample name in the VCF file and the one specified in the metadata.')
    arg_parser.add_argument('--metadata_json', required=True, dest='metadata_json',
                            help='EVA metadata json file')
    arg_parser.add_argument('--vcf_dir_prefix', dest='vcf_dir_prefix',
                            help='Path to the directory which prefix the path provided in the metadata. concatenation '
                                 'of the two is where the submitted files can be found')
    arg_parser.add_argument('--output_yaml', required=True, dest='output_yaml',
                            help='Path to the location of the results')

    args = arg_parser.parse_args()
    logging_config.add_stdout_handler()
    check_sample_name_concordance(args.metadata_json, args.vcf_dir_prefix, args.output_yaml)


if __name__ == "__main__":
    main()
