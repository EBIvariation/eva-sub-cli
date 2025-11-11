import csv
import os
import re
import subprocess
import time

from ebi_eva_common_pyutils.logger import logging_config
from retry import retry

from eva_sub_cli.validators.validator import Validator, ALL_VALIDATION_TASKS

logger = logging_config.get_logger(__name__)

default_container_image = 'ebivariation/eva-sub-cli'
default_container_tag = 'v0.0.8'
container_validation_dir = '/opt/vcf_validation'
container_validation_output_dir = 'vcf_validation_output'


class DockerValidator(Validator):

    def __init__(self, mapping_file, submission_dir, project_title, metadata_json=None,
                 metadata_xlsx=None, metadata_xlsx_version=None, validation_tasks=ALL_VALIDATION_TASKS,
                 shallow_validation=False, docker_path='docker', submission_config=None, container_image=None,
                 container_tag=None, container_name=None):
        super().__init__(mapping_file, submission_dir, project_title, metadata_json=metadata_json,
                         metadata_xlsx=metadata_xlsx, metadata_xlsx_version=metadata_xlsx_version,
                         validation_tasks=validation_tasks, shallow_validation=shallow_validation,
                         submission_config=submission_config)
        self.docker_path = docker_path
        submission_basename = re.sub('[^a-zA-Z0-9]', '', os.path.basename(submission_dir))
        self.container_image = container_image or default_container_image
        self.container_tag = container_tag or default_container_tag
        self.container_name = container_name or f'{self.container_image.split("/")[1]}.{self.container_tag}.{submission_basename}'

    def _validate(self):
        self.run_docker_validator()

    @staticmethod
    def _validation_file_path_for(file_path):
        return f'{container_validation_dir}/{file_path}'

    def get_docker_validation_cmd(self):
        docker_cmd = ''.join([
            f"{self.docker_path} exec {self.container_name} nextflow run eva_sub_cli/nextflow/validation.nf ",
            f"--base_dir {container_validation_dir} ",
            f"--tasks {','.join(self.tasks)} "
            f"--vcf_files_mapping {self.mapping_file} ",
            f"--metadata_xlsx {self.metadata_xlsx} ",
            f"--conversion_configuration_name {self._get_xlsx_conversion_configuration_name()} "
            if self.metadata_xlsx and not self.metadata_json else f"--metadata_json {self.metadata_json} ",
            f"--shallow_validation true " if self.shallow_validation else "",
            f"--output_dir {container_validation_output_dir}"
        ])
        return docker_cmd

    def run_docker_validator(self):
        # check if docker container is ready for running validation
        self.verify_docker_is_installed()
        self.download_container_image_if_needed()
        self.run_container_if_required()
        try:
            # remove all existing files from container
            self._run_quiet_command(
                "Remove existing files from validation directory in container",
                f"{self.docker_path} exec {self.container_name} rm -rf work {container_validation_dir}"
            )

            # copy all required files to container (mapping file, vcf and fasta)
            self.copy_files_to_container()
            # create the output directory
            self._run_quiet_command(
                "Create output directory in container",
                f"{self.docker_path} exec {self.container_name} mkdir -p {container_validation_dir}/{container_validation_output_dir}"
            )

            docker_cmd = self.get_docker_validation_cmd()
            # start validation
            self._run_quiet_command("Run Validation using Nextflow", docker_cmd)
        except subprocess.CalledProcessError as ex:
            logger.error(ex)
        finally:
            # copy validation result to user host
            self._run_quiet_command(
                "Copy validation output from container to host",
                f"{self.docker_path} cp {self.container_name}:{container_validation_dir}/{container_validation_output_dir}/. {self.output_dir}"
            )
            self.stop_running_container()

    def verify_docker_is_installed(self):
        try:
            self._run_quiet_command(
                "check docker is installed and available on the path",
                f"{self.docker_path} --version"
            )
        except subprocess.CalledProcessError as ex:
            logger.error(ex)
            raise RuntimeError(f"Please make sure docker ({self.docker_path}) is installed and available on the path")

    def verify_container_is_running(self):
        try:
            container_run_cmd_output = self._run_quiet_command("check if container is running", f"{self.docker_path} ps", return_process_output=True)
            if container_run_cmd_output is not None and self.container_name in container_run_cmd_output:
                logger.debug(f"Container ({self.container_name}) is running")
                return True
            else:
                logger.debug(f"Container ({self.container_name}) is not running")
                return False
        except subprocess.CalledProcessError as ex:
            logger.error(ex)
            raise RuntimeError(f"Please make sure docker ({self.docker_path}) is installed and running in the background")

    def verify_container_is_stopped(self):
        container_stop_cmd_output = self._run_quiet_command(
            "check if container is stopped", f"{self.docker_path} ps -a",  return_process_output=True
        )
        if container_stop_cmd_output is not None and self.container_name in container_stop_cmd_output:
            logger.debug(f"Container ({self.container_name}) is in stop state")
            return True
        else:
            logger.debug(f"Container ({self.container_name}) is not in stop state")
            return False

    def try_restarting_container(self):
        logger.info(f"Trying to restart container {self.container_name}")
        try:
            self._run_quiet_command("Try restarting container", f"{self.docker_path} start {self.container_name}")
            if not self.verify_container_is_running():
                raise RuntimeError(f"Container ({self.container_name}) could not be restarted")
        except subprocess.CalledProcessError as ex:
            logger.error(ex)
            raise RuntimeError(f"Container ({self.container_name}) could not be restarted")

    def verify_image_available_locally(self):
        container_images_cmd_ouptut = self._run_quiet_command(
            "Check if validator image is present",
            f"{self.docker_path} images",
            return_process_output=True
        )
        if container_images_cmd_ouptut is not None and re.search(self.container_image + r'\s+' + self.container_tag, container_images_cmd_ouptut):
            logger.debug(f"Container ({self.container_image}) image is available locally")
            return True
        else:
            logger.debug(f"Container ({self.container_image}) image is not available locally")
            return False

    def run_container_if_required(self):
        if self.verify_container_is_running():
            raise RuntimeError(f"Container ({self.container_name}) is already running. "
                               f"Did you start multiple validation for the same directory ?")
        if self.verify_container_is_stopped():
            logger.warn(f"Container {self.container_name} was stopped but not cleaned up before.")
            self.try_restarting_container()
        else:
            logger.debug(f"Trying to start container {self.container_name}")
            try:
                self._run_quiet_command(
                    "Running container",
                    f"{self.docker_path} run -it --rm -d --name {self.container_name} {self.container_image}:{self.container_tag}"
                )
                # Wait to give some time to container to get up and running
                time.sleep(5)
                if not self.verify_container_is_running():
                    raise RuntimeError(f"Container ({self.container_name}) could not be started")
            except subprocess.CalledProcessError as ex:
                logger.error(ex)
                raise RuntimeError(f"Container ({self.container_name}) could not be started")

    def stop_running_container(self):
        if self.verify_container_is_running():
            self._run_quiet_command(
                "Stop the running container",
                f"{self.docker_path} stop {self.container_name}"
            )

    @retry(RuntimeError, tries=3, delay=5, backoff=1, jitter=2, logger=logger)
    def download_container_image_if_needed(self):
        if not self.verify_image_available_locally():
            logger.debug(f"Pulling container ({self.container_image}) image")
            try:
                self._run_quiet_command("pull container image",
                                        f"{self.docker_path} pull {self.container_image}:{self.container_tag}")
            except subprocess.CalledProcessError as ex:
                logger.error(ex)
                raise RuntimeError(f"Cannot pull container ({self.container_image}) image")
            # Give the pull command some time to complete
            time.sleep(5)

    def copy_files_to_container(self):
        def _copy(file_description, file_path):
            self._run_quiet_command(
                f"Create directory structure for copying {file_description} into container",
                (f"{self.docker_path} exec {self.container_name} "
                 f"mkdir -p {container_validation_dir}/{os.path.dirname(file_path)}")
            )
            self._run_quiet_command(
                f"Copy {file_description} to container",
                (f"{self.docker_path} cp {file_path} "
                 f"{self.container_name}:{container_validation_dir}/{file_path}")
            )
        _copy('vcf metadata file', self.mapping_file)
        if self.metadata_json:
            _copy('json metadata file', self.metadata_json)
        if self.metadata_xlsx:
            _copy('excel metadata file', self.metadata_xlsx)
        with open(self.mapping_file) as open_file:
            reader = csv.DictReader(open_file, delimiter=',')
            for row in reader:
                _copy('vcf files', row['vcf'])
                _copy('fasta files', row['fasta'])
                # report is optional
                if row.get('report'):
                    _copy('assembly report files', row['report'])
