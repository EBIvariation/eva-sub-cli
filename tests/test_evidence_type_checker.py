import os
from unittest import TestCase

import yaml

from eva_sub_cli.executables.evidence_type_checker import check_evidence_type
from eva_sub_cli.metadata import EvaMetadataJson


class TestEvidenceTypeChecker(TestCase):
    resource_dir = os.path.join(os.path.dirname(__file__), 'resources')
    output_yaml = os.path.join(resource_dir, 'validation_output', 'evidence_type_checker.yaml')
    os.makedirs(os.path.join(resource_dir, 'validation_output'), exist_ok=True)

    def tearDown(self) -> None:
        if os.path.exists(self.output_yaml):
            os.remove(self.output_yaml)

    def test_evidence_check(self):
        working_dir = os.path.join(self.resource_dir, 'sample_checker')
        metadata_json = os.path.join(working_dir, 'metadata.json')
        # Change to working_dir so filenames in metadata.json are resolvable
        os.chdir(working_dir)
        vcf_files = [
            os.path.join(working_dir, file_name)
            for file_name in ['example1.vcf.gz', 'example2.vcf', 'example3.vcf']
        ]

        self.run_and_assert_evidence_type_check(metadata_json, vcf_files)

    def test_evidence_check_absolute_paths(self):
        working_dir = os.path.join(self.resource_dir, 'sample_checker')
        metadata_json = os.path.join(working_dir, 'metadata.json')
        vcf_files = [
            os.path.join(working_dir, file_name)
            for file_name in ['example1.vcf.gz', 'example2.vcf', 'example3.vcf']
        ]
        # Set filenames in metadata to absolute paths
        metadata = EvaMetadataJson(metadata_json)
        updated_files = metadata.files
        for file_obj in updated_files:
            file_obj['fileName'] = os.path.join(working_dir, file_obj['fileName'])
        metadata.set_files(updated_files)
        updated_metadata = os.path.join(working_dir, 'updated_metadata.json')
        metadata.write(updated_metadata)

        self.run_and_assert_evidence_type_check(updated_metadata, vcf_files)

        if os.path.exists(updated_metadata):
            os.remove(updated_metadata)

    def run_and_assert_evidence_type_check(self, metadata_json, vcf_files):
        check_evidence_type(metadata_json, vcf_files, self.output_yaml)
        expected_results = {
            'VD1': {
                'evidence_type': 'genotype',
                'errors': None
            },
            'VD2': {
                'evidence_type': 'genotype',
                'errors': None
            },
            'VD3': {
                'evidence_type': 'genotype',
                'errors': None
            }
        }

        with open(self.output_yaml) as open_yaml:
            assert yaml.safe_load(open_yaml) == expected_results
