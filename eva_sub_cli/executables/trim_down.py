import argparse
import os

from ebi_eva_common_pyutils.logger import logging_config
from eva_sub_cli.file_utils import open_gzip_if_required, fasta_iter

logger = logging_config.get_logger(__name__)


max_nb_lines = 10000


def trim_down_vcf(vcf_file, output_vcf):
    """
    Produce a smaller file
    """
    with open_gzip_if_required(vcf_file) as vcf_in, open(output_vcf, 'w') as vcf_out:
        line_count = 0
        ref_seq_names = set()
        for line in vcf_in:
            if line.startswith('#') or line_count < max_nb_lines:
                vcf_out.write(line)
                if not line.startswith('#'):
                    line_count += 1
                    ref_seq_names.add(line.split('\t')[0])
            else:
                break
    if line_count != max_nb_lines:
        logger.warning(f'Only {line_count} found in the source VCF {vcf_file} ')
    return ref_seq_names


def trim_down_fasta(fasta_file, output_fasta, ref_seq_names):
    found_sequences = set()
    with open(output_fasta, 'w') as fasta_out:
        for header, sequence in fasta_iter(fasta_file):
            name = header.split()[0]
            if name in ref_seq_names:
                found_sequences.add(name)
                fasta_out.write(header)
                fasta_out.write(sequence)
    return found_sequences


def main():
    arg_parser = argparse.ArgumentParser(
        description=f'Take a VCF file and only keep {max_nb_lines} lines and remove unused fasta sequence from the '
                    f'associated reference genome')
    arg_parser.add_argument('--vcf_file', dest='vcf_file', help='Path to the vcf file to be trimmed down')
    arg_parser.add_argument('--output_vcf_file', dest='output_vcf_file', help='Path to the output vcf file')
    arg_parser.add_argument('--fasta_file', dest='fasta_file', help='Path to the fasta file to be trimmed down')
    arg_parser.add_argument('--output_fasta_file', dest='output_fasta_file', help='Path to the output fasta file')

    args = arg_parser.parse_args()
    logging_config.add_stdout_handler()

    ref_sequence = trim_down_vcf(args.vcf_file, args.output_vcf_file)
    sequence_found = trim_down_fasta(args.fasta_file, args.output_fasta_file, ref_sequence)
    if len(sequence_found) != len(ref_sequence):
        logger.warning(f'Not all sequences were found in the fasta file. Cancelling trimming down of fasta file')
        os.link(args.fasta_file, args.output_fasta_file)