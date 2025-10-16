import json
import os
import shutil
import subprocess
from unittest import TestCase
from unittest.mock import patch

import yaml

from eva_sub_cli import MINIMUM_METADATA_XLSX_TEMPLATE_VERSION
from eva_sub_cli.orchestrator import verify_and_get_metadata_xlsx_version
from eva_sub_cli.validators.docker_validator import DockerValidator
from tests.test_utils import create_mapping_file


class TestDockerValidator(TestCase):
    resources_folder = os.path.join(os.path.dirname(__file__), 'resources')
    project_title = 'Example Project'
    vcf_files = os.path.join(resources_folder, 'vcf_files')
    fasta_files = os.path.join(resources_folder, 'fasta_files')
    assembly_reports = os.path.join(resources_folder, 'assembly_reports')

    test_run_dir1 = os.path.join(resources_folder, 'docker_test_run1')
    test_run_dir2 = os.path.join(resources_folder, 'docker_test_run2')
    mapping_file = os.path.join(test_run_dir1, 'vcf_files_metadata.csv')
    metadata_json = os.path.join(test_run_dir1, 'sub_metadata.json')
    metadata_xlsx = os.path.join(test_run_dir2, 'sub_metadata.xlsx')


    def setUp(self):
        os.makedirs(self.test_run_dir1, exist_ok=True)
        os.makedirs(self.test_run_dir2, exist_ok=True)

        # create vcf mapping file
        create_mapping_file(self.mapping_file,
                            [os.path.join(self.vcf_files, 'input_passed.vcf')],
                            [os.path.join(self.fasta_files, 'input_passed.fa')],
                            [os.path.join(self.assembly_reports, 'input_passed.txt')])
        sub_metadata = {
            "submitterDetails": [],
            "project": {
                "parentProject": "PRJ_INVALID"
            },
            "sample": [
                {"analysisAlias": ["AA"], "sampleInVCF": "HG00096", "bioSampleAccession": "SAME123"}
            ],
            "analysis": [
                {"analysisAlias": "AA"}
            ],
            "files": [
                {"analysisAlias": "AA", "fileName": 'input_passed.vcf', "fileType": "vcf"}
            ]
        }
        with open(self.metadata_json, 'w') as open_metadata:
            json.dump(sub_metadata, open_metadata)
        self.validator = DockerValidator(
            mapping_file=self.mapping_file,
            submission_dir=self.test_run_dir1,
            project_title=self.project_title,
            metadata_json=self.metadata_json
        )
        shutil.copyfile(
            os.path.join(self.resources_folder, 'EVA_Submission_test.xlsx'),
            self.metadata_xlsx
        )
        metadata_xlsx_version = verify_and_get_metadata_xlsx_version(self.metadata_xlsx, MINIMUM_METADATA_XLSX_TEMPLATE_VERSION)

        self.validator_from_excel = DockerValidator(
            mapping_file=self.mapping_file,
            submission_dir=self.test_run_dir2,
            project_title=self.project_title,
            metadata_xlsx=self.metadata_xlsx,
            metadata_xlsx_version=metadata_xlsx_version
        )

    def tearDown(self):
        for d in [self.test_run_dir1, self.test_run_dir2]:
            if os.path.exists(d):
                shutil.rmtree(d)
        self.validator.stop_running_container()
        self.validator_from_excel.stop_running_container()

    def assert_same_dict_and_unordered_list(self, o1, o2):
        if isinstance(o1, dict) and isinstance(o2, dict):
            self.assertEqual(set(o1), set(o2))
            [self.assert_same_dict_and_unordered_list(o1.get(k), o2.get(k)) for k in o1]
        elif isinstance(o1, list) and isinstance(o2, list):
            self.assertEqual(set(o1), set(o2))
        else:
            self.assertEqual(o1, o2)

    def assert_sample_checker(self, sample_checker_file, expected_checker):
        self.assertTrue(os.path.isfile(sample_checker_file))
        with open(sample_checker_file) as open_yaml:
            self.assert_same_dict_and_unordered_list(yaml.safe_load(open_yaml), expected_checker)

    def assert_validation_results(self, validator, expected_sample_checker, expected_metadata_files_json,
                               expected_metadata_val, expected_semantic_val):
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
        self.assert_sample_checker(validator._sample_check_yaml, expected_sample_checker)

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
            assert semantic_output[1] == expected_semantic_val

    def test_validate(self):
        # run validation in docker
        self.validator.validate()
        expected_sample_checker = {
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
        expected_metadata_files_json = [
            {'analysisAlias': 'AA', 'fileName': 'input_passed.vcf', 'fileType': 'vcf',
             'md5': '96a80c9368cc3c37095c86fbe6044fb2', 'fileSize': 45050}
        ]
        expected_metadata_val = 'must match pattern "^PRJ(E|D|N)[A-Z][0-9]+$"'
        expected_semantic_val = {'description': 'SAME123 does not exist or is private',
                                          'property': '/sample/0/bioSampleAccession'}

        self.assert_validation_results(self.validator, expected_sample_checker, expected_metadata_files_json,
                                       expected_metadata_val, expected_semantic_val)

    def test_validate_from_excel(self):
        self.validator_from_excel.validate()
        expected_sample_checker = {
            'overall_differences': True,
            'results_per_analysis': {
                'No analysis': {'difference': True, 'more_metadata_submitted_files': [],
                                'more_per_submitted_files_metadata': {'input_passed.vcf': ['HG00096']},
                                'more_submitted_files_metadata': ['HG00096']},
                'VD1': {'difference': True, 'more_metadata_submitted_files': ['sample2', 'sample1'],
                        'more_per_submitted_files_metadata': {}, 'more_submitted_files_metadata': []},
                'VD2': {'difference': True, 'more_metadata_submitted_files': ['sample2', 'sample1'],
                        'more_per_submitted_files_metadata': {}, 'more_submitted_files_metadata': []},
                'VD3': {'difference': True, 'more_metadata_submitted_files': ['sample3', 'sample2', 'sample1'],
                        'more_per_submitted_files_metadata': {},'more_submitted_files_metadata': []},
                'VD4': {'difference': True, 'more_metadata_submitted_files': ['sample4'],
                        'more_per_submitted_files_metadata': {}, 'more_submitted_files_metadata': []},
                'VD5': {'difference': True, 'more_metadata_submitted_files': ['sample4'],
                        'more_per_submitted_files_metadata': {}, 'more_submitted_files_metadata': []}
            }
        }
        expected_metadata_files_json = [
            {'analysisAlias': 'VD1', 'fileName': 'example1.vcf.gz', 'fileSize': '', 'md5': ''},
            {'analysisAlias': 'VD2', 'fileName': 'example2.vcf', 'fileSize': '', 'md5': ''},
            {'analysisAlias': 'VD3', 'fileName': 'example3.vcf',  'fileSize': '', 'md5': ''}
        ]
        expected_metadata_val = 'Validation passed successfully.'
        expected_semantic_val = {'description': 'Project PRJEB00002 does not exist in ENA or is private',
                                 'property': '/project/childProjects/0'}
        self.assert_validation_results(self.validator_from_excel, expected_sample_checker, expected_metadata_files_json,
                                       expected_metadata_val, expected_semantic_val)

    def test_download_container_image_if_needed(self):
        with patch('eva_sub_cli.validators.validator.run_command_with_output') as m_run_command:
            m_run_command.side_effect = [
                None,                                       # <- verify_image_available_locally
                subprocess.CalledProcessError(1, 'pull'),   # <- First Pull
                None,                                       # <- verify_image_available_locally
                None                                        # <- Second Pull
            ]
            self.validator.download_container_image_if_needed()
