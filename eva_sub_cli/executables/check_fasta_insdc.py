import argparse
import hashlib

import requests
import yaml
from ebi_eva_common_pyutils.logger import logging_config
from requests import HTTPError
from retry import retry

from eva_sub_cli.file_utils import fasta_iter
from eva_sub_cli.metadata import EvaMetadataJson

REFGET_SERVER = 'https://www.ebi.ac.uk/ena/cram'
CONTIG_ALIAS_SERVER = 'https://www.ebi.ac.uk/eva/webservices/contig-alias/v1/chromosomes/md5checksum'

logger = logging_config.get_logger(__name__)


def write_result_yaml(output_yaml, results):
    with open(output_yaml, 'w') as open_yaml:
        yaml.safe_dump(data=results, stream=open_yaml)


def refget_md5_digest(sequence):
    return hashlib.md5(sequence.upper().encode('utf-8')).hexdigest()

@retry(exceptions=(HTTPError,), tries=3, delay=2, backoff=1.2, jitter=(1, 3))
def get_refget_metadata(md5_digest):
    response = requests.get(f'{REFGET_SERVER}/sequence/{md5_digest}/metadata')
    if 500 <= response.status_code < 600:
        raise HTTPError(f"{response.status_code} Server Error: {response.reason} for url: {response.url}", response=response)
    if 200 <= response.status_code < 300:
        return response.json()
    return None


@retry(exceptions=(HTTPError,), tries=3, delay=2, backoff=1.2, jitter=(1, 3))
def _get_containing_assemblies_paged(url):
    response = requests.get(url)
    if 500 <= response.status_code < 600:
        raise HTTPError(f"{response.status_code} Server Error: {response.reason} for url: {response.url}",
                        response=response)
    if 200 <= response.status_code < 300:
        results = set()
        response_data = response.json()
        if '_embedded' in response_data and 'chromosomeEntities' in response_data['_embedded']:
            for contigEntity in response_data['_embedded']['chromosomeEntities']:
                results.add(contigEntity['assembly']['insdcAccession'])
        if '_links' in response_data and 'next' in response_data['_links']:
            # Add results from next page if needed
            results = results.union(_get_containing_assemblies_paged(response_data['_links']['next']['href']))
        return results
    return set()


def get_containing_assemblies(md5_digest):
    # Wrapper method to handle pagination
    url = f'{CONTIG_ALIAS_SERVER}/{md5_digest}'
    return _get_containing_assemblies_paged(url)


def assess_fasta(input_fasta, analyses, assembly_in_metadata):
    """
    Check whether all sequences in fasta file are INSDC, and if so whether the INSDC accession provided in the metadata
    is compatible.
    :param input_fasta: path to fasta file
    :param analyses: aliases of all analyses associated with this fasta (used only for reporting)
    :param assembly_in_metadata: INSDC accession from metadata (if None will only do the first check but will report
      compatible assemblies)
    :returns: dict of results
    """
    results = {'sequences': []}
    all_insdc = True
    possible_assemblies = set()
    try:
        for header, sequence in fasta_iter(input_fasta):
            # Check sequence is INSDC
            name = header.split()[0]
            md5_digest = refget_md5_digest(sequence)
            sequence_metadata = get_refget_metadata(md5_digest)
            is_insdc = bool(sequence_metadata)
            results['sequences'].append({'sequence_name': name, 'sequence_md5': md5_digest, 'insdc': is_insdc})
            all_insdc = all_insdc and is_insdc
            # Get possible assemblies for sequence
            containing_assemblies = get_containing_assemblies(md5_digest)
            if len(containing_assemblies) == 0:
                if is_insdc:
                    logger.warning(f'Sequence with this MD5 is INSDC but not found in contig alias: {md5_digest}')
            elif len(possible_assemblies) == 0:
                possible_assemblies = containing_assemblies
            else:
                possible_assemblies &= containing_assemblies
    except Exception as e:
        # Server errors from either ENA refget or EVA contig alias will halt the check prematurely.
        # Report the error but do not return from the method, so that incomplete results can be reported
        # (i.e. any sequences found to be INSDC and any compatible assemblies so far)
        results['connection_error'] = str(e)

    # Always report whether everything is INSDC
    results['all_insdc'] = all_insdc
    # Only report compatible assembly accessions if any were found in contig alias
    if possible_assemblies:
        results['possible_assemblies'] = possible_assemblies
    # Only report on metadata concordance if we found compatible assemblies and found a single assembly accession in
    # the metadata to compare against this FASTA file
    if possible_assemblies and assembly_in_metadata:
        results['metadata_assembly_compatible'] = (assembly_in_metadata in possible_assemblies)
        results['associated_analyses'] = analyses
        results['assembly_in_metadata'] = assembly_in_metadata
    return results


def get_analyses_and_reference_genome_from_metadata(vcf_files_for_fasta, json_file):
    """
    Get analysis aliases and associated reference genome from the metadata.
    :param vcf_files_for_fasta: list of VCF file paths, assumed to be associated with a single FASTA file and thus a
      single assembly accession
    :param json_file: JSON file of the metadata
    """
    metadata = EvaMetadataJson(json_file)
    # Get all analyses associated with all vcf files that are linked with a single fasta file
    all_analyses = set()
    for vcf_file in vcf_files_for_fasta:
        analysis_aliases = metadata.get_analysis_for_vcf_file(vcf_file)
        if len(analysis_aliases) != 1:
            logger.error(f'Could not determine analysis associated with VCF file: {vcf_file}')
        else:
            all_analyses.add(analysis_aliases[0])
    # Get (single) assembly associated with these analyses
    assemblies = [metadata.get_reference_assembly_for_analysis(analysis) for analysis in all_analyses]
    if len(assemblies) != 1:
        logger.error(f'Could not determine assembly accession to check against fasta file, out of: {assemblies}')
        return all_analyses, None
    return all_analyses, assemblies[0]


def main():
    arg_parser = argparse.ArgumentParser(
        description="Calculate each sequence's Refget MD5 digest and compare these against INSDC Refget server.")
    arg_parser.add_argument('--input_fasta', required=True, dest='input_fasta',
                            help='Fasta file that contains the sequence to be checked')
    arg_parser.add_argument('--vcf_files', dest='vcf_files', nargs='+',
                            help='VCF files associated with this fasta file (used to connect fasta file to '
                                 'assembly accession in metadata via analysis)')
    arg_parser.add_argument('--metadata_json', required=True, dest='metadata_json', help='EVA metadata json file')
    arg_parser.add_argument('--output_yaml', required=True, dest='output_yaml',
                            help='Path to the location of the results')
    args = arg_parser.parse_args()
    logging_config.add_stdout_handler()
    analyses, metadata_insdc = get_analyses_and_reference_genome_from_metadata(args.vcf_files, args.metadata_json)
    results = assess_fasta(args.input_fasta, analyses, metadata_insdc)
    write_result_yaml(args.output_yaml, results)
