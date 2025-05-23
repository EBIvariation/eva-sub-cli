import copy
import logging
import os
import shutil
from unittest import TestCase
from unittest.mock import patch, Mock

import yaml

from eva_sub_cli.executables import trim_down
from eva_sub_cli.executables.trim_down import trim_down_vcf, trim_down_fasta
from eva_sub_cli.file_utils import open_gzip_if_required


class TestTrimDown(TestCase):

    resources_folder = os.path.join(os.path.dirname(__file__), 'resources')
    submission_dir = os.path.abspath(os.path.join(resources_folder, 'submission_dir'))

    def setUp(self) -> None:
        os.makedirs(self.submission_dir, exist_ok=True)

    def tearDown(self) -> None:
        if os.path.exists(self.submission_dir):
            shutil.rmtree(self.submission_dir)

    def test_main_trim(self):
        vcf_file = os.path.join(self.resources_folder, 'vcf_files', 'input_passed.vcf')
        output_vcf = os.path.join(self.submission_dir, 'trim_input_passed.vcf')

        fasta_file = os.path.join(self.resources_folder, 'fasta_files', 'multi_seq.fa')
        output_fasta = os.path.join(self.submission_dir, 'trim_multi_seq.fa')

        output_yaml_file = os.path.join(self.submission_dir, 'metric.yml')

        args = Mock(vcf_file=vcf_file, output_vcf_file=output_vcf, fasta_file=fasta_file,
                    output_fasta_file=output_fasta, output_yaml_file=output_yaml_file)
        with patch('eva_sub_cli.executables.trim_down.parse_args', return_value=args):
            trim_down.main()
            assert os.path.exists(output_vcf)
            assert os.path.exists(output_fasta)
            assert os.path.exists(output_yaml_file)
            with open(output_yaml_file) as open_file:
                data = yaml.safe_load(open_file)
                assert data == {'number_sequence_found': 1, 'trim_down_required': False, 'trim_down_vcf_record': 247}

    def test_trim_down_fasta(self):
        fasta_file = os.path.join(self.resources_folder, 'fasta_files', 'multi_seq.fa')
        output_fasta = os.path.join(self.submission_dir, 'trim_multi_seq.fa')

        trim_down_fasta(fasta_file=fasta_file, output_fasta=output_fasta, ref_seq_names=['1', '3'])
        assert os.path.exists(output_fasta)
        nb_line = count_line(output_fasta)
        assert nb_line == 4

    def test_trim_down_vcf(self):
        vcf_file = os.path.join(self.resources_folder, 'vcf_files', 'input_passed.vcf')
        nb_line = count_line(vcf_file)
        assert nb_line == 247
        output_vcf = os.path.join(self.submission_dir, 'trim_input_passed.vcf')
        line_count, trimmed_down, ref_seq_names = trim_down_vcf(vcf_file, output_vcf, max_nb_lines=100)
        assert line_count == 100
        assert trimmed_down == True
        assert ref_seq_names == {'1'}
        nb_line = count_line(output_vcf)
        assert nb_line == 100

    def test_trim_down_vcf_gz(self):
        vcf_file = os.path.join(self.resources_folder, 'vcf_files', 'example2.vcf.gz')
        nb_line = count_line(vcf_file)
        assert nb_line == 2
        assert is_gz_file(vcf_file)

        output_vcf = os.path.join(self.submission_dir, 'trim_example2.vcf.gz')
        line_count, trimmed_down, ref_seq_names = trim_down_vcf(vcf_file, output_vcf, max_nb_lines=1)
        assert line_count == 1
        assert trimmed_down == True
        assert ref_seq_names == {'1'}
        nb_line = count_line(output_vcf)
        assert nb_line == 1
        assert is_gz_file(output_vcf)

    def test_not_trim_down_vcf(self):
        vcf_file = os.path.join(self.resources_folder, 'vcf_files', 'input_passed.vcf')
        output_vcf = os.path.join(self.submission_dir, 'trim_input_passed.vcf')
        line_count, trimmed_down, ref_seq_names = trim_down_vcf(vcf_file, output_vcf, max_nb_lines=1000)
        assert line_count == 247
        assert trimmed_down == False
        assert ref_seq_names == {'1'}
        nb_line = count_line(output_vcf)
        assert nb_line == 247


def is_gz_file(filepath):
    with open(filepath, 'rb') as test_f:
        return test_f.read(2) == b'\x1f\x8b'


def count_line(vcf_file):
    count=0
    with open_gzip_if_required(vcf_file) as open_vcf_file:
        for line in open_vcf_file:
            if line.startswith('#'):
                continue
            else:
                count += 1

    return  count
