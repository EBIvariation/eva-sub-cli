import argparse
import os

import sys
import yaml
from ebi_eva_common_pyutils.logger import logging_config
from eva_sub_cli.file_utils import open_gzip_if_required, fasta_iter

logger = logging_config.get_logger(__name__)


MAX_NB_LINES = 10000


def trim_down_vcf(vcf_file, output_vcf, max_nb_lines=MAX_NB_LINES):
    """
    Produce a smaller vcf files containing a maximum of 10000 records
    """
    with open_gzip_if_required(vcf_file) as vcf_in, open_gzip_if_required(output_vcf, 'w') as vcf_out:
        line_count = 0
        trimmed_down = False
        ref_seq_names = set()
        for line in vcf_in:
            if line.startswith('#') or line_count < max_nb_lines:
                vcf_out.write(line)
                if not line.startswith('#'):
                    line_count += 1
                    ref_seq_names.add(line.split('\t')[0])
            else:
                trimmed_down = True
                break
    if line_count != max_nb_lines:
        logger.warning(f'Only {line_count} found in the source VCF {vcf_file} ')

    return line_count, trimmed_down, ref_seq_names


def trim_down_fasta(fasta_file, output_fasta, ref_seq_names):
    """
    Produce a smaller fasta files containing only the reference sequences found in the VCF file
    """
    found_sequences = set()
    with open(output_fasta, 'w') as fasta_out:
        for header, sequence in fasta_iter(fasta_file):
            name = header.split()[0]
            if name in ref_seq_names:
                found_sequences.add(name)
                print(f'>{header}', file=fasta_out)
                for i in range(0, len(sequence), 80):
                    print(sequence[i:i+80], file=fasta_out)
    return found_sequences

def parse_args(cmd_line_args):
    arg_parser = argparse.ArgumentParser(
        description=f'Take a VCF file and only keep {MAX_NB_LINES} lines and remove unused fasta sequence from the '
                    f'associated reference genome')
    arg_parser.add_argument('--vcf_file', dest='vcf_file', required=True,
                            help='Path to the vcf file to be trimmed down')
    arg_parser.add_argument('--output_vcf_file', dest='output_vcf_file', required=True,
                            help='Path to the output vcf file')
    arg_parser.add_argument('--fasta_file', dest='fasta_file', required=True,
                            help='Path to the fasta file to be trimmed down')
    arg_parser.add_argument('--output_fasta_file', dest='output_fasta_file', required=True,
                            help='Path to the output fasta file')
    arg_parser.add_argument('--output_yaml_file', dest='output_yaml_file', required=True,
                            help='Path to the yaml file containing the trim down metrics')

    args = arg_parser.parse_args()
    return args

def main():
    args = parse_args(sys.argv[1:])

    logging_config.add_stdout_handler()

    line_count, trimmed_down, ref_sequence = trim_down_vcf(args.vcf_file, args.output_vcf_file)
    sequence_found = trim_down_fasta(args.fasta_file, args.output_fasta_file, ref_sequence)
    trim_down_metrics = {'trim_down_vcf_record': line_count, 'number_sequence_found': len(sequence_found),
                         'trim_down_required': trimmed_down}
    if len(sequence_found) != len(ref_sequence):
        logger.warning(f'Not all sequences were found in the fasta file. Cancelling trimming down of fasta file')
        if os.path.exists(args.output_fasta_file):
            os.remove(args.output_fasta_file)
        os.link(args.fasta_file, args.output_fasta_file)
        trim_down_metrics.pop('number_sequence_found')
    with open(args.output_yaml_file, 'w') as open_file:
        yaml.safe_dump(trim_down_metrics, open_file)

