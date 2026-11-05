import argparse
import json

from ebi_eva_common_pyutils.logger import logging_config

from eva_sub_cli.seqcol import sequence_collection_from_fasta

logger = logging_config.get_logger(__name__)


def main():
    arg_parser = argparse.ArgumentParser(
        description='Calculate the GA4GH sequence collection (and its digest) of a FASTA file.')
    arg_parser.add_argument('--input_fasta', required=True, dest='input_fasta',
                            help='Fasta file for which the sequence collection will be calculated')
    arg_parser.add_argument('--output_json', required=True, dest='output_json',
                            help='Path to the JSON file where the sequence collection will be written')
    args = arg_parser.parse_args()
    logging_config.add_stdout_handler()
    sequence_collection = sequence_collection_from_fasta(args.input_fasta)
    logger.info(f'Sequence collection digest for {args.input_fasta}: {sequence_collection["digest"]}')
    with open(args.output_json, 'w') as open_json:
        json.dump(sequence_collection, open_json)


if __name__ == "__main__":
    main()
