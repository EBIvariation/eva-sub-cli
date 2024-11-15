#!/usr/bin/env python
import csv
import datetime
import json
import logging
import os
from functools import lru_cache, cached_property

import yaml
from ebi_eva_common_pyutils.command_utils import run_command_with_output
from ebi_eva_common_pyutils.config import WritableConfig

from eva_sub_cli import ETC_DIR, SUB_CLI_CONFIG_FILE, __version__
from eva_sub_cli.file_utils import backup_file_or_directory, resolve_single_file_path
from eva_sub_cli.report import generate_html_report
from ebi_eva_common_pyutils.logger import logging_config, AppLogger

from eva_sub_cli.validators.validation_results_parsers import parse_assembly_check_log, parse_assembly_check_report, \
    parse_biovalidator_validation_results, convert_metadata_sheet, convert_metadata_row, convert_metadata_attribute, \
    parse_vcf_check_report, parse_metadata_property

VALIDATION_OUTPUT_DIR = "validation_output"
VALIDATION_RESULTS_KEY = 'validation_results'
VALIDATION_RESULTS_FILE = 'validation_results.yaml'
READY_FOR_SUBMISSION_TO_EVA = 'ready_for_submission_to_eva'

logger = logging_config.get_logger(__name__)


class Validator(AppLogger):

    def __init__(self, mapping_file, submission_dir, project_title=None, metadata_json=None, metadata_xlsx=None,
                 shallow_validation=False, submission_config: WritableConfig = None):
        # validator write to the validation output directory
        # If the submission_config is not set it will also be written to the VALIDATION_OUTPUT_DIR
        self.submission_dir = submission_dir
        self.output_dir = os.path.join(submission_dir, VALIDATION_OUTPUT_DIR)
        self.validation_result_file = os.path.join(submission_dir, VALIDATION_RESULTS_FILE)
        self.mapping_file = mapping_file
        vcf_files, fasta_files = self._find_vcf_and_fasta_files()
        self.vcf_files = vcf_files
        self.fasta_files = fasta_files
        self.results = {'shallow_validation': {'requested': shallow_validation}}
        self.project_title = project_title
        self.validation_date = datetime.datetime.now()
        self.metadata_json = metadata_json
        self.metadata_xlsx = metadata_xlsx
        self.shallow_validation = shallow_validation
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
        self._assess_validation_results()
        self._save_validation_results()

    def report(self):
        self.create_reports()

    def _validate(self):
        raise NotImplementedError

    def set_up_output_dir(self):
        if os.path.exists(self.output_dir):
            backup_file_or_directory(self.output_dir, max_backups=9)
        os.makedirs(self.output_dir, exist_ok=True)

    def clean_up_output_dir(self):
        # Move intermediate validation outputs into a subdir except metadata.json
        subdir = os.path.join(self.output_dir, 'other_validations')
        os.mkdir(subdir)
        for file_name in os.listdir(self.output_dir):
            if file_name == 'metadata.json':
                continue
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

    def verify_ready_for_submission_to_eva(self):
        """ Checks if all the validation are passed """
        return all((
            all((value.get('pass', False) is True for key, value in self.results.items() if
                 key in ['vcf_check', 'assembly_check', 'fasta_check', 'sample_check', 'metadata_check'])),
            any((
                self.results['shallow_validation']['requested'] is False,
                self.results['shallow_validation'].get('required', True) is False
            ))
        ))

    def _collect_validation_workflow_results(self):
        # Collect information from the output and summarise in the config
        if self.shallow_validation:
            self._collect_trim_down_metrics()
        self._collect_vcf_check_results()
        self._collect_assembly_check_results()
        self._load_sample_check_results()
        self._load_fasta_check_results()
        self._collect_metadata_results()

    def _assess_validation_results(self):
        """
            Assess if the validation results are meeting expectations and marks them as "PASS: true" or "PASS: false"
            It assumes all validation have been parsed already.
        """
        # vcf_check result
        vcf_check_result = all((vcf_check.get('critical_count', 1) == 0
                                for vcf_name, vcf_check in self.results.get('vcf_check', {}).items()))
        self.results['vcf_check']['pass'] = vcf_check_result

        # assembly_check result
        asm_nb_mismatch_result = all((asm_check.get('nb_mismatch', 1) == 0
                                      for vcf_name, asm_check in self.results.get('assembly_check', {}).items()))
        asm_nb_error_result = all((asm_check.get('nb_error', 1) == 0
                                   for vcf_name, asm_check in self.results.get('assembly_check', {}).items()))
        self.results['assembly_check']['pass'] = asm_nb_mismatch_result and asm_nb_error_result

        # fasta_check result
        fasta_check_result = all((fa_file_check.get('all_insdc', False) is True
                                  for fa_file, fa_file_check in self.results.get('fasta_check', {}).items()))
        self.results['fasta_check']['pass'] = fasta_check_result

        # sample check result
        self.results['sample_check']['pass'] = self.results.get('sample_check', {}).get('overall_differences',
                                                                                        True) is False

        # metadata check result
        metadata_xlsx_result = len(self.results.get('metadata_check', {}).get('spreadsheet_errors', []) or []) == 0
        metadata_json_result = len(self.results.get('metadata_check', {}).get('json_errors', []) or []) == 0
        self.results['metadata_check']['pass'] = metadata_xlsx_result and metadata_json_result

        # update config based on the validation results
        self.sub_config.set(READY_FOR_SUBMISSION_TO_EVA, value=self.verify_ready_for_submission_to_eva())

    def _save_validation_results(self):
        with open(self.validation_result_file, 'w') as val_res_file:
            yaml.safe_dump(self.results, val_res_file)

        self.debug(f"saved validation result in {self.validation_result_file}")

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

    @cached_property
    def _sample_check_yaml(self):
        return resolve_single_file_path(os.path.join(self.output_dir, 'other_validations', 'sample_checker.yml'))

    def _collect_vcf_check_results(self,):
        # detect output files for vcf check
        self.results['vcf_check'] = {}
        for vcf_file in self.vcf_files:
            vcf_name = os.path.basename(vcf_file)

            vcf_check_log = self._vcf_check_log(vcf_name)
            vcf_check_text_report = self._vcf_check_text_report(vcf_name)

            if vcf_check_log and vcf_check_text_report:
                valid, warning_count, error_count, critical_count, error_list, critical_list = parse_vcf_check_report(vcf_check_text_report)
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

    def _collect_assembly_check_results(self):
        # detect output files for assembly check
        self.results['assembly_check'] = {}
        for vcf_file in self.vcf_files:
            vcf_name = os.path.basename(vcf_file)

            assembly_check_log = self._assembly_check_log(vcf_name)
            assembly_check_text_report = self._assembly_check_text_report(vcf_name)

            if assembly_check_log and assembly_check_text_report:
                error_list_from_log, nb_error_from_log, match, total = \
                    parse_assembly_check_log(assembly_check_log)
                mismatch_list, nb_mismatch, error_list_from_report, nb_error_from_report = \
                    parse_assembly_check_report(assembly_check_text_report)
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
        self.collect_biovalidator_validation_results()
        self._collect_semantic_metadata_results()
        if self.metadata_xlsx:
            self._convert_biovalidator_validation_to_spreadsheet()
            self._write_spreadsheet_validation_results()
        self._collect_file_info_to_metadata()

    def _load_spreadsheet_conversion_errors(self):
        errors_file = resolve_single_file_path(os.path.join(self.output_dir, 'other_validations',
                                                            'metadata_conversion_errors.yml'))
        if not errors_file:
            return
        with open(errors_file) as open_yaml:
            self.results['metadata_check']['spreadsheet_errors'] = yaml.safe_load(open_yaml)

    def collect_biovalidator_validation_results(self):
        """
        Read the biovalidator's report and extract the list of validation errors
        """
        metadata_check_file = resolve_single_file_path(os.path.join(self.output_dir, 'other_validations',
                                                                    'metadata_validation.txt'))
        errors = parse_biovalidator_validation_results(metadata_check_file)
        self.results['metadata_check'].update({
            'json_report_path': metadata_check_file,
            'json_errors': errors
        })

    def _collect_semantic_metadata_results(self):
        errors_file = resolve_single_file_path(os.path.join(self.output_dir, 'other_validations',
                                                            'metadata_semantic_check.yml'))
        if not errors_file:
            return
        with open(errors_file) as open_yaml:
            # errors is a list of dicts matching format of biovalidator errors
            errors = yaml.safe_load(open_yaml)
            # biovalidator error parsing always places a list here, even if no errors
            self.results['metadata_check']['json_errors'] += errors

    def _convert_biovalidator_validation_to_spreadsheet(self):
        config_file = os.path.join(ETC_DIR, "spreadsheet2json_conf.yaml")
        with open(config_file) as open_file:
            xls2json_conf = yaml.safe_load(open_file)

        if 'spreadsheet_errors' not in self.results['metadata_check']:
            self.results['metadata_check']['spreadsheet_errors'] = []
        for error in self.results['metadata_check'].get('json_errors', {}):
            sheet_json, row_json, attribute_json = parse_metadata_property(error['property'])
            # There should only be one Project but adding the row back means it's easier for users to find
            if sheet_json == 'project' and row_json is None:
                row_json = 0
            sheet = convert_metadata_sheet(sheet_json, xls2json_conf)
            row = convert_metadata_row(sheet, row_json, xls2json_conf)
            column = convert_metadata_attribute(sheet, attribute_json, xls2json_conf)
            if row_json is None and attribute_json is None and sheet is not None:
                new_description = f'Sheet "{sheet}" is missing'
            elif row_json is None:
                if 'have required' not in error['description']:
                    new_description = error['description']
                else:
                    new_description = f'Column "{column}" is not populated'
            elif attribute_json and column:
                if 'have required' not in error['description']:
                    new_description = error['description']
                else:
                    new_description = f'Column "{column}" is not populated'
            else:
                new_description = error["description"].replace(sheet_json, sheet)
            if column is None:
                # We do not know this attribute.
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

    def _collect_file_info_to_metadata(self):
        md5sum_file = resolve_single_file_path(os.path.join(self.output_dir, 'other_validations', 'file_info.txt'))
        file_path_2_md5 = {}
        file_name_2_md5 = {}
        file_path_2_file_size = {}
        file_name_2_file_size = {}
        if md5sum_file:
            with open(md5sum_file) as open_file:
                for line in open_file:
                    sp_line = line.split(' ')
                    md5sum = sp_line[0]
                    file_size = int(sp_line[1])
                    vcf_file = sp_line[2].strip()
                    file_path_2_md5[vcf_file] = md5sum
                    file_name_2_md5[os.path.basename(vcf_file)] = md5sum
                    file_path_2_file_size[vcf_file] = file_size
                    file_name_2_file_size[os.path.basename(vcf_file)] = file_size
        else:
            self.error(
                f"Cannot locate file_info.txt at {os.path.join(self.output_dir, 'other_validations', 'file_info.txt')}"
            )
        if self.metadata_json_post_validation:
            with open(self.metadata_json_post_validation) as open_file:
                try:
                    json_data = json.load(open_file)
                    file_rows = []
                    files_from_metadata = json_data.get('files', [])
                    if files_from_metadata:
                        for file_dict in json_data.get('files', []):
                            file_path = self._validation_file_path_for(file_dict.get('fileName'))
                            file_dict['md5'] = file_path_2_md5.get(file_path) or \
                                               file_name_2_md5.get(file_dict.get('fileName')) or ''
                            file_dict['fileSize'] = file_path_2_file_size.get(file_path) or \
                                               file_name_2_file_size.get(file_dict.get('fileName')) or ''
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
        else:
            self.error(f'Cannot locate the metadata in JSON format in {os.path.join(self.output_dir, "metadata.json")}')

    def _collect_trim_down_metrics(self):
        self.results['shallow_validation']['metrics'] = {}
        shallow_validation_required = False
        for vcf_file in self.vcf_files:
            basename = os.path.basename(vcf_file)
            vcf_name, _ = os.path.splitext(basename)
            trimmed_down_metrics = resolve_single_file_path(os.path.join(self.output_dir, 'other_validations',
                                                                         f'{vcf_name}_trim_down.yml'))
            with open(trimmed_down_metrics) as open_file:
                metrics = yaml.safe_load(open_file)
                shallow_validation_required = shallow_validation_required or metrics['trim_down_required']
                self.results['shallow_validation']['metrics'][vcf_file] = metrics
        self.results['shallow_validation']['required'] = shallow_validation_required

    def get_vcf_fasta_analysis_mapping(self):
        vcf_fasta_analysis_mapping = []
        with open(self.mapping_file) as open_file:
            reader = csv.DictReader(open_file, delimiter=',')
            for row in reader:
                vcf_fasta_analysis_mapping.append({'vcf_file': row['vcf'], 'fasta_file': row['fasta']})

        if self.metadata_json_post_validation:
            with open(self.metadata_json_post_validation) as open_file:
                try:
                    vcf_analysis_dict = {}
                    json_data = json.load(open_file)
                    if json_data.get('files', []):
                        for file in json_data.get('files', []):
                            if file.get('fileName', []) and file.get('analysisAlias', []):
                                vcf_analysis_dict[file.get('fileName')] = file.get('analysisAlias')

                    for vcf_fasta_mapping in vcf_fasta_analysis_mapping:
                        vcf_file = vcf_fasta_mapping.get('vcf_file')
                        if vcf_file in vcf_analysis_dict:
                            vcf_fasta_mapping.update({'analysis': vcf_analysis_dict.get(vcf_file)})
                        else:
                            vcf_fasta_mapping.update({'analysis': 'Could not be linked'})

                    return vcf_fasta_analysis_mapping
                except Exception as e:
                    self.error('Error building Validation Report : Error getting info from metadata file' + str(e))
        else:
            self.error('Error building validation report : Metadata file not present')

    def create_reports(self):
        report_html = generate_html_report(self.results, self.validation_date, self.submission_dir,
                                           self.get_vcf_fasta_analysis_mapping(),
                                           self.project_title)
        file_path = os.path.join(self.output_dir, 'report.html')
        with open(file_path, "w") as f:
            f.write(report_html)
        self.info(f'Validation result: {"SUCCESS" if self.verify_ready_for_submission_to_eva() else "FAILURE"}')
        self.info(f'View the full report in your browser: {file_path}')
        return file_path
