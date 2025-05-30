import os
from unittest import TestCase

import yaml

from eva_sub_cli.executables.samples_checker import check_sample_name_concordance


class TestSampleChecker(TestCase):
    resource_dir = os.path.join(os.path.dirname(__file__), 'resources')
    output_yaml = os.path.join(resource_dir, 'validation_output', 'sample_checker.yaml')
    os.makedirs(os.path.join(resource_dir, 'validation_output'), exist_ok=True)

    def tearDown(self) -> None:
        if os.path.exists(self.output_yaml):
            os.remove(self.output_yaml)

    def test_check_sample_name_concordance(self):
        # TODO test both relative and absolute paths
        metadata_json = os.path.join(self.resource_dir, 'sample_checker', 'metadata.json')
        vcf_files = [
            os.path.join(self.resource_dir, 'sample_checker', file_name)
            for file_name in ['example1.vcf.gz', 'example2.vcf', 'example3.vcf']
        ]

        check_sample_name_concordance(metadata_json, vcf_files, self.output_yaml)
        expected_results = {
            'overall_differences': True,
            'results_per_analysis': {
                'VD1': {
                    'difference': False,
                    'more_metadata_submitted_files': [],
                    'more_per_submitted_files_metadata': {},
                    'more_submitted_files_metadata': []
                },
                'VD2': {
                    'difference': True,
                    'more_metadata_submitted_files': [],
                    'more_per_submitted_files_metadata': {'example2.vcf': ['sample3']},
                    'more_submitted_files_metadata': ['sample3']
                },
                'VD3': {
                    'difference': True,
                    'more_metadata_submitted_files': ['sample3'],
                    'more_per_submitted_files_metadata': {},
                    'more_submitted_files_metadata': []}
            }
        }

        with open(self.output_yaml) as open_yaml:
            assert yaml.safe_load(open_yaml) == expected_results
