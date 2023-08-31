#!/usr/bin/env python
import datetime
import glob
import os
import re

import yaml

from cli.report import generate_html_report


def resolve_single_file_path(file_path):
    files = glob.glob(file_path)
    if len(files) == 0:
        return None
    elif len(files) > 0:
        return files[0]


class Reporter:

    def __init__(self, vcf_files, output_dir):
        self.output_dir = output_dir
        self.vcf_files = vcf_files
        self.results = {}
        self.project_title = None  # TODO fill this from metadata?
        self.validation_date = datetime.datetime.now()

    def validate(self):
        self._validate()
        self._collect_validation_workflow_results()

    def _validate(self):
        raise NotImplementedError

    def parse_assembly_check_log(self, assembly_check_log):
        error_list = []
        nb_error, nb_mismatch = 0, 0
        match = total = None
        with open(assembly_check_log) as open_file:
            for line in open_file:
                if line.startswith('[error]'):
                    nb_error += 1
                    if nb_error < 11:
                        error_list.append(line.strip()[len('[error]'):])
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

    def _collect_validation_workflow_results(self, ):
        # Collect information from the output and summarise in the config
        self._collect_vcf_check_results()
        self._collect_assembly_check_results()
        self._load_sample_check_results()
        self._parse_metadata_validation_results()

    def _collect_vcf_check_results(self,):
        # detect output files for vcf check
        self.results['vcf_check'] = {}
        for vcf_file in self.vcf_files:
            vcf_name = os.path.basename(vcf_file)

            vcf_check_log = resolve_single_file_path(
                os.path.join(self.output_dir, 'vcf_format', vcf_name + '.vcf_format.log')
            )
            vcf_check_text_report = resolve_single_file_path(
                os.path.join(self.output_dir, 'vcf_format', vcf_name + '.*.txt')
            )
            vcf_check_db_report = resolve_single_file_path(
                os.path.join(self.output_dir, 'vcf_format', vcf_name + '.*.db')
            )

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

    def _collect_assembly_check_results(self):
        # detect output files for assembly check
        self.results['assembly_check'] = {}
        for vcf_file in self.vcf_files:
            vcf_name = os.path.basename(vcf_file)

            assembly_check_log = resolve_single_file_path(
                os.path.join(self.output_dir, 'assembly_check',  vcf_name + '.assembly_check.log')
            )
            assembly_check_valid_vcf = resolve_single_file_path(
                os.path.join(self.output_dir, 'assembly_check', vcf_name + '.valid_assembly_report*')
            )
            assembly_check_text_report = resolve_single_file_path(
                os.path.join(self.output_dir, 'assembly_check', vcf_name + '*text_assembly_report*')
            )

            if assembly_check_log and assembly_check_valid_vcf and assembly_check_text_report:
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

    def _load_sample_check_results(self):
        sample_check_yaml = resolve_single_file_path(os.path.join(self.output_dir, 'sample_checker.yml'))
        with open(sample_check_yaml) as open_yaml:
            self.results['sample_check'] = yaml.safe_load(open_yaml)
        self.results['sample_check']['report_path'] = sample_check_yaml

    def _parse_metadata_validation_results(self):
        """
        Read the biovalidator's report and extract the list of validation errors
        """
        metadata_check_file = resolve_single_file_path(os.path.join(self.output_dir, 'metadata_validation.txt'))
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

        def clean_read(ifile):
            l = ifile.readline()
            if l:
                return ansi_escape.sub('', l).strip()

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
        self.results['metadata_check'] = {
            'report_path': metadata_check_file,
            'json_errors': errors
        }

    def create_reports(self):
        report_html = generate_html_report(self.results, self.validation_date, self.project_title)
        file_path = 'report.html'
        with open(file_path, "w") as f:
            f.write(report_html)
        return file_path
