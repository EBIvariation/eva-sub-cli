import os
from unittest import TestCase

from eva_sub_cli.metadata import EvaMetadataJson


class TestEvaMetadata(TestCase):
    working_dir = os.path.dirname(__file__)
    resource_dir = os.path.join(working_dir, 'resources')
    metadata_json = os.path.join(resource_dir, 'EVA_Submission_test.json')

    def setUp(self):
        self.metadata = EvaMetadataJson(self.metadata_json)
        os.chdir(self.working_dir)

    def test_resolved_files(self):
        assert self.metadata.resolved_files == [
            {
                'analysisAlias': 'VD1',
                'fileName': os.path.join(self.working_dir, 'example1.vcf.gz'),
                'fileType': 'vcf'
            },
            {
                'analysisAlias': 'VD2',
                'fileName': os.path.join(self.working_dir, 'example2.vcf'),
                'fileType': 'vcf'
            },
            {
                'analysisAlias': 'VD3',
                'fileName': os.path.join(self.working_dir, 'example3.vcf'),
                'fileType': 'vcf'
            }
        ]
        # Confirm resolved_files does not affect files
        assert self.metadata.files[0]['fileName'] == 'example1.vcf.gz'

    def test_samples_per_analysis(self):
        assert self.metadata.samples_per_analysis == {
            'VD1': {'sample1', 'sample2'},
            'VD2': {'sample1', 'sample2'},
            'VD3': {'sample1', 'sample2', 'sample3'},
            'VD4': {'sample4'},
            'VD5': {'sample4'}
        }

    def test_files_per_analysis(self):
        assert self.metadata.files_per_analysis == {
            'VD1': {os.path.join(self.working_dir, 'example1.vcf.gz')},
            'VD2': {os.path.join(self.working_dir, 'example2.vcf')},
            'VD3': {os.path.join(self.working_dir, 'example3.vcf')}
        }

    def test_get_reference_assembly_for_analysis(self):
        assert self.metadata.get_reference_assembly_for_analysis('VD1') == 'GCA_000001405.27'
        assert self.metadata.get_reference_assembly_for_analysis('nonexistent') is None

    def test_get_analysis_for_vcf_file(self):
        # File exists and resolves to match metadata
        open('example1.vcf.gz', 'w').close()
        assert self.metadata.get_analysis_for_vcf_file(os.path.join(self.working_dir, 'example1.vcf.gz')) == ['VD1']
        assert self.metadata.get_analysis_for_vcf_file('example1.vcf.gz') == ['VD1']
        os.remove('example1.vcf.gz')

        # File does not exist
        with self.assertRaises(FileNotFoundError):
            self.metadata.get_analysis_for_vcf_file('example2.vcf')

        # File exists but does not resolve to a path that matches metadata
        assert self.metadata.get_analysis_for_vcf_file(os.path.join(self.resource_dir, 'vcf_files', 'example2.vcf.gz')) == []
