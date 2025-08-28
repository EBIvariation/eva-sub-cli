import os
from unittest import TestCase
from unittest.mock import patch

import pytest
import requests as requests

from eva_sub_cli.executables.check_fasta_insdc import assess_fasta, get_analyses_and_reference_genome_from_metadata, \
    get_containing_assemblies
from eva_sub_cli.metadata import EvaMetadataJson


class TestFastaChecker(TestCase):
    resource_dir = os.path.join(os.path.dirname(__file__), 'resources')

    def test_get_analysis_and_reference_genome_from_metadata(self):
        working_dir = os.path.join(self.resource_dir, 'sample_checker')
        metadata_json = os.path.join(working_dir, 'metadata.json')
        vcf_file = os.path.join(working_dir, 'example1.vcf.gz')
        # Change to working_dir so filenames in metadata.json are resolvable
        os.chdir(working_dir)
        analyses, reference = get_analyses_and_reference_genome_from_metadata([vcf_file], metadata_json)
        assert analyses == {'VD1'}
        assert reference == 'GCA_000001405.27'

    def test_get_analysis_and_reference_genome_from_metadata_absolute_paths(self):
        working_dir = os.path.join(self.resource_dir, 'sample_checker')
        metadata_json = os.path.join(working_dir, 'metadata.json')
        vcf_file = os.path.join(working_dir, 'example1.vcf.gz')

        # Set filenames in metadata to absolute paths
        metadata = EvaMetadataJson(metadata_json)
        updated_files = metadata.files
        for file_obj in updated_files:
            file_obj['fileName'] = os.path.join(working_dir, file_obj['fileName'])
        metadata.set_files(updated_files)
        updated_metadata = os.path.join(working_dir, 'updated_metadata.json')
        metadata.write(updated_metadata)

        analyses, reference = get_analyses_and_reference_genome_from_metadata([vcf_file], updated_metadata)
        assert analyses == {'VD1'}
        assert reference == 'GCA_000001405.27'

        if os.path.exists(updated_metadata):
            os.remove(updated_metadata)

    def test_assess_fasta_is_insdc(self):
        input_fasta = os.path.join(self.resource_dir, 'fasta_files', 'Saccharomyces_cerevisiae_I.fa')
        with patch('eva_sub_cli.executables.check_fasta_insdc.get_refget_metadata', autospec=True) as m_get_refget, \
                patch('eva_sub_cli.executables.check_fasta_insdc._get_containing_assemblies_paged', autospec=True) as m_get_assemblies:
            m_get_refget.return_value = {'sequence_name': 'chr1'}
            m_get_assemblies.return_value = {'GCA_000146045.2'}
            results = assess_fasta(input_fasta, ['analysis'], None)
            assert results == {
                'all_insdc': True,
                'sequences': [{'sequence_name': 'I', 'sequence_md5': '6681ac2f62509cfc220d78751b8dc524', 'insdc': True}],
                'possible_assemblies': {'GCA_000146045.2'}
            }
        with patch('eva_sub_cli.executables.check_fasta_insdc.get_refget_metadata', autospec=True) as m_get_refget, \
                patch('eva_sub_cli.executables.check_fasta_insdc._get_containing_assemblies_paged', autospec=True) as m_get_assemblies:
            m_get_refget.return_value = None
            m_get_assemblies.return_value = set()
            results = assess_fasta(input_fasta, ['analysis'], None)
            assert results == {
                'all_insdc': False,
                'sequences': [{'sequence_name': 'I', 'sequence_md5': '6681ac2f62509cfc220d78751b8dc524', 'insdc': False}]
            }

    def test_assess_fasta_matches_metadata(self):
        input_fasta = os.path.join(self.resource_dir, 'fasta_files', 'Saccharomyces_cerevisiae_I.fa')
        with patch('eva_sub_cli.executables.check_fasta_insdc.get_refget_metadata', autospec=True) as m_get_refget, \
                patch('eva_sub_cli.executables.check_fasta_insdc._get_containing_assemblies_paged', autospec=True) as m_get_assemblies:
            m_get_refget.return_value = {'sequence_name': 'I'}
            m_get_assemblies.return_value = {'GCA_000146045.2'}
            results = assess_fasta(input_fasta, ['analysis'], 'GCA_000146045.2')
            assert results == {
                'all_insdc': True,
                'sequences': [
                    {'sequence_name': 'I', 'sequence_md5': '6681ac2f62509cfc220d78751b8dc524', 'insdc': True}],
                'possible_assemblies': {'GCA_000146045.2'},
                'metadata_assembly_compatible': True,
                'associated_analyses': ['analysis'],
                'assembly_in_metadata': 'GCA_000146045.2'
            }
            results = assess_fasta(input_fasta, ['analysis'], 'GCA_002915635.1')
            assert results == {
                'all_insdc': True,
                'sequences': [
                    {'sequence_name': 'I', 'sequence_md5': '6681ac2f62509cfc220d78751b8dc524', 'insdc': True}],
                'possible_assemblies': {'GCA_000146045.2'},
                'metadata_assembly_compatible': False,
                'associated_analyses': ['analysis'],
                'assembly_in_metadata': 'GCA_002915635.1'
            }

    def test_assess_fasta_http_error(self):
        input_fasta = os.path.join(self.resource_dir, 'fasta_files', 'Saccharomyces_cerevisiae_I.fa')
        with patch('eva_sub_cli.executables.check_fasta_insdc.get_refget_metadata', autospec=True) as m_get_refget, \
                patch('eva_sub_cli.executables.check_fasta_insdc._get_containing_assemblies_paged', autospec=True) as m_get_assemblies:
            m_get_refget.return_value = {'sequence_name': 'I'}
            m_get_assemblies.side_effect = requests.HTTPError('500 Internal Server Error')
            results = assess_fasta(input_fasta, ['analysis'], None)
            assert results == {
                'all_insdc': True,
                'sequences': [{'sequence_name': 'I', 'sequence_md5': '6681ac2f62509cfc220d78751b8dc524', 'insdc': True}],
                'connection_error': '500 Internal Server Error'
            }

    @pytest.mark.integration
    def test_assess_fasta_is_insdc_integration(self):
        input_fasta = os.path.join(self.resource_dir, 'fasta_files', 'input_passed.fa')
        results = assess_fasta(input_fasta, ['analysis'], None)
        assert results == {
            'all_insdc': False,
            'sequences': [{'sequence_name': 'chr1', 'sequence_md5': 'd2b3f22704d944f92a6bc45b6603ea2d', 'insdc': False}]
        }

    @pytest.mark.integration
    def test_assess_fasta_matches_metadata_integration(self):
        input_fasta = os.path.join(self.resource_dir, 'fasta_files', 'Saccharomyces_cerevisiae_I.fa')
        results = assess_fasta(input_fasta, ['analysis'], 'GCA_000146045.2')
        assert results == {
            'all_insdc': True,
            'sequences': [
                {'sequence_name': 'I', 'sequence_md5': '6681ac2f62509cfc220d78751b8dc524', 'insdc': True}],
            'possible_assemblies': {'GCA_000146045.2'},
            'metadata_assembly_compatible': True,
            'associated_analyses': ['analysis'],
            'assembly_in_metadata': 'GCA_000146045.2'
        }

    @pytest.mark.integration
    def test_get_containing_assemblies(self):
        results = get_containing_assemblies('6ac8f815bf8e845bb3031b73f812c012')
        assert len(results) == 15
        assert 'GCA_000001405.29' in results
