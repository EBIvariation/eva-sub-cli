import argparse
import csv
import os
import subprocess
import time

from cli import ETC_DIR
from cli.reporter import Reporter
from ebi_eva_common_pyutils.logger import logging_config

logger = logging_config.get_logger(__name__)

container_image = 'eva_sub_cli'
container_validation_dir = '/opt/vcf_validation'
container_validation_output_dir = '/opt/vcf_validation/vcf_validation_output'
container_etc_dir = '/opt/cli/etc'


def run_command_with_output(command_description, command, return_process_output=True,
                            log_error_stream_to_output=False):
    process_output = ""

    logger.info(f"Starting process: {command_description}")
    logger.info(f"Running command: {command}")

    stdout = subprocess.PIPE
    # Some utilities output non-error messages to error stream. This is a workaround for that
    stderr = subprocess.STDOUT if log_error_stream_to_output else subprocess.PIPE
    with subprocess.Popen(command, stdout=stdout, stderr=stderr, bufsize=1, universal_newlines=True,
                          shell=True) as process:
        for line in iter(process.stdout.readline, ''):
            line = str(line).rstrip()
            logger.info(line)
            if return_process_output:
                process_output += line + "\n"
        if not log_error_stream_to_output:
            for line in iter(process.stderr.readline, ''):
                line = str(line).rstrip()
                logger.error(line)
    if process.returncode != 0:
        logger.error(f"{command_description} - failed! Refer to the error messages for details.")
        raise subprocess.CalledProcessError(process.returncode, process.args)
    else:
        logger.info(f"{command_description} - completed successfully")
    if return_process_output:
        return process_output


class DockerValidator(Reporter):

    def __init__(self, mapping_file, output_dir, metadata_json=None,
                 metadata_xlsx=None, container_name=container_image, docker_path='docker'):
        self.docker_path = docker_path
        self.mapping_file = mapping_file
        self.metadata_json = metadata_json
        self.metadata_xlsx = metadata_xlsx
        self.container_name = container_name
        self.spreadsheet2json_conf = os.path.join(ETC_DIR, "spreadsheet2json_conf.yaml")
        super().__init__(self._find_vcf_file(), output_dir)

    def _validate(self):
        self.run_docker_validator()

    def _find_vcf_file(self):
        vcf_files = []
        with open(self.mapping_file) as open_file:
            reader = csv.DictReader(open_file, delimiter=',')
            for row in reader:
                vcf_files.append(row['vcf'])
        return vcf_files

    def get_docker_validation_cmd(self):
        if self.metadata_xlsx and not self.metadata_json:
            docker_cmd = (
                f"{self.docker_path} exec {self.container_name} nextflow run cli/nextflow/validation.nf "
                f"--vcf_files_mapping {container_validation_dir}/{self.mapping_file} "
                f"--metadata_xlsx {container_validation_dir}/{self.metadata_xlsx} "
                f"--conversion_configuration {container_validation_dir}/{self.spreadsheet2json_conf} "
                f"--schema_dir {container_etc_dir} "
                f"--output_dir {container_validation_output_dir}"
            )
        else:
            docker_cmd = (
                f"{self.docker_path} exec {self.container_name} nextflow run cli/nextflow/validation.nf "
                f"--vcf_files_mapping {container_validation_dir}/{self.mapping_file} "
                f"--metadata_json {container_validation_dir}/{self.metadata_json} "
                f"--schema_dir {container_etc_dir} "
                f"--output_dir {container_validation_output_dir}"
            )
        return docker_cmd

    def run_docker_validator(self):
        # verify mapping file exists
        if not os.path.exists(self.mapping_file):
            raise RuntimeError(f'Mapping file {self.mapping_file} not found')

        # verify all files mentioned in metadata files exist
        files_missing, missing_files_list = self.check_if_file_missing()
        if files_missing:
            raise RuntimeError(f"some files (vcf/fasta) mentioned in metadata file could not be found. "
                               f"Missing files list {missing_files_list}")

        # check if docker container is ready for running validation
        self.verify_docker_env()

        try:
            # remove all existing files from container
            run_command_with_output(
                "Remove existing files from validation directory in container",
                f"{self.docker_path} exec {self.container_name} rm -rf work {container_validation_dir}"
            )

            # copy all required files to container (mapping file, vcf and fasta)
            self.copy_files_to_container()

            docker_cmd = self.get_docker_validation_cmd()
            # start validation
            # FIXME: If nextflow fails in the docker exec still exit with error code 0
            run_command_with_output("Run Validation using Nextflow", docker_cmd)
            # copy validation result to user host
            run_command_with_output(
                "Copy validation output from container to host",
                f"{self.docker_path} cp {self.container_name}:{container_validation_output_dir} {self.output_dir}"
            )
        except subprocess.CalledProcessError as ex:
            logger.error(ex)

    def check_if_file_missing(self):
        files_missing = False
        missing_files_list = []
        with open(self.mapping_file) as open_file:
            reader = csv.DictReader(open_file, delimiter=',')
            for row in reader:
                if not os.path.exists(row['vcf']):
                    files_missing = True
                    missing_files_list.append(row['vcf'])
                if not os.path.exists(row['fasta']):
                    files_missing = True
                    missing_files_list.append(row['fasta'])
                if not os.path.exists(row['report']):
                    files_missing = True
                    missing_files_list.append(row['report'])

        return files_missing, missing_files_list

    def verify_docker_is_installed(self):
        try:
            run_command_with_output(
                "check docker is installed and available on the path",
                f"{self.docker_path} --version"
            )
        except subprocess.CalledProcessError as ex:
            logger.error(ex)
            raise RuntimeError(f"Please make sure docker ({self.docker_path}) is installed and available on the path")

    def verify_container_is_running(self):
        container_run_cmd_ouptut = run_command_with_output("check if container is running", f"{self.docker_path} ps")
        if container_run_cmd_ouptut is not None and self.container_name in container_run_cmd_ouptut:
            logger.info(f"Container ({self.container_name}) is running")
            return True
        else:
            logger.info(f"Container ({self.container_name}) is not running")
            return False

    def verify_container_is_stopped(self):
        container_stop_cmd_output = run_command_with_output(
            "check if container is stopped",
            f"{self.docker_path} ps -a"
        )
        if container_stop_cmd_output is not None and self.container_name in container_stop_cmd_output:
            logger.info(f"Container ({self.container_name}) is in stop state")
            return True
        else:
            logger.info(f"Container ({self.container_name}) is not in stop state")
            return False

    def try_restarting_container(self):
        logger.info(f"Trying to restart container {self.container_name}")
        try:
            run_command_with_output("Try restarting container", f"{self.docker_path} start {self.container_name}")
            if not self.verify_container_is_running():
                raise RuntimeError(f"Container ({self.container_name}) could not be restarted")
        except subprocess.CalledProcessError as ex:
            logger.error(ex)
            raise RuntimeError(f"Container ({self.container_name}) could not be restarted")

    def verify_image_available_locally(self):
        container_images_cmd_ouptut = run_command_with_output(
            "Check if validator image is present",
            f"{self.docker_path} images"
        )
        if container_images_cmd_ouptut is not None and container_image in container_images_cmd_ouptut:
            logger.info(f"Container ({container_image}) image is available locally")
            return True
        else:
            logger.info(f"Container ({container_image}) image is not available locally")
            return False

    def run_container(self):
        logger.info(f"Trying to run container {self.container_name}")
        try:
            run_command_with_output(
                "Try running container",
                f"{self.docker_path} run -it --rm -d --name {self.container_name} {container_image}"
            )
            # stopping execution to give some time to container to get up and running
            time.sleep(5)
            if not self.verify_container_is_running():
                raise RuntimeError(f"Container ({self.container_name}) could not be started")
        except subprocess.CalledProcessError as ex:
            logger.error(ex)
            raise RuntimeError(f"Container ({self.container_name}) could not be started")

    def stop_running_container(self):
        if not self.verify_container_is_stopped():
            run_command_with_output(
                "Stop the running container",
                f"{self.docker_path} stop --name {self.container_name}"
            )

    def download_container_image(self):
        logger.info(f"Pulling container ({container_image}) image")
        try:
            run_command_with_output("pull container image", f"{self.docker_path} pull {container_image}")
            if not self.run_container():
                raise RuntimeError(f"Container ({self.container_name}) could not be started")
        except subprocess.CalledProcessError as ex:
            logger.error(ex)
            raise RuntimeError(f"Cannot pull container ({container_image}) image")

    def verify_docker_env(self):
        self.verify_docker_is_installed()

        if not self.verify_container_is_running():
            if self.verify_container_is_stopped():
                self.try_restarting_container()
            else:
                if self.verify_image_available_locally():
                    self.run_container()
                else:
                    self.download_container_image()

    def copy_files_to_container(self):
        def _copy(file_description, file_path):
            run_command_with_output(
                f"Create directory structure for copying {file_description} into container",
                (f"{self.docker_path} exec {self.container_name} "
                 f"mkdir -p {container_validation_dir}/{os.path.dirname(file_path)}")
            )
            run_command_with_output(
                f"Copy {file_description} to container",
                (f"{self.docker_path} cp {file_path} "
                 f"{self.container_name}:{container_validation_dir}/{file_path}")
            )
        _copy('vcf metadata file', self.mapping_file)
        if self.metadata_json:
            _copy('json metadata file', self.metadata_json)
        if self.metadata_xlsx:
            _copy('excel metadata file', self.metadata_xlsx)
            _copy('configuration', self.spreadsheet2json_conf)
        with open(self.mapping_file) as open_file:
            reader = csv.DictReader(open_file, delimiter=',')
            for row in reader:
                _copy('vcf files', row['vcf'])
                _copy('fasta files', row['fasta'])
                _copy('assembly report files', row['report'])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run pre-submission validation checks on VCF files', add_help=False)
    parser.add_argument("--docker_path", help="Full path to the docker installation, "
                                              "not required if docker is available on path", required=False)
    parser.add_argument("--container_name", help="Name of the docker container", required=False)
    parser.add_argument("--vcf_files_mapping",
                        help="csv file with the mappings for vcf files, fasta and assembly report", required=True)
    parser.add_argument("--output_dir", help="Directory where the validation output reports will be made available",
                        required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--metadata_json",
                       help="Json file that describe the project, analysis, samples and files")
    group.add_argument("--metadata_xlsx",
                       help="Excel spreadsheet  that describe the project, analysis, samples and files")
    args = parser.parse_args()

    docker_path = args.docker_path if args.docker_path else 'docker'
    docker_container_name = args.container_name if args.container_name else container_image

    logging_config.add_stdout_handler()
    validator = DockerValidator(args.vcf_files_mapping, args.output_dir, args.metadata_json, args.metadata_xlsx,
                                docker_container_name, docker_path)
    validator.validate()
    validator.create_reports()
