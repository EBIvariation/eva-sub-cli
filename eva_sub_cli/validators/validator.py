#!/usr/bin/env python
import csv
import datetime
import logging
import os
from functools import lru_cache, cached_property

import yaml
from ebi_eva_common_pyutils.command_utils import run_command_with_output
from ebi_eva_common_pyutils.config import WritableConfig
from ebi_eva_common_pyutils.logger import logging_config, AppLogger
from packaging import version

import eva_sub_cli
from eva_sub_cli import ETC_DIR, SUB_CLI_CONFIG_FILE, __version__
from eva_sub_cli.file_utils import backup_file_or_directory, resolve_single_file_path
from eva_sub_cli.metadata import EvaMetadataJson
from eva_sub_cli.report import generate_html_report, generate_text_report
from eva_sub_cli.validators.validation_results_parsers import parse_assembly_check_log, parse_assembly_check_report, \
    parse_biovalidator_validation_results, convert_metadata_sheet, convert_metadata_row, convert_metadata_attribute, \
    parse_vcf_check_report, parse_metadata_property

VALIDATION_OUTPUT_DIR = "validation_output"
VALIDATION_RESULTS_FILE = 'validation_results.yaml'
READY_FOR_SUBMISSION_TO_EVA = 'ready_for_submission_to_eva'

VCF_CHECK = 'vcf_check'
EVIDENCE_TYPE_CHECK = 'evidence_type_check'
ASSEMBLY_CHECK = 'assembly_check'
FASTA_CHECK = 'fasta_check'
METADATA_CHECK = 'metadata_check'
SAMPLE_CHECK = 'sample_check'
# Tasks that can be requested by user.
# Here VCF_CHECK includes both vcf_validator and evidence type check,
# and ASSEMBLY_CHECK includes both vcf_assembly and INSDC check.
ALL_VALIDATION_TASKS = [VCF_CHECK, ASSEMBLY_CHECK, METADATA_CHECK, SAMPLE_CHECK]
# Tasks used for the purpose of reporting results.
ALL_VALIDATION_TASKS_GRANULAR = [VCF_CHECK, EVIDENCE_TYPE_CHECK, ASSEMBLY_CHECK, FASTA_CHECK, SAMPLE_CHECK,
                                 METADATA_CHECK]
SHALLOW_VALIDATION = 'shallow_validation'
TRIM_DOWN = 'trim_down'
RUN_STATUS_KEY = 'run_status'
PASS = 'pass'

logger = logging_config.get_logger(__name__)


class Validator(AppLogger):

    def __init__(self, mapping_file, submission_dir, project_title=None, metadata_json=None, metadata_xlsx=None,
                 metadata_xlsx_version=None, validation_tasks=ALL_VALIDATION_TASKS, shallow_validation=False,
                 submission_config: WritableConfig = None):
        # validator write to the validation output directory
        # If the submission_config is not set it will also be written to the VALIDATION_OUTPUT_DIR
        self.tasks = validation_tasks
        self.submission_dir = submission_dir
        self.output_dir = os.path.join(submission_dir, VALIDATION_OUTPUT_DIR)
        self.validation_result_file = os.path.join(submission_dir, VALIDATION_RESULTS_FILE)
        self.mapping_file = mapping_file
        vcf_files, fasta_files = self._find_vcf_and_fasta_files()
        self.vcf_files = vcf_files
        self.fasta_files = fasta_files
        self.results = {}
        self.project_title = project_title
        self.validation_date = datetime.datetime.now()
        self.metadata_json = metadata_json
        self.metadata_xlsx = metadata_xlsx
        self.metadata_xlsx_version = metadata_xlsx_version
        self.shallow_validation = (shallow_validation and
                                   any(v in [VCF_CHECK, ASSEMBLY_CHECK] for v in validation_tasks))
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

    def _get_xlsx_conversion_configuration_name(self):
        if version.parse(self.metadata_xlsx_version) < version.parse('3.0.0'):
            return 'spreadsheet2json_conf_V2.yaml'
        else:
            return 'spreadsheet2json_conf.yaml'

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
        self._load_previous_validation_results()
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
        raise NotImplementedError

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
            all(key in self.results and self.results[key].get(PASS, False) is True for key in ALL_VALIDATION_TASKS_GRANULAR),
            all(self.results[key].get(TRIM_DOWN, False) is False for key in ALL_VALIDATION_TASKS_GRANULAR),
        ))

    def _load_previous_validation_results(self):
        if os.path.exists(self.validation_result_file):
            with open(self.validation_result_file, 'r') as val_res_file:
                self.results = yaml.safe_load(val_res_file) or {}

        # update previous shallow validation format to new one, if applicable
        if 'version' in self.results:
            if version.parse(self.results['version']) < version.parse('v0.4.15'):
                self.update_previous_version_results()
        else:
            self.update_previous_version_results()

    def update_previous_version_results(self):
        if 'requested' in self.results.get(SHALLOW_VALIDATION, {}):
            if 'required' in self.results.get(SHALLOW_VALIDATION, {}):
                if self.results.get(SHALLOW_VALIDATION, {}).get('required', False):
                    self.results[VCF_CHECK][TRIM_DOWN] = True
                    self.results[ASSEMBLY_CHECK][TRIM_DOWN] = True
                    self.results[FASTA_CHECK][TRIM_DOWN] = True
                    self.results[SHALLOW_VALIDATION][TRIM_DOWN] = True
                    self.results[TRIM_DOWN] = True

                del self.results[SHALLOW_VALIDATION]['required']
            del self.results[SHALLOW_VALIDATION]['requested']


    def _collect_validation_workflow_results(self):
        # Collect information from the output and summarise in the config
        if self.shallow_validation:
            self._collect_trim_down_metrics()

        if VCF_CHECK in self.tasks:
            self._collect_vcf_check_results()
            self._load_evidence_check_results()

        if ASSEMBLY_CHECK in self.tasks:
            self._collect_assembly_check_results()
            self._load_fasta_check_results()

        if METADATA_CHECK in self.tasks:
            self._collect_metadata_results()

        if SAMPLE_CHECK in self.tasks:
            self._load_sample_check_results()

    def _assess_validation_results(self):
        """
            Assess if the validation results are meeting expectations and marks them as "PASS: true", "PASS: false"
            It assumes all validation have been parsed already.
        """

        if VCF_CHECK in self.tasks:
            # vcf_check result
            vcf_check_result = all((vcf_check.get('critical_count', 1) == 0
                                    for vcf_name, vcf_check in self.results.get(VCF_CHECK, {}).items()
                                    if isinstance(vcf_check, dict)))
            self.results[VCF_CHECK][PASS] = vcf_check_result

            # evidence type check result
            self.results[EVIDENCE_TYPE_CHECK][PASS] = (
                    any(isinstance(v, dict) for v in self.results.get(EVIDENCE_TYPE_CHECK, {}).values())
                    and
                    all('evidence_type' in v and v['evidence_type'] is not None
                        for v in self.results.get(EVIDENCE_TYPE_CHECK, {}).values()
                        if isinstance(v, dict)))
        elif VCF_CHECK not in self.results:
            self.results[VCF_CHECK] = {RUN_STATUS_KEY: False}
            self.results[EVIDENCE_TYPE_CHECK] = {RUN_STATUS_KEY: False}

        if ASSEMBLY_CHECK in self.tasks:
            # assembly_check result
            asm_nb_mismatch_result = all((asm_check.get('nb_mismatch', 1) == 0
                                          for vcf_name, asm_check in self.results.get(ASSEMBLY_CHECK, {}).items()
                                          if isinstance(asm_check, dict)))
            asm_nb_error_result = all((asm_check.get('nb_error', 1) == 0
                                       for vcf_name, asm_check in self.results.get(ASSEMBLY_CHECK, {}).items()
                                       if isinstance(asm_check, dict)))
            self.results[ASSEMBLY_CHECK][PASS] = asm_nb_mismatch_result and asm_nb_error_result

            # fasta_check result
            fasta_check_result = all((fa_file_check.get('all_insdc', False) is True
                                      for fa_file, fa_file_check in self.results.get(FASTA_CHECK, {}).items()
                                      if isinstance(fa_file_check, dict)))
            self.results[FASTA_CHECK][PASS] = fasta_check_result
        elif ASSEMBLY_CHECK not in self.results:
            self.results[ASSEMBLY_CHECK] = {RUN_STATUS_KEY: False}
            self.results[FASTA_CHECK] = {RUN_STATUS_KEY: False}

        if SAMPLE_CHECK in self.tasks:
            # sample check result
            self.results[SAMPLE_CHECK][PASS] = self.results.get(SAMPLE_CHECK, {}).get('overall_differences',
                                                                                      True) is False
        elif SAMPLE_CHECK not in self.results:
            self.results[SAMPLE_CHECK] = {RUN_STATUS_KEY: False}

        if METADATA_CHECK in self.tasks:
            # metadata check result
            metadata_xlsx_result = len(self.results.get(METADATA_CHECK, {}).get('spreadsheet_errors', []) or []) == 0
            metadata_json_result = len(self.results.get(METADATA_CHECK, {}).get('json_errors', []) or []) == 0
            self.results[METADATA_CHECK][PASS] = metadata_xlsx_result and metadata_json_result
        elif METADATA_CHECK not in self.results:
            self.results[METADATA_CHECK] = {RUN_STATUS_KEY: False}

        # update config based on the validation results
        self.sub_config.set(READY_FOR_SUBMISSION_TO_EVA, value=self.verify_ready_for_submission_to_eva())
        self.results[READY_FOR_SUBMISSION_TO_EVA] = self.verify_ready_for_submission_to_eva()
        # update shallow validation TRIM_DOWN val
        self.results[TRIM_DOWN] = any(self.results[key].get(TRIM_DOWN, False) is True
                                      for key in ALL_VALIDATION_TASKS_GRANULAR)
        self.results['version'] = eva_sub_cli.__version__

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

    @cached_property
    def _evidence_type_check_yaml(self):
        return resolve_single_file_path(os.path.join(self.output_dir, 'other_validations', 'evidence_type_checker.yml'))

    def _collect_vcf_check_results(self):
        # detect output files for vcf check
        self.results[VCF_CHECK] = {RUN_STATUS_KEY: True}
        if self.shallow_validation and self.results[SHALLOW_VALIDATION][TRIM_DOWN] is True:
            self.results[VCF_CHECK].update(TRIM_DOWN, True)

        for vcf_file in self.vcf_files:
            vcf_name = os.path.basename(vcf_file)

            vcf_check_log = self._vcf_check_log(vcf_name)
            vcf_check_text_report = self._vcf_check_text_report(vcf_name)

            if vcf_check_log and vcf_check_text_report:
                valid, warning_count, error_count, critical_count, error_list, critical_list = parse_vcf_check_report(
                    vcf_check_text_report)
            else:
                valid, warning_count, error_count, critical_count, error_list, critical_list = (False, 0, 0, 1, [],
                                                                                                ['Process failed'])
            self.results[VCF_CHECK][vcf_name] = {
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
        self.results[ASSEMBLY_CHECK] = {RUN_STATUS_KEY: True}
        if self.shallow_validation and self.results[SHALLOW_VALIDATION][TRIM_DOWN] is True:
            self.results[ASSEMBLY_CHECK].update(TRIM_DOWN, True)

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
            self.results[ASSEMBLY_CHECK][vcf_name] = {
                'report_path': assembly_check_text_report,
                'error_list': error_list,
                'mismatch_list': mismatch_list,
                'nb_mismatch': nb_mismatch,
                'nb_error': nb_error,
                'match': match,
                'total': total
            }

    def _load_fasta_check_results(self):
        self.results[FASTA_CHECK] = {RUN_STATUS_KEY: True}
        if self.shallow_validation and self.results[SHALLOW_VALIDATION][TRIM_DOWN] is True:
            self.results[FASTA_CHECK].update(TRIM_DOWN, True)

        for fasta_file in self.fasta_files:
            fasta_file_name = os.path.basename(fasta_file)
            fasta_check = resolve_single_file_path(os.path.join(self.output_dir, 'other_validations',
                                                                f'{fasta_file_name}_check.yml'))
            if not fasta_check:
                continue
            with open(fasta_check) as open_yaml:
                self.results[FASTA_CHECK][fasta_file_name] = yaml.safe_load(open_yaml)

    def _load_sample_check_results(self):
        self.results[SAMPLE_CHECK] = {}
        if self._sample_check_yaml:
            with open(self._sample_check_yaml) as open_yaml:
                self.results[SAMPLE_CHECK] = yaml.safe_load(open_yaml)
            self.results[SAMPLE_CHECK]['report_path'] = self._sample_check_yaml

        self.results[SAMPLE_CHECK].update({RUN_STATUS_KEY: True})

    def _load_evidence_check_results(self):
        self.results[EVIDENCE_TYPE_CHECK] = {}
        if self._evidence_type_check_yaml:
            with open(self._evidence_type_check_yaml) as open_yaml:
                self.results[EVIDENCE_TYPE_CHECK] = yaml.safe_load(open_yaml)
            self.results[EVIDENCE_TYPE_CHECK]['report_path'] = self._evidence_type_check_yaml
        self.results[EVIDENCE_TYPE_CHECK].update({RUN_STATUS_KEY: True})
        self._update_metadata_with_evidence_type()

    def _collect_metadata_results(self):
        self.results[METADATA_CHECK] = {RUN_STATUS_KEY: True}
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
            self.results[METADATA_CHECK]['spreadsheet_errors'] = yaml.safe_load(open_yaml)

    def collect_biovalidator_validation_results(self):
        """
        Read the biovalidator's report and extract the list of validation errors
        """
        metadata_check_file = resolve_single_file_path(os.path.join(self.output_dir, 'other_validations',
                                                                    'metadata_validation.txt'))
        errors = parse_biovalidator_validation_results(metadata_check_file)
        self.results[METADATA_CHECK].update({
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
            self.results[METADATA_CHECK]['json_errors'] += errors

    def _convert_biovalidator_validation_to_spreadsheet(self):
        config_file = os.path.join(ETC_DIR, "spreadsheet2json_conf.yaml")
        with open(config_file) as open_file:
            xls2json_conf = yaml.safe_load(open_file)

        if 'spreadsheet_errors' not in self.results[METADATA_CHECK]:
            self.results[METADATA_CHECK]['spreadsheet_errors'] = []
        for error in self.results[METADATA_CHECK].get('json_errors', {}):
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
                missing_property_error = f" have required property '{sheet_json}'"
                if not error['description'].endswith(missing_property_error):
                    new_description = error['description']
                else:
                    new_description = f'Column "{column}" is not populated'
            elif attribute_json and column:
                missing_property_error = f" have required property '{attribute_json}'"
                if not error['description'].endswith(missing_property_error):
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
            self.results[METADATA_CHECK]['spreadsheet_errors'].append({
                'sheet': sheet, 'row': row, 'column': column,
                'description': new_description
            })

    def _write_spreadsheet_validation_results(self):
        if ('spreadsheet_errors' in self.results[METADATA_CHECK]
                and 'json_report_path' in self.results[METADATA_CHECK]):
            spreadsheet_report_file = os.path.join(os.path.dirname(self.results[METADATA_CHECK]['json_report_path']),
                                                   'metadata_spreadsheet_validation.txt')
            with open(spreadsheet_report_file, 'w') as open_file:
                for error_dict in self.results[METADATA_CHECK]['spreadsheet_errors']:
                    open_file.write(error_dict.get('description') + '\n')
            self.results[METADATA_CHECK]['spreadsheet_report_path'] = spreadsheet_report_file

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
            metadata = EvaMetadataJson(self.metadata_json_post_validation)
            try:
                file_rows = []
                if metadata.files:
                    for file_dict in metadata.files:
                        file_path = self._validation_file_path_for(file_dict.get('fileName'))
                        file_dict['md5'] = file_path_2_md5.get(file_path) or \
                                           file_name_2_md5.get(file_dict.get('fileName')) or ''
                        file_dict['fileSize'] = file_path_2_file_size.get(file_path) or \
                                                file_name_2_file_size.get(file_dict.get('fileName')) or ''
                        file_rows.append(file_dict)
                else:
                    self.error('No file found in metadata and multiple analysis alias exist: '
                               'cannot infer the relationship between files and analysis alias')
                metadata.set_files(file_rows)
            except Exception as e:
                # Skip adding the md5
                self.error('Error while loading or parsing metadata json: ' + str(e))
            metadata.write(self.metadata_json_post_validation)
        else:
            self.error(f'Cannot locate the metadata in JSON format in {os.path.join(self.output_dir, "metadata.json")}')

    def _update_metadata_with_evidence_type(self):
        if self.metadata_json_post_validation:
            metadata = EvaMetadataJson(self.metadata_json_post_validation)
            try:
                analysis_data = []
                if metadata.analyses:
                    for analysis in metadata.analyses:
                        analysis_alias = analysis['analysisAlias']
                        if (analysis_alias in self.results['evidence_type_check']
                                and self.results['evidence_type_check'][analysis_alias]['evidence_type'] is not None):
                            analysis['evidenceType'] = self.results[EVIDENCE_TYPE_CHECK][analysis_alias][
                                'evidence_type']
                        analysis_data.append(analysis)
                else:
                    self.error('No analyses found in metadata')

                metadata.set_analyses(analysis_data)
            except Exception as e:
                # Skip adding the results in case of any exception or error
                self.error('Error while loading or parsing metadata json: ' + str(e))
            metadata.write(self.metadata_json_post_validation)
        else:
            self.error(f'Cannot locate the metadata in JSON format in {os.path.join(self.output_dir, "metadata.json")}')

    def _collect_trim_down_metrics(self):
        self.results[SHALLOW_VALIDATION] = {'metrics': {}}
        shallow_validation_required = False
        for vcf_file in self.vcf_files:
            basename = os.path.basename(vcf_file)
            vcf_name, _ = os.path.splitext(basename)
            trimmed_down_metrics = resolve_single_file_path(os.path.join(self.output_dir, 'other_validations',
                                                                         f'{vcf_name}_trim_down.yml'))
            with open(trimmed_down_metrics) as open_file:
                metrics = yaml.safe_load(open_file)
                shallow_validation_required = shallow_validation_required or metrics['trim_down_required']
                self.results[SHALLOW_VALIDATION]['metrics'][vcf_file] = metrics
        self.results[SHALLOW_VALIDATION][TRIM_DOWN] = shallow_validation_required

    def get_vcf_fasta_analysis_mapping(self):
        vcf_fasta_analysis_mapping = []
        with open(self.mapping_file) as open_file:
            reader = csv.DictReader(open_file, delimiter=',')
            for row in reader:
                vcf_fasta_analysis_mapping.append({'vcf_file': row['vcf'], 'fasta_file': row['fasta']})

        if self.metadata_json_post_validation:
            metadata = EvaMetadataJson(self.metadata_json_post_validation)
            try:
                vcf_analysis_dict = {}
                for file in metadata.resolved_files:
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
        return []

    def create_reports(self):
        is_consent_statement_needed = self._check_consent_statement_is_needed_for_submission()

        report_html = generate_html_report(self.results, self.validation_date, self.submission_dir,
                                           self.get_vcf_fasta_analysis_mapping(),
                                           self.project_title, is_consent_statement_needed)
        html_path = os.path.join(self.output_dir, 'report.html')
        with open(html_path, "w") as f:
            f.write(report_html)

        report_text = generate_text_report(self.results, self.validation_date, self.submission_dir,
                                           self.get_vcf_fasta_analysis_mapping(),
                                           self.project_title, is_consent_statement_needed)
        text_path = os.path.join(self.output_dir, 'report.txt')
        with open(text_path, "w") as f:
            f.write(report_text)

        self.info(f'Validation result: {"SUCCESS" if self.verify_ready_for_submission_to_eva() else "FAILURE"}')
        self.info(f'View the full report in your browser: {html_path}')
        self.info(f'Or view a text version: {text_path}')
        return html_path, text_path

    def _check_consent_statement_is_needed_for_submission(self):
        if self.metadata_json_post_validation:
            metadata = EvaMetadataJson(self.metadata_json_post_validation)
            return metadata.project.get('taxId') == 9606 and any(
                v['evidence_type'] == 'genotype'
                for k, v in self.results[EVIDENCE_TYPE_CHECK].items()
                if isinstance(v, dict) and 'evidence_type' in v
            )

        return False
