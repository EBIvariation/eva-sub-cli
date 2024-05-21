#!/usr/bin/env python
import csv
import datetime
import glob
import json
import logging
import os
import re
import shutil
from functools import lru_cache, cached_property

import yaml
from ebi_eva_common_pyutils.command_utils import run_command_with_output
from ebi_eva_common_pyutils.config import WritableConfig

from eva_sub_cli import ETC_DIR, SUB_CLI_CONFIG_FILE, __version__
from eva_sub_cli.file_utils import backup_file_or_directory
from eva_sub_cli.report import generate_html_report
from ebi_eva_common_pyutils.logger import logging_config, AppLogger

VALIDATION_OUTPUT_DIR = "validation_output"
VALIDATION_RESULTS = 'validation_results'
READY_FOR_SUBMISSION_TO_EVA = 'ready_for_submission_to_eva'

logger = logging_config.get_logger(__name__)


def resolve_single_file_path(file_path):
    files = glob.glob(file_path)
    if len(files) == 0:
        return None
    elif len(files) > 0:
        return files[0]


class Validator(AppLogger):

    def __init__(self, mapping_file, submission_dir, metadata_json=None, metadata_xlsx=None,
                 submission_config: WritableConfig = None):
        # validator write to the validation output directory
        # If the submission_config is not set it will also be written to the VALIDATION_OUTPUT_DIR
        self.output_dir = os.path.join(submission_dir, VALIDATION_OUTPUT_DIR)
        self.mapping_file = mapping_file
        vcf_files, fasta_files = self._find_vcf_and_fasta_files()
        self.vcf_files = vcf_files
        self.fasta_files = fasta_files
        self.results = {}
        self.project_title = None  # TODO fill this from metadata?
        self.validation_date = datetime.datetime.now()
        self.metadata_json = metadata_json
        self.metadata_xlsx = metadata_xlsx
        if submission_config:
            self.sub_config = submission_config
        else:
            config_file = os.path.join(submission_dir, SUB_CLI_CONFIG_FILE)
            self.sub_config = WritableConfig(config_file, version=__version__)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.sub_config.backup()
        self.sub_config.write()

    @property
    def metadata_json_post_validation(self):
        if self.metadata_json:
            return self.metadata_json
        return resolve_single_file_path(os.path.join(self.output_dir, 'metadata.json'))

    @staticmethod
    def _run_quiet_command(command_description, command, **kwargs):
        return run_command_with_output(command_description, command, stdout_log_level=logging.DEBUG,
                                       stderr_log_level=logging.DEBUG, **kwargs)

    def _find_vcf_and_fasta_files(self):
        vcf_files = []
        fasta_files = []
        with open(self.mapping_file) as open_file:
            reader = csv.DictReader(open_file, delimiter=',')
            for row in reader:
                vcf_files.append(row['vcf'])
                fasta_files.append(row['fasta'])
        return vcf_files, fasta_files

    def validate_and_report(self):
        self.info('Start validation')
        self.validate()
        self.info('Create report')
        self.report()

    def validate(self):
        self.set_up_output_dir()
        self.verify_files_present()
        self._validate()
        self.clean_up_output_dir()
        self._collect_validation_workflow_results()

    def report(self):
        self.create_reports()
        self.update_config_with_validation_result()

    def _validate(self):
        raise NotImplementedError

    def set_up_output_dir(self):
        if os.path.exists(self.output_dir):
            backup_file_or_directory(self.output_dir, max_backups=9)
        os.makedirs(self.output_dir, exist_ok=True)

    def clean_up_output_dir(self):
        # Move intermediate validation outputs into a subdir
        subdir = os.path.join(self.output_dir, 'other_validations')
        os.mkdir(subdir)
        for file_name in os.listdir(self.output_dir):
            file_path = os.path.join(self.output_dir, file_name)
            if os.path.isfile(file_path):
                os.rename(file_path, os.path.join(subdir, file_name))

    @staticmethod
    def _validation_file_path_for(file_path):
        return file_path

    def verify_files_present(self):
        # verify mapping file exists
        if not os.path.exists(self.mapping_file):
            raise FileNotFoundError(f'Mapping file {self.mapping_file} not found')

        # verify all files mentioned in metadata files exist
        files_missing, missing_files_list = self.check_if_file_missing()
        if files_missing:
            raise FileNotFoundError(f"some files (vcf/fasta) mentioned in metadata file could not be found. "
                               f"Missing files list {missing_files_list}")

    def check_if_file_missing(self):
        files_missing = False
        missing_files_list = []
        with open(self.mapping_file) as open_file:
            reader = csv.DictReader(open_file, delimiter=',')
            for row in reader:
                if not os.path.exists(row['vcf']):
                    files_missing = True
                    missing_files_list.append(row['vcf'])
                if not os.path.exists(row['fasta']):
                    files_missing = True
                    missing_files_list.append(row['fasta'])
                # Assembly report is optional but should exist if it is set.
                if row.get('report') and not os.path.exists(row['report']):
                    files_missing = True
                    missing_files_list.append(row['report'])
        return files_missing, missing_files_list

    def update_config_with_validation_result(self):
        self.sub_config.set(VALIDATION_RESULTS, value=self.results)
        self.sub_config.set(READY_FOR_SUBMISSION_TO_EVA, value=self.verify_ready_for_submission_to_eva())

    def verify_ready_for_submission_to_eva(self):
        # TODO:  check validation results and confirm if they are good enough for submitting to EVA
        return True

    def parse_assembly_check_log(self, assembly_check_log):
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

    def parse_assembly_check_report(self, assembly_check_report):
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
        return mismatch_list, nb_mismatch, error_list, nb_error

    def parse_vcf_check_report(self, vcf_check_report):
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
                elif self.vcf_check_errors_is_critical(line.strip()):
                    critical_count += 1
                    if critical_count <= max_error_reported:
                        critical_list.append(line.strip())
                else:
                    error_count += 1
                    if error_count <= max_error_reported:
                        error_list.append(line.strip())

        return valid, warning_count, error_count, critical_count, error_list, critical_list

    def vcf_check_errors_is_critical(self, error):
        """
        This function identify VCF check errors that are not critical for the processing of the VCF within EVA.
        They affect specific INFO or FORMAT fields that are used in the variant detection but less so in the downstream analysis.
        Critical:
        Reference and alternate alleles must not be the same.
        Requested evidence presence with --require-evidence. Please provide genotypes (GT field in FORMAT and samples), or allele frequencies (AF field in INFO), or allele counts (AC and AN fields in INFO)..
        Contig is not sorted by position. Contig chr10 position 41695506 found after 41883113.
        Duplicated variant chr1A:1106203:A>G found.
        Metadata description string is not valid.

        Error
        Sample #10, field PL does not match the meta specification Number=G (expected 2 value(s)). PL=.. It must derive its number of values from the ploidy of GT (if present), or assume diploidy. Contains 1 value(s), expected 2 (derived from ploidy 1).
        Sample #102, field AD does not match the meta specification Number=R (expected 3 value(s)). AD=..
        """
        non_critical_format_fields = ['PL', 'AD', 'AC']
        non_critical_info_fields = ['AC']
        regexes = {
            r'^INFO (\w+) does not match the specification Number': non_critical_format_fields,
            r'^Sample #\d+, field (\w+) does not match the meta specification Number=': non_critical_info_fields
        }
        for regex in regexes:
            match = re.match(regex, error)
            if match:
                field_affected = match.group(1)
                if field_affected in regexes[regex]:
                    return False
        return True

    def _collect_validation_workflow_results(self):
        # Collect information from the output and summarise in the config
        self._collect_vcf_check_results()
        self._collect_assembly_check_results()
        self._load_sample_check_results()
        self._load_fasta_check_results()
        self._collect_metadata_results()

    @lru_cache
    def _vcf_check_log(self, vcf_name):
        return resolve_single_file_path(
            os.path.join(self.output_dir, 'vcf_format', vcf_name + '.vcf_format.log')
        )

    @lru_cache
    def _vcf_check_text_report(self, vcf_name):
        return resolve_single_file_path(
            os.path.join(self.output_dir, 'vcf_format', vcf_name + '.*.txt')
        )

    @lru_cache
    def _vcf_check_db_report(self, vcf_name):
        return resolve_single_file_path(
            os.path.join(self.output_dir, 'vcf_format', vcf_name + '.*.db')
        )

    def _collect_vcf_check_results(self,):
        # detect output files for vcf check
        self.results['vcf_check'] = {}
        for vcf_file in self.vcf_files:
            vcf_name = os.path.basename(vcf_file)

            vcf_check_log = self._vcf_check_log(vcf_name)
            vcf_check_text_report = self._vcf_check_text_report(vcf_name)
            vcf_check_db_report = self._vcf_check_db_report(vcf_name)

            if vcf_check_log and vcf_check_text_report and vcf_check_db_report:
                valid, warning_count, error_count, critical_count, error_list, critical_list = self.parse_vcf_check_report(vcf_check_text_report)
            else:
                valid, warning_count, error_count, critical_count, error_list, critical_list = (False, 0, 0, 1, [], ['Process failed'])
            self.results['vcf_check'][vcf_name] = {
                'report_path': vcf_check_text_report,
                'valid': valid,
                'error_list': error_list,
                'error_count': error_count,
                'warning_count': warning_count,
                'critical_count': critical_count,
                'critical_list': critical_list
            }

    @lru_cache
    def _assembly_check_log(self, vcf_name):
        return resolve_single_file_path(
            os.path.join(self.output_dir, 'assembly_check', vcf_name + '.assembly_check.log')
        )

    @lru_cache
    def _assembly_check_text_report(self, vcf_name):
        return resolve_single_file_path(
            os.path.join(self.output_dir, 'assembly_check', vcf_name + '*text_assembly_report*')
        )

    def _collect_assembly_check_results(self):
        # detect output files for assembly check
        self.results['assembly_check'] = {}
        for vcf_file in self.vcf_files:
            vcf_name = os.path.basename(vcf_file)

            assembly_check_log = self._assembly_check_log(vcf_name)
            assembly_check_text_report = self._assembly_check_text_report(vcf_name)

            if assembly_check_log and assembly_check_text_report:
                error_list_from_log, nb_error_from_log, match, total = \
                    self.parse_assembly_check_log(assembly_check_log)
                mismatch_list, nb_mismatch, error_list_from_report, nb_error_from_report = \
                    self.parse_assembly_check_report(assembly_check_text_report)
                nb_error = nb_error_from_log + nb_error_from_report
                error_list = error_list_from_log + error_list_from_report
            else:
                error_list, mismatch_list, nb_mismatch, nb_error, match, total = (['Process failed'], [], 0, 1, 0, 0)
            self.results['assembly_check'][vcf_name] = {
                'report_path': assembly_check_text_report,
                'error_list': error_list,
                'mismatch_list': mismatch_list,
                'nb_mismatch': nb_mismatch,
                'nb_error': nb_error,
                'match': match,
                'total': total
            }

    @cached_property
    def _sample_check_yaml(self):
        return resolve_single_file_path(os.path.join(self.output_dir, 'other_validations', 'sample_checker.yml'))

    def _load_fasta_check_results(self):
        for fasta_file in self.fasta_files:
            fasta_file_name = os.path.basename(fasta_file)
            fasta_check = resolve_single_file_path(os.path.join(self.output_dir, 'other_validations',
                                                                f'{fasta_file_name}_check.yml'))
            self.results['fasta_check'] = {}
            if not fasta_check:
                continue
            with open(fasta_check) as open_yaml:
                self.results['fasta_check'][fasta_file_name] = yaml.safe_load(open_yaml)

    def _load_sample_check_results(self):
        self.results['sample_check'] = {}
        if not self._sample_check_yaml:
            return
        with open(self._sample_check_yaml) as open_yaml:
            self.results['sample_check'] = yaml.safe_load(open_yaml)
        self.results['sample_check']['report_path'] = self._sample_check_yaml

    def _collect_metadata_results(self):
        self.results['metadata_check'] = {}
        self._load_spreadsheet_conversion_errors()
        self._parse_biovalidator_validation_results()
        self._convert_biovalidator_validation_to_spreadsheet()
        self._write_spreadsheet_validation_results()
        self._collect_md5sum_to_metadata()

    def _load_spreadsheet_conversion_errors(self):
        errors_file = resolve_single_file_path(os.path.join(self.output_dir, 'other_validations',
                                                            'metadata_conversion_errors.yml'))
        if not errors_file:
            return
        with open(errors_file) as open_yaml:
            self.results['metadata_check']['spreadsheet_errors'] = yaml.safe_load(open_yaml)

    def _parse_biovalidator_validation_results(self):
        """
        Read the biovalidator's report and extract the list of validation errors
        """
        metadata_check_file = resolve_single_file_path(os.path.join(self.output_dir, 'other_validations',
                                                                    'metadata_validation.txt'))
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

        def clean_read(ifile):
            l = ifile.readline()
            if l:
                return ansi_escape.sub('', l).strip()

        if not metadata_check_file:
            return
        with open(metadata_check_file) as open_file:
            errors = []
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
                    line2 = clean_read(open_file)
                    if line is None or line2 is None:
                        break  # EOF
                    errors.append({'property': line, 'description': line2})
        self.results['metadata_check'].update({
            'json_report_path': metadata_check_file,
            'json_errors': errors
        })

    def _parse_metadata_property(self, property_str):
        if property_str.startswith('.'):
            return property_str.strip('.'), None, None
        match = re.match(r'/(\w+)(/(\d+))?([./](\w+))?', property_str)
        if match:
            return match.group(1), match.group(3), match.group(5)
        else:
            logger.error(f'Cannot parse {property_str} in JSON metadata error')
            return None, None, None

    def _convert_biovalidator_validation_to_spreadsheet(self):
        config_file = os.path.join(ETC_DIR, "spreadsheet2json_conf.yaml")
        with open(config_file) as open_file:
            xls2json_conf = yaml.safe_load(open_file)

        if 'spreadsheet_errors' not in self.results['metadata_check']:
            self.results['metadata_check']['spreadsheet_errors'] = []
        for error in self.results['metadata_check'].get('json_errors', {}):
            sheet_json, row_json, attribute_json = self._parse_metadata_property(error['property'])
            sheet = self._convert_metadata_sheet(sheet_json, xls2json_conf)
            row = self._convert_metadata_row(sheet, row_json, xls2json_conf)
            column = self._convert_metadata_attribute(sheet, attribute_json, xls2json_conf)
            if row_json is None and attribute_json is None:
                new_description = f'Sheet "{sheet}" is missing'
            elif row_json is None:
                new_description = f'In sheet "{sheet}", column "{column}" is not populated'
            elif attribute_json and column:
                new_description = f'In sheet "{sheet}", row "{row}", column "{column}" is not populated'
            else:
                new_description = error["description"].replace(sheet_json, sheet)
            if column is None:
                # We do not know this attribute. It's most likely about bioSampleObject
                continue
            if 'schema' in new_description:
                # This is an error specific to json schema
                continue
            self.results['metadata_check']['spreadsheet_errors'].append({
                'sheet': sheet, 'row': row, 'column': column,
                'description': new_description
            })

    def _write_spreadsheet_validation_results(self):
        if ('spreadsheet_errors' in self.results['metadata_check']
                and 'json_report_path' in self.results['metadata_check']):
            spreadsheet_report_file = os.path.join(os.path.dirname(self.results['metadata_check']['json_report_path']),
                                                   'metadata_spreadsheet_validation.txt')
            with open(spreadsheet_report_file, 'w') as open_file:
                for error_dict in self.results['metadata_check']['spreadsheet_errors']:
                    open_file.write(error_dict.get('description') + '\n')
            self.results['metadata_check']['spreadsheet_report_path'] = spreadsheet_report_file

    def _convert_metadata_sheet(self, json_attribute, xls2json_conf):
        if json_attribute is None:
            return None
        for sheet_name in xls2json_conf['worksheets']:
            if xls2json_conf['worksheets'][sheet_name] == json_attribute:
                return sheet_name

    def _convert_metadata_row(self, sheet, json_row, xls2json_conf):
        if json_row is None:
            return ''
        if 'header_row' in xls2json_conf[sheet]:
            return int(json_row) + xls2json_conf[sheet]['header_row']
        else:
            return int(json_row) + 2

    def _convert_metadata_attribute(self, sheet, json_attribute, xls2json_conf):
        if json_attribute is None:
            return ''
        attributes_dict = {}
        attributes_dict.update(xls2json_conf[sheet].get('required', {}))
        attributes_dict.update(xls2json_conf[sheet].get('optional', {}))
        for attribute in attributes_dict:
            if attributes_dict[attribute] == json_attribute:
                return attribute

    def _collect_md5sum_to_metadata(self):
        md5sum_file = resolve_single_file_path(os.path.join(self.output_dir, 'other_validations', 'md5sums.txt'))
        file_path_2_md5 = {}
        file_name_2_md5 = {}
        if md5sum_file:
            with open(md5sum_file) as open_file:
                for line in open_file:
                    sp_line = line.split(' ')
                    md5sum = sp_line[0]
                    vcf_file = line.strip()[len(md5sum):].lstrip()  # Remove the md5: the rest is the file path
                    file_path_2_md5[vcf_file] = md5sum
                    file_name_2_md5[os.path.basename(vcf_file)] = md5sum
        if self.metadata_json_post_validation:
            with open(self.metadata_json_post_validation) as open_file:
                try:
                    json_data = json.load(open_file)
                    analysis_aliases = [a.get('analysisAlias') for a in json_data.get('analysis', [])]
                    file_rows = []
                    files_from_metadata = json_data.get('files', [])
                    if files_from_metadata:
                        for file_dict in json_data.get('files', []):
                            if file_dict.get('fileType') == 'vcf':
                                file_path = self._validation_file_path_for(file_dict.get('fileName'))
                                file_dict['md5'] = file_path_2_md5.get(file_path) or \
                                                   file_name_2_md5.get(file_dict.get('fileName')) or ''
                            file_rows.append(file_dict)
                    else:
                        self.error('No file found in metadata and multiple analysis alias exist: '
                                   'cannot infer the relationship between files and analysis alias')
                    json_data['files'] = file_rows
                except Exception as e:
                    # Skip adding the md5
                    self.error('Error while loading or parsing metadata json: ' + str(e))
            if json_data:
                with open(self.metadata_json_post_validation, 'w') as open_file:
                    json.dump(json_data, open_file)

    def create_reports(self):
        report_html = generate_html_report(self.results, self.validation_date, self.project_title)
        file_path = os.path.join(self.output_dir, 'report.html')
        with open(file_path, "w") as f:
            f.write(report_html)
        self.info(f'View the validation report in your browser: {file_path}')
        return file_path
