import json
import logging
import os
import shutil
import subprocess
from unittest import TestCase

import yaml
from ebi_eva_common_pyutils.command_utils import run_command_with_output
from ebi_eva_common_pyutils.logger import logging_config

from eva_sub_cli.validators.docker_validator import DockerValidator
from tests.test_utils import create_mapping_file

logger = logging_config.get_logger(__name__)


class TestDockerValidator(TestCase):
    resources_folder = os.path.join(os.path.dirname(__file__), 'resources')
    vcf_files = os.path.join(resources_folder, 'vcf_files')
    fasta_files = os.path.join(resources_folder, 'fasta_files')
    assembly_reports = os.path.join(resources_folder, 'assembly_reports')

    test_run_dir_json = os.path.join(resources_folder, 'docker_test_run_json')
    test_run_dir_xlsx = os.path.join(resources_folder, 'docker_test_run_xlsx')
    mapping_file = os.path.join(test_run_dir_json, 'vcf_files_metadata.csv')
    metadata_json = os.path.join(test_run_dir_json, 'sub_metadata.json')
    metadata_xlsx = os.path.join(test_run_dir_xlsx, 'sub_metadata.xlsx')

    docker_path = 'docker'
    docker_build_context = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
    docker_file_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'docker', 'Dockerfile'))
    container_image = 'eva-sub-cli-test'
    container_tag = 'test-latest'
    container_name = f'{container_image}.{container_tag}'
    container_validation_dir = '/opt/vcf_validation'
    container_validation_output_dir = 'vcf_validation_output'

    project_title = 'test_project_title'

    def setUp(self):
        # build docker image for test
        self.build_docker_image_for_test()

        for d in [self.test_run_dir_json, self.test_run_dir_xlsx]:
            if os.path.exists(d):
                shutil.rmtree(d)

        os.makedirs(self.test_run_dir_json, exist_ok=True)
        os.makedirs(self.test_run_dir_xlsx, exist_ok=True)

        # create vcf mapping file
        create_mapping_file(self.mapping_file,
                            [os.path.join(self.vcf_files, 'input_passed.vcf')],
                            [os.path.join(self.fasta_files, 'input_passed.fa')],
                            [os.path.join(self.assembly_reports, 'input_passed.txt')])

        sub_metadata = self.get_submission_json_metadata()
        with open(self.metadata_json, 'w') as open_metadata:
            json.dump(sub_metadata, open_metadata)

        self.validator = DockerValidator(
            mapping_file=self.mapping_file,
            submission_dir=self.test_run_dir_json,
            project_title=self.project_title,
            metadata_json=self.metadata_json,
            container_image=self.container_image,
            container_tag=self.container_tag,
            container_name=self.container_name
        )

        shutil.copyfile(
            os.path.join(self.resources_folder, 'EVA_Submission_Docker_Test.xlsx'),
            self.metadata_xlsx
        )

        self.xlsx_validator = DockerValidator(
            mapping_file=self.mapping_file,
            submission_dir=self.test_run_dir_xlsx,
            project_title=self.project_title,
            metadata_xlsx=self.metadata_xlsx,
            container_image=self.container_image,
            container_tag=self.container_tag,
            container_name=self.container_name
        )

    def tearDown(self):
        for d in [self.test_run_dir_json, self.test_run_dir_xlsx]:
            if os.path.exists(d):
                shutil.rmtree(d)
        self.validator.stop_running_container()
        self.xlsx_validator.stop_running_container()

    def build_docker_image_for_test(self):
        self.stop_and_remove_test_container()
        self.remove_existing_test_image()
        self.build_docker_image()

    def stop_and_remove_test_container(self):
        try:
            self._run_quiet_command(
                "stop and remove docker test container",
                f"{self.docker_path} rm -f {self.container_name} || true"
            )
        except subprocess.CalledProcessError as ex:
            logger.error(ex)
            raise RuntimeError(
                f"Please make sure docker ({self.docker_path}) is installed and available on the path. {ex}")

    def remove_existing_test_image(self):
        try:
            self._run_quiet_command(
                "remove existing docker test image",
                f"{self.docker_path} rmi {self.container_image}:{self.container_tag} || true"
            )
        except subprocess.CalledProcessError as ex:
            logger.error(ex)
            raise RuntimeError(
                f"Please make sure docker ({self.docker_path}) is installed and available on the path. {ex}")

    def build_docker_image(self):
        try:
            self._run_quiet_command(
                "build docker image for test",
                f"{self.docker_path} build -t {self.container_image}:{self.container_tag} -f {self.docker_file_path} {self.docker_build_context}"
            )
        except subprocess.CalledProcessError as ex:
            logger.error(ex)
            raise RuntimeError(
                f"Please make sure docker ({self.docker_path}) is installed and available on the path. {ex}")

    @staticmethod
    def _run_quiet_command(command_description, command, **kwargs):
        return run_command_with_output(command_description, command, stdout_log_level=logging.DEBUG,
                                       stderr_log_level=logging.DEBUG, **kwargs)

    def test_validate_with_json(self):
        self.validator.validate()

        expected_sample_checker = self.get_expected_sample()
        expected_metadata_val = 'Validation passed successfully.'
        expected_semantic_val = {'description': 'SAME123 does not exist or is private',
                                 'property': '/sample/0/bioSampleAccession'}
        expected_evidence_type_val = {'AA': {'evidence_type': 'genotype', 'errors': None}}
        expected_metadata_files_json = [
            {'analysisAlias': 'AA', 'fileName': 'input_passed.vcf', 'fileType': 'vcf',
             'md5': '96a80c9368cc3c37095c86fbe6044fb2', 'fileSize': 45050}
        ]

        self.assert_validation_results(self.validator, expected_sample_checker, expected_metadata_files_json,
                                       expected_metadata_val, expected_semantic_val, expected_evidence_type_val)

    def test_validate_with_xlsx(self):
        self.xlsx_validator.validate()

        expected_sample_checker = self.get_expected_sample()
        expected_metadata_val = 'Validation passed successfully.'
        expected_semantic_val = {'description': 'SAME123 does not exist or is private',
                                 'property': '/sample/0/bioSampleAccession'}
        expected_evidence_type_val = {'AA': {'evidence_type': 'genotype', 'errors': None}}
        expected_metadata_files_json = [
            {'analysisAlias': 'AA', 'fileName': 'input_passed.vcf',
             'md5': '96a80c9368cc3c37095c86fbe6044fb2', 'fileSize': 45050}
        ]

        self.assert_validation_results(self.xlsx_validator, expected_sample_checker, expected_metadata_files_json,
                                       expected_metadata_val, expected_semantic_val, expected_evidence_type_val)

    def get_submission_json_metadata(self):
        return {
            "submitterDetails": [
                {
                    "firstName": "test_user_first_name",
                    "lastName": "test_user_last_name",
                    "email": "test_user_email@abc.com",
                    "laboratory": "test_user_laboratory",
                    "centre": "test_user_centre",
                }
            ],
            "project": {
                "title": "test_project_title",
                "description": "test_project_description",
                "taxId": 1234,
                "centre": "test_project_centre"
            },
            "analysis": [
                {
                    "analysisTitle": "test_analysis_title",
                    "analysisAlias": "AA",
                    "description": "test_analysis_description",
                    "experimentType": "Whole genome sequencing",
                    "referenceGenome": "test_analysis_reference_genome",
                }
            ],
            "sample": [
                {
                    "analysisAlias": ["AA"],
                    "sampleInVCF": "HG00096",
                    "bioSampleAccession": "SAME123"
                }
            ],
            "files": [
                {
                    "analysisAlias": "AA",
                    "fileName": 'input_passed.vcf',
                    "fileType": "vcf"
                }
            ]
        }

    def get_expected_sample(self):
        return {
            'overall_differences': False,
            'results_per_analysis': {
                'AA': {
                    'difference': False,
                    'more_metadata_submitted_files': [],
                    'more_per_submitted_files_metadata': {},
                    'more_submitted_files_metadata': []
                }
            }
        }

    def get_docker_validation_cmd(self):
        docker_cmd = ''.join([
            f"{self.docker_path} exec {self.container_name} nextflow run eva_sub_cli/nextflow/validation.nf ",
            f"--base_dir {self.container_validation_dir} ",
            f"--vcf_files_mapping {self.mapping_file} ",
            f"--metadata_json {self.metadata_json} ",
            f"--output_dir {self.container_validation_output_dir}"
        ])
        return docker_cmd

    def assert_validation_results(self, validator, expected_sample_checker, expected_metadata_files_json,
                                  expected_metadata_val, expected_semantic_val, expected_evidence_type_val):
        vcf_format_dir = os.path.join(validator.output_dir, 'vcf_format')
        self.assertTrue(os.path.exists(vcf_format_dir))

        vcf_format_log_file = os.path.join(vcf_format_dir, 'input_passed.vcf.vcf_format.log')
        self.assertTrue(os.path.exists(vcf_format_log_file))

        with open(vcf_format_log_file) as vcf_format_log_file:
            vcf_format_logs = vcf_format_log_file.readlines()
            self.assertEqual('[info] According to the VCF specification, the input file is valid\n',
                             vcf_format_logs[2])
            text_report = vcf_format_logs[1].split(':')[1].strip()
            with open(os.path.join(validator.output_dir, text_report)) as text_report:
                text_report_content = text_report.readlines()
                self.assertEqual('According to the VCF specification, the input file is valid\n',
                                 text_report_content[0])

        # assert assembly report
        assembly_check_dir = os.path.join(validator.output_dir, 'assembly_check')
        self.assertTrue(os.path.exists(assembly_check_dir))

        assembly_check_log_file = os.path.join(assembly_check_dir, 'input_passed.vcf.assembly_check.log')
        self.assertTrue(os.path.exists(assembly_check_log_file))

        with open(assembly_check_log_file) as assembly_check_log_file:
            assembly_check_logs = assembly_check_log_file.readlines()
            self.assertEqual('[info] Number of matches: 247/247\n', assembly_check_logs[4])
            self.assertEqual('[info] Percentage of matches: 100%\n', assembly_check_logs[5])

        # Assert Samples concordance
        self.assert_yaml_file(validator._sample_check_yaml, expected_sample_checker)

        # assert evidence type check
        self.assert_yaml_file(validator._evidence_type_check_yaml, expected_evidence_type_val)

        with open(validator.metadata_json_post_validation) as open_file:
            json_data = json.load(open_file)
            assert json_data.get('files') == expected_metadata_files_json

        # Check metadata errors
        with open(os.path.join(validator.output_dir, 'other_validations', 'metadata_validation.txt')) as open_file:
            metadata_val_lines = {l.strip() for l in open_file.readlines()}
            assert any((expected_metadata_val in line for line in metadata_val_lines))

        # Check semantic metadata errors
        semantic_yaml_file = os.path.join(validator.output_dir, 'other_validations', 'metadata_semantic_check.yml')
        self.assertTrue(os.path.isfile(semantic_yaml_file))
        with open(semantic_yaml_file) as open_yaml:
            semantic_output = yaml.safe_load(open_yaml)
            assert semantic_output[0] == expected_semantic_val

    def assert_yaml_file(self, yaml_file, expected_data):
        self.assertTrue(os.path.isfile(yaml_file))
        with open(yaml_file) as open_yaml:
            self.assert_same_dict_and_unordered_list(yaml.safe_load(open_yaml), expected_data)

    def assert_same_dict_and_unordered_list(self, o1, o2):
        if isinstance(o1, dict) and isinstance(o2, dict):
            self.assertEqual(set(o1), set(o2))
            [self.assert_same_dict_and_unordered_list(o1.get(k), o2.get(k)) for k in o1]
        elif isinstance(o1, list) and isinstance(o2, list):
            self.assertEqual(set(o1), set(o2))
        else:
            self.assertEqual(o1, o2)
