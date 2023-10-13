#!/usr/bin/env python
import csv
import os
from argparse import ArgumentParser

from ebi_eva_common_pyutils.config import WritableConfig
from ebi_eva_common_pyutils.logger import logging_config

from eva_sub_cli import SUB_CLI_CONFIG_FILE, __version__
from eva_sub_cli.docker_validator import DockerValidator, docker_path, container_image
from eva_sub_cli.reporter import READY_FOR_SUBMISSION_TO_EVA
from eva_sub_cli.submit import StudySubmitter

VALIDATION_OUTPUT_DIR = "validation_output"
VALIDATE = 'validate'
SUBMIT = 'submit'
RESUME_SUBMISSION = 'resume_submission'

logging_config.add_stdout_handler()


def get_docker_validator(vcf_files_mapping, output_dir, metadata_json, metadata_xlsx,
                         arg_container, arg_docker, sub_config):
    docker = arg_docker or docker_path
    container = arg_container or container_image
    validation_output_dir = os.path.join(output_dir, VALIDATION_OUTPUT_DIR)
    return DockerValidator(vcf_files_mapping, validation_output_dir, metadata_json, metadata_xlsx,
                           container, docker, sub_config)

def get_vcf_files(mapping_file):
    vcf_files = []
    with open(mapping_file) as open_file:
        reader = csv.DictReader(open_file, delimiter=',')
        for row in reader:
            vcf_files.append(row['vcf'])
    return vcf_files

if __name__ == "__main__":
    argparser = ArgumentParser(description='EVA Submission CLI - validate and submit data to EVA')
    argparser.add_argument('--task', required=True, choices=[VALIDATE, SUBMIT, RESUME_SUBMISSION],
                           help='Select a task to perform')
    argparser.add_argument('--submission_dir', required=True, type=str,
                           help='Full path to the directory where all processing will be done '
                                'and submission info is/will be stored')
    argparser.add_argument("--vcf_files_mapping", required=True,
                           help="csv file with the mappings for vcf files, fasta and assembly report")
    group = argparser.add_mutually_exclusive_group(required=True)
    group.add_argument("--metadata_json",
                       help="Json file that describe the project, analysis, samples and files")
    group.add_argument("--metadata_xlsx",
                       help="Excel spreadsheet  that describe the project, analysis, samples and files")
    argparser.add_argument("--docker_path", required=False, help="Full path to the docker installation, "
                                                                 "not required if docker is available in the PATH environment variable")
    argparser.add_argument("--container_name", required=False, help="Name of the docker container")

    args = argparser.parse_args()

    # load config
    config_file_path = os.path.join(args.submission_dir, SUB_CLI_CONFIG_FILE)
    sub_config = WritableConfig(config_file_path, version=__version__)

    vcf_files = get_vcf_files(args.vcf_files_mapping)
    metadata_file = args.metadata_json or args.metadata_xlsx

    if args.task == RESUME_SUBMISSION:
        # if validation is not passed, process task submit (validate and submit)
        if READY_FOR_SUBMISSION_TO_EVA not in sub_config or not sub_config[READY_FOR_SUBMISSION_TO_EVA]:
            args.task = SUBMIT
        else:
            # if validation is passed, upload files without validating again
            with StudySubmitter(args.submission_dir, vcf_files, metadata_file, submission_config=sub_config) as submitter:
                submitter.upload_submission()

    if args.task == VALIDATE or args.task == SUBMIT:
        docker_validator = get_docker_validator(args.vcf_files_mapping, args.submission_dir, args.metadata_json,
                                                args.metadata_xlsx, args.container_name, args.docker_path, sub_config)
        docker_validator.validate()
        docker_validator.create_reports()
        docker_validator.update_config_with_validation_result()

    if args.task == SUBMIT:
        with StudySubmitter(args.submission_dir, vcf_files, metadata_file, submission_config=sub_config) as submitter:
            submitter.submit()
