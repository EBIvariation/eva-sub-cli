import os
import subprocess

from ebi_eva_common_pyutils.logger import logging_config

from eva_sub_cli.validators.validator import Validator, ALL_VALIDATION_TASKS

logger = logging_config.get_logger(__name__)


class NativeValidator(Validator):

    def __init__(self, mapping_file, submission_dir, project_title, metadata_json=None, metadata_xlsx=None,

                 metadata_xlsx_version=None, validation_tasks=ALL_VALIDATION_TASKS, shallow_validation=False, vcf_validator_path='vcf_validator',
                 assembly_checker_path='vcf_assembly_checker', biovalidator_path='biovalidator',
                 submission_config=None, nextflow_config=None):
        super().__init__(mapping_file, submission_dir, project_title, metadata_json=metadata_json,
                         metadata_xlsx=metadata_xlsx, metadata_xlsx_version=metadata_xlsx_version,
                         validation_tasks=validation_tasks, shallow_validation=shallow_validation,
                         submission_config=submission_config)
        self.nextflow_config = nextflow_config
        self.vcf_validator_path = vcf_validator_path
        self.assembly_checker_path = assembly_checker_path
        self.biovalidator_path = biovalidator_path

    @staticmethod
    def _validation_file_path_for(file_path):
        return file_path

    def _validate(self):
        self.run_validator()

    def run_validator(self):
        self.verify_executables_installed()
        curr_wd = os.getcwd()
        try:
            command = self.get_validation_cmd()
            os.chdir(self.submission_dir)
            self._run_quiet_command("Run Validation using Nextflow", command)
        except subprocess.CalledProcessError as ex:
            logger.error(ex)
        finally:
            os.chdir(curr_wd)

    def get_validation_cmd(self):
        if self.metadata_xlsx and not self.metadata_json:
            metadata_flag = f"--metadata_xlsx {self.metadata_xlsx} "
            metadata_flag += f"--conversion_configuration_name {self._get_xlsx_conversion_configuration_name()}"
        else:
            metadata_flag = f"--metadata_json {self.metadata_json}"
        path_to_workflow = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                        'nextflow/validation.nf')
        return ''.join([
            f"nextflow run {path_to_workflow}",
            f" --tasks {','.join(self.tasks)} "
            f" --vcf_files_mapping {self.mapping_file}",
            f" {metadata_flag}",
            f" --output_dir {self.output_dir}",
            f" --shallow_validation true " if self.shallow_validation else "",
            f" --executable.vcf_validator {self.vcf_validator_path}",
            f" --executable.vcf_assembly_checker {self.assembly_checker_path}",
            f" --executable.biovalidator {self.biovalidator_path}",
            f" -c {self.nextflow_config} " if self.nextflow_config else ""
        ])

    def verify_executables_installed(self):
        for name, path in [('vcf-validator', self.vcf_validator_path),
                           ('vcf-assembly-checker', self.assembly_checker_path),
                           ('biovalidator', self.biovalidator_path)]:
            try:
                self._run_quiet_command(
                    f"Check {name} is installed and available on the path",
                    f"{path} --version"
                )
            except subprocess.CalledProcessError as ex:
                logger.error(ex)
                raise RuntimeError(f"Please make sure {name} ({path}) is installed and available on the path")
