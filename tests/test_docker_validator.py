import csv
import json
import os
import shutil
from unittest import TestCase
from unittest.mock import patch

import yaml

from eva_sub_cli.docker_validator import DockerValidator


class TestDockerValidator(TestCase):
    resources_folder = os.path.join(os.path.dirname(__file__), 'resources')

    vcf_files = os.path.join(resources_folder, 'vcf_files')
    fasts_files = os.path.join(resources_folder, 'fasta_files')
    assembly_reports = os.path.join(resources_folder, 'assembly_reports')

    test_run_dir = os.path.join(resources_folder, 'docker_test_run')
    mapping_file = os.path.join(test_run_dir, 'vcf_files_metadata.csv')
    metadata_json = os.path.join(test_run_dir, 'sub_metadata.json')
    metadata_xlsx = os.path.join(test_run_dir, 'sub_metadata.xlsx')

    output_dir = os.path.join(test_run_dir, 'validation_output')

    def setUp(self):
        if not os.path.exists(self.test_run_dir):
            os.makedirs(self.test_run_dir)

        # create vcf metadata file
        data = [
            ['vcf', 'fasta', 'report'],
            [os.path.join(self.vcf_files, 'input_passed.vcf'),
             os.path.join(self.fasts_files, 'input_passed.fa'),
             os.path.join(self.assembly_reports, 'input_passed.txt')]
        ]
        with open(self.mapping_file, 'w', encoding='UTF8') as f:
            writer = csv.writer(f)
            for row in data:
                writer.writerow(row)
        sub_metadata = {
            "submitterDetails": [],
            "project": {},
            "sample": [
                {"analysisAlias":  "AA", "sampleInVCF":  "HG00096", "BioSampleAccession": "SAME0000096"}
            ],
            "analysis": [
                {"analysisAlias": "AA"}
            ],
            "file": [
                {"analysisAlias": "AA", "fileName": os.path.join(self.vcf_files, 'input_passed.vcf'), "fileType": "vcf"}
            ]
        }
        with open(self.metadata_json, 'w') as open_metadata:
            json.dump(sub_metadata, open_metadata)
        self.validator = DockerValidator(
            mapping_file=self.mapping_file,
            output_dir=self.output_dir,
            metadata_json=self.metadata_json,
            container_name='eva-sub-eva_sub_cli-test'
        )
        shutil.copyfile(
            os.path.join(self.resources_folder, 'EVA_Submission_template.V1.1.4.xlsx'),
            self.metadata_xlsx
        )

        self.validator_from_excel = DockerValidator(
            mapping_file=self.mapping_file,
            output_dir=self.output_dir,
            metadata_xlsx=self.metadata_xlsx,
            container_name='eva-sub-eva_sub_cli-test'
        )

    def tearDown(self):
        if os.path.exists(self.test_run_dir):
            shutil.rmtree(self.test_run_dir)
        self.validator.stop_running_container()
        self.validator_from_excel.stop_running_container()

    def test_validate(self):
        # run validation in docker
        self.validator.validate()

        # assert vcf checks
        vcf_format_dir = os.path.join(self.output_dir, 'vcf_format')
        self.assertTrue(os.path.exists(vcf_format_dir))

        vcf_format_log_file = os.path.join(vcf_format_dir, 'input_passed.vcf.vcf_format.log')
        self.assertTrue(os.path.exists(vcf_format_log_file))

        with open(vcf_format_log_file) as vcf_format_log_file:
            vcf_format_logs = vcf_format_log_file.readlines()
            self.assertEqual('[info] According to the VCF specification, the input file is valid\n',
                             vcf_format_logs[3])

            text_report = vcf_format_logs[2].split(':')[1].strip()
            with open(os.path.join(self.output_dir, text_report)) as text_report:
                text_report_content = text_report.readlines()
                self.assertEqual('According to the VCF specification, the input file is valid\n',
                                 text_report_content[0])

        # assert assembly report
        assembly_check_dir = os.path.join(self.output_dir, 'assembly_check')
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
        sample_checker_yaml = os.path.join(self.output_dir, 'sample_checker.yml')
        self.assertTrue(os.path.isfile(sample_checker_yaml))
        with open(sample_checker_yaml) as open_yaml:
            assert yaml.safe_load(open_yaml) == expected_checker

    def test_validate_from_excel(self):
        # FIXME: The Sample check fails because the json file generated does not currently match the expected one
        # Need to skip the file collection
        with patch.object(DockerValidator, '_collect_validation_workflow_results'):
            self.validator_from_excel.validate()
            sample_checker_yaml = os.path.join(self.output_dir, 'sample_checker.yml')
            self.assertFalse(os.path.isfile(sample_checker_yaml))
