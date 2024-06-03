import json
import os
import shutil
from unittest import TestCase

import yaml

from eva_sub_cli.validators.docker_validator import DockerValidator
from tests.test_utils import create_mapping_file


class TestDockerValidator(TestCase):
    resources_folder = os.path.join(os.path.dirname(__file__), 'resources')
    project_title = 'Example Project'
    vcf_files = os.path.join(resources_folder, 'vcf_files')
    fasta_files = os.path.join(resources_folder, 'fasta_files')
    assembly_reports = os.path.join(resources_folder, 'assembly_reports')

    test_run_dir = os.path.join(resources_folder, 'docker_test_run')
    mapping_file = os.path.join(test_run_dir, 'vcf_files_metadata.csv')
    metadata_json = os.path.join(test_run_dir, 'sub_metadata.json')
    metadata_xlsx = os.path.join(test_run_dir, 'sub_metadata.xlsx')

    submission_dir = test_run_dir

    def setUp(self):
        os.makedirs(self.test_run_dir, exist_ok=True)

        # create vcf mapping file
        create_mapping_file(self.mapping_file,
                            [os.path.join(self.vcf_files, 'input_passed.vcf')],
                            [os.path.join(self.fasta_files, 'input_passed.fa')],
                            [os.path.join(self.assembly_reports, 'input_passed.txt')])
        sub_metadata = {
            "submitterDetails": [],
            "project": {},
            "sample": [
                {"analysisAlias":  "AA", "sampleInVCF":  "HG00096", "BioSampleAccession": "SAME0000096"}
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
            submission_dir=self.submission_dir,
            project_title=self.project_title,
            metadata_json=self.metadata_json,
            container_name='eva-sub-cli-test'
        )
        shutil.copyfile(
            os.path.join(self.resources_folder, 'EVA_Submission_test.xlsx'),
            self.metadata_xlsx
        )

        self.validator_from_excel = DockerValidator(
            mapping_file=self.mapping_file,
            submission_dir=self.submission_dir,
            project_title=self.project_title,
            metadata_xlsx=self.metadata_xlsx,
            container_name='eva-sub-cli-test'
        )

    def tearDown(self):
        if os.path.exists(self.test_run_dir):
            shutil.rmtree(self.test_run_dir)
        self.validator.stop_running_container()
        self.validator_from_excel.stop_running_container()

    def assert_sample_checker(self, sample_checker_file, expected_checker):
        self.assertTrue(os.path.isfile(sample_checker_file))
        with open(sample_checker_file) as open_yaml:
            assert yaml.safe_load(open_yaml) == expected_checker

    def test_validate(self):
        # run validation in docker
        self.validator.validate()

        vcf_format_dir = os.path.join(self.validator.output_dir, 'vcf_format')
        self.assertTrue(os.path.exists(vcf_format_dir))

        vcf_format_log_file = os.path.join(vcf_format_dir, 'input_passed.vcf.vcf_format.log')
        self.assertTrue(os.path.exists(vcf_format_log_file))

        with open(vcf_format_log_file) as vcf_format_log_file:
            vcf_format_logs = vcf_format_log_file.readlines()
            self.assertEqual('[info] According to the VCF specification, the input file is valid\n',
                             vcf_format_logs[3])

            text_report = vcf_format_logs[2].split(':')[1].strip()
            with open(os.path.join(self.validator.output_dir, text_report)) as text_report:
                text_report_content = text_report.readlines()
                self.assertEqual('According to the VCF specification, the input file is valid\n',
                                 text_report_content[0])

        # assert assembly report
        assembly_check_dir = os.path.join(self.validator.output_dir, 'assembly_check')
        self.assertTrue(os.path.exists(assembly_check_dir))

        assembly_check_log_file = os.path.join(assembly_check_dir, 'input_passed.vcf.assembly_check.log')
        self.assertTrue(os.path.exists(assembly_check_log_file))

        with open(assembly_check_log_file) as assembly_check_log_file:
            assembly_check_logs = assembly_check_log_file.readlines()
            self.assertEqual('[info] Number of matches: 247/247\n', assembly_check_logs[5])
            self.assertEqual('[info] Percentage of matches: 100%\n', assembly_check_logs[6])

        # Assert Samples concordance
        expected_checker = {
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
        self.assert_sample_checker(self.validator._sample_check_yaml, expected_checker)

        with open(self.validator.metadata_json_post_validation) as open_file:
            json_data = json.load(open_file)
            assert json_data.get('files') == [
                {'analysisAlias': 'AA', 'fileName': 'input_passed.vcf', 'fileType': 'vcf',
                 'md5': '96a80c9368cc3c37095c86fbe6044fb2'}
            ]

    def test_validate_from_excel(self):
        self.validator_from_excel.validate()
        self.assertTrue(os.path.isfile(self.validator_from_excel._sample_check_yaml))
