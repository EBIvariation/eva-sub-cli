import re

from ebi_eva_common_pyutils.logger import logging_config

logger = logging_config.get_logger(__name__)

def parse_assembly_check_log(assembly_check_log):
    error_list = []
    nb_error, nb_mismatch = 0, 0
    match = total = None
    with open(assembly_check_log) as open_file:
        for line in open_file:
            if line.startswith('[error]'):
                nb_error += 1
                if nb_error < 11:
                    error_list.append(line.strip()[len('[error] '):])
            elif line.startswith('[info] Number of matches:'):
                match, total = line.strip()[len('[info] Number of matches: '):].split('/')
                match = int(match)
                total = int(total)
    return error_list, nb_error, match, total


def parse_assembly_check_report(assembly_check_report):
    mismatch_list = []
    nb_mismatch = 0
    nb_error = 0
    error_list = []
    with open(assembly_check_report) as open_file:
        for line in open_file:
            if 'does not match the reference sequence' in line:
                nb_mismatch += 1
                if nb_mismatch < 11:
                    mismatch_list.append(line.strip())
            elif 'Multiple synonyms' in line:
                nb_error += 1
                if nb_error < 11:
                    error_list.append(line.strip())
            # Contig not found in FASTA is reported here rather than in logs when no assembly report is used.
            # Count and report once per contig name rather than once per line, to avoid redundant errors.
            elif 'is not present in FASTA file' in line:
                line_num, error_msg = line.split(': ')
                error_msg = error_msg.strip()
                if error_msg not in error_list:
                    nb_error += 1
                    if nb_error < 11:
                        error_list.append(error_msg)
    return mismatch_list, nb_mismatch, error_list, nb_error


def parse_vcf_check_report(vcf_check_report):
    valid = True
    max_error_reported = 10
    error_list, critical_list = [], []
    warning_count = error_count = critical_count = 0
    with open(vcf_check_report) as open_file:
        for line in open_file:
            if 'warning' in line:
                warning_count = 1
            elif line.startswith('According to the VCF specification'):
                if 'not' in line:
                    valid = False
            elif vcf_check_errors_is_critical(line.strip()):
                critical_count += 1
                if critical_count <= max_error_reported:
                    critical_list.append(line.strip())
            else:
                error_count += 1
                if error_count <= max_error_reported:
                    error_list.append(line.strip())

    return valid, warning_count, error_count, critical_count, error_list, critical_list


def vcf_check_errors_is_critical(error):
    """
    This function identify VCF check errors that are not critical for the processing of the VCF within EVA.
    They affect specific INFO or FORMAT fields that are used in the variant detection but less so in the downstream
    analysis.
    Critical:
    Reference and alternate alleles must not be the same.
    Requested evidence presence with --require-evidence. Please provide genotypes (GT field in FORMAT and samples),
    or allele frequencies (AF field in INFO), or allele counts (AC and AN fields in INFO)..
    Contig is not sorted by position. Contig chr10 position 41695506 found after 41883113.
    Duplicated variant chr1A:1106203:A>G found.
    Metadata description string is not valid.

    Error
    Sample #10, field PL does not match the meta specification Number=G (expected 2 value(s)). PL=.. It must derive
    its number of values from the ploidy of GT (if present), or assume diploidy. Contains 1 value(s), expected 2
    (derived from ploidy 1).
    Sample #102, field AD does not match the meta specification Number=R (expected 3 value(s)). AD=..
    """
    non_critical_format_fields = ['PL', 'AD', 'AC', 'GQ']
    non_critical_info_fields = ['AC']
    regexes = {
        r'^INFO (\w+) does not match the specification Number': non_critical_info_fields,
        r'^INFO (\w+) metadata Number is not ': non_critical_info_fields,
        r'^Line \d+: Sample #\d+, field (\w+) does not match the meta specification Number=': non_critical_format_fields,
        r'^Line \d+: FORMAT (\w+) metadata Type is not ': non_critical_format_fields,
        r'^Line \d+: FORMAT (\w+) metadata Number is not ': non_critical_format_fields,
        r'^Line \d+: INFO SVLEN must be equal to "length of ALT - length of REF" for non-symbolic alternate alleles. SVLEN=': None
    }
    for regex in regexes:
        match = re.match(regex, error)
        if match:
            if regexes[regex] is None:
                # No list of value to match against
                return False
            field_affected = match.group(1)
            if field_affected in regexes[regex]:
                return False
    return True


def parse_biovalidator_validation_results(metadata_check_file):
    """
    Read the biovalidator's report and extract the list of validation errors
    """
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    def clean_read(ifile):
        l = ifile.readline()
        if l:
            return ansi_escape.sub('', l).strip()

    if not metadata_check_file:
        return

    errors = []

    with open(metadata_check_file) as open_file:
        collect = False
        while True:
            line = clean_read(open_file)
            if line is None:
                break  # EOF
            elif not line:
                continue  # Empty line
            if not collect:
                if line.startswith('Validation failed with following error(s):'):
                    collect = True
            else:
                while line and not line.startswith('/'):
                    # Sometimes there are multiple (possibly redundant) errors listed under a single property,
                    # we only report the first
                    line = clean_read(open_file)
                line2 = clean_read(open_file)
                if line is None or line2 is None:
                    break  # EOF
                errors.append({'property': line, 'description': line2})
    return errors


def convert_metadata_sheet(json_attribute, xls2json_conf):
    if json_attribute is None:
        return None
    for sheet_name in xls2json_conf['worksheets']:
        if xls2json_conf['worksheets'][sheet_name] == json_attribute:
            return sheet_name


def convert_metadata_row(sheet, json_row, xls2json_conf):
    if json_row is None:
        return ''
    if 'header_row' in xls2json_conf[sheet]:
        return int(json_row) + xls2json_conf[sheet]['header_row']
    else:
        return int(json_row) + 2


def convert_metadata_attribute(sheet, json_attribute, xls2json_conf):
    if json_attribute is None:
        return ''
    attributes_dict = {}
    attributes_dict.update(xls2json_conf[sheet].get('required', {}))
    attributes_dict.update(xls2json_conf[sheet].get('optional', {}))
    attributes_dict['Scientific Name'] = 'species'
    attributes_dict['BioSample Name'] = 'name'

    for attribute in attributes_dict:
        if attributes_dict[attribute] == json_attribute:
            return attribute


def parse_metadata_property(property_str):
    if property_str.startswith('.'):
        return property_str.strip('./'), None, None
    # First attempt to parse as BioSample object
    sheet, row, col = parse_sample_metadata_property(property_str)
    if sheet is not None and row is not None and col is not None:
        return sheet, row, col
    match = re.match(r'/(\w+)(/(\d+))?([./](\w+))?', property_str)
    if match:
        return match.group(1), match.group(3), match.group(5)
    else:
        logger.error(f'Cannot parse {property_str} in JSON metadata error')
        return None, None, None


def parse_sample_metadata_property(property_str):
    # Check characteristics
    match = re.match(r'/sample/(\d+)/bioSampleObject/characteristics/(\w+)', property_str)
    if match:
        return 'sample', match.group(1), match.group(2)
    # Check name
    match = re.match(r'/sample/(\d+)/bioSampleObject/name', property_str)
    if match:
        return 'sample', match.group(1), 'name'
    return None, None, None
