import copy
import datetime
import os
from unittest import TestCase

import eva_sub_cli
from eva_sub_cli.report import generate_html_report, generate_text_report
from eva_sub_cli.validators.validator import RUN_STATUS_KEY, TRIM_DOWN

validation_results_xlsx = {
    "ready_for_submission_to_eva": False,
    "version": "0.5.1",
    "trim_down": False,
    "assembly_check": {
        'run_status': True,
        'pass': False,
        "input_passed.vcf": {
            "report_path": "/path/to/assembly_passed/report",
            "error_list": [],
            "match": 247,
            "mismatch_list": [],
            "nb_error": 0,
            "nb_mismatch": 0,
            "total": 247,
        },
        "input_fail.vcf": {
            "report_path": "/path/to/assembly_failed/report",
            "error_list": ["The assembly checking could not be completed: Contig 'chr23' not found in assembly report"],
            "match": 26,
            "mismatch_list": [
                "Chromosome 1, position 35549, reference allele 'G' does not match the reference sequence, expected 'c'",
                "Chromosome 1, position 35595, reference allele 'G' does not match the reference sequence, expected 'a'",
                "Chromosome 1, position 35618, reference allele 'G' does not match the reference sequence, expected 'c'",
                "Chromosome 1, position 35626, reference allele 'A' does not match the reference sequence, expected 'g'",
                "Chromosome 1, position 35639, reference allele 'T' does not match the reference sequence, expected 'c'",
                "Chromosome 1, position 35643, reference allele 'T' does not match the reference sequence, expected 'g'",
                "Chromosome 1, position 35717, reference allele 'T' does not match the reference sequence, expected 'g'",
                "Chromosome 1, position 35819, reference allele 'T' does not match the reference sequence, expected 'a'",
                "Chromosome 1, position 35822, reference allele 'T' does not match the reference sequence, expected 'c'",
            ],
            "nb_error": 1,
            "nb_mismatch": 10,
            "total": 36,
        },
    },
    "vcf_check": {
        'run_status': True,
        'pass': False,
        "input_passed.vcf": {
            'report_path': '/path/to/vcf_passed/report',
            "error_count": 0,
            "error_list": [],
            "valid": True,
            "warning_count": 0,
        },
        "input_fail.vcf": {
            'report_path': '/path/to/vcf_failed/report',
            "critical_count": 1,
            "critical_list": ["Line 4: Error in meta-data section."],
            "error_count": 1,
            "error_list": [
                "Sample #11, field AD does not match the meta specification Number=R (expected 2 value(s)). AD=.."],
            "valid": False,
            "warning_count": 0,
        },
    },
    "sample_check": {
        'run_status': True,
        'pass': False,
        'report_path': '/path/to/sample/report',
        'overall_differences': True,
        'results_per_analysis': {
            'Analysis A': {
                'difference': True,
                'more_metadata_submitted_files': [' SampleA1', 'SampleA2 ', 'SampleA3', 'SampleA4', 'SampleA5',
                                                  'SampleA6', 'SampleA7', 'SampleA8', 'SampleA9', 'SampleA10'],
                'more_per_submitted_files_metadata': {},
                'more_submitted_files_metadata': ['A1Sample ', ' A2Sample', 'A3Sample', 'A4Sample', 'A5Sample',
                                                  'A6Sample', 'A7Sample', 'A8Sample', 'A9Sample', 'A10Sample']
            },
            'Analysis B': {
                'difference': False,
                'more_metadata_submitted_files': [],
                'more_per_submitted_files_metadata': {},
                'more_submitted_files_metadata': []
            },
            'Analysis C': {
                'difference': True,
                'more_metadata_submitted_files': ['SampleC1 ', ' SampleC2', 'SampleC3', 'SampleC4'],
                'more_per_submitted_files_metadata': {},
                'more_submitted_files_metadata': ['C1Sample ', ' C2Sample', 'C3Sample', 'C4Sample']
            }
        }
    },
    # NB. obviously this doesn't make sense for the number of analyses in this report, but demonstrates the possible
    # outputs for this check.
    "fasta_check": {
        'run_status': True,
        'pass': False,
        'not_all_insdc.fa': {
            'report_path': '/path/to/not_all_insdc_check.yml',
            'all_insdc': False,
            'sequences': [
                {'sequence_name': '1', 'sequence_md5': 'hsjvchdhdo3ate83jdfd76rp2', 'insdc': True},
                {'sequence_name': '2', 'sequence_md5': 'hjfdoijsfc47hfg0gh9qwjrve', 'insdc': False}
            ],
            'metadata_assembly_compatible': True,
            'possible_assemblies': {'GCA_1'},
            'assembly_in_metadata': 'GCA_1',
            'associated_analyses': ['Analysis A']
        },
        'metadata_asm_not_found.fa': {
            'report_path': '/path/to/metadata_asm_not_found.yml',
            'all_insdc': True,
            'sequences': [
                {'sequence_name': '1', 'sequence_md5': 'hsjvchdhdo3ate83jdfd76rp2', 'insdc': True},
                {'sequence_name': '2', 'sequence_md5': 'hjfdoijsfc47hfg0gh9qwjrve', 'insdc': True}
            ],
            'possible_assemblies': {'GCA_1'}
        },
        'metadata_asm_not_match.fa': {
            'report_path': '/path/to/metadata_asm_not_match.yml',
            'all_insdc': True,
            'sequences': [
                {'sequence_name': '1', 'sequence_md5': 'hsjvchdhdo3ate83jdfd76rp2', 'insdc': True},
                {'sequence_name': '2', 'sequence_md5': 'hjfdoijsfc47hfg0gh9qwjrve', 'insdc': True}
            ],
            'metadata_assembly_compatible': False,
            'possible_assemblies': {'GCA_1'},
            'assembly_in_metadata': 'GCA_2',
            'associated_analyses': ['Analysis B']
        },
        'metadata_asm_match.fa': {
            'report_path': '/path/to/metadata_asm_match.yml',
            'all_insdc': True,
            'sequences': [
                {'sequence_name': '1', 'sequence_md5': 'hsjvchdhdo3ate83jdfd76rp2', 'insdc': True},
                {'sequence_name': '2', 'sequence_md5': 'hjfdoijsfc47hfg0gh9qwjrve', 'insdc': True}
            ],
            'metadata_assembly_compatible': True,
            'possible_assemblies': {'GCA_1'},
            'assembly_in_metadata': 'GCA_1',
            'associated_analyses': ['Analysis A']
        },
        'metadata_error.fa': {
            'report_path': '/path/to/metadata_error.yml',
            'all_insdc': True,
            'sequences': [
                {'sequence_name': '1', 'sequence_md5': 'hsjvchdhdo3ate83jdfd76rp2', 'insdc': True},
                {'sequence_name': '2', 'sequence_md5': 'hjfdoijsfc47hfg0gh9qwjrve', 'insdc': True}
            ],
            'metadata_assembly_compatible': True,
            'possible_assemblies': {'GCA_1'},
            'assembly_in_metadata': 'GCA_1',
            'associated_analyses': ['Analysis C'],
            'connection_error': '500 Server Error: Internal Server Error for url: https://www.ebi.ac.uk/eva/webservices/contig-alias/v1/chromosomes/md5checksum/hjfdoijsfc47hfg0gh9qwjrve'
        }
    },
    'metadata_check': {
        'run_status': True,
        'pass': False,
        'spreadsheet_errors': [
            {'sheet': 'Files', 'row': '', 'column': '', 'description': 'Sheet "Files" is missing'},
            {'sheet': 'Project', 'row': 2, 'column': 'Project Title',
             'description': 'Column "Project Title" is not populated'},
            {'sheet': 'Project', 'row': 2, 'column': 'Description',
             'description': 'Column "Description" is not populated'},
            {'sheet': 'Project', 'row': 2, 'column': 'Tax ID', 'description': 'Column "Tax ID" is not populated'},
            {'sheet': 'Project', 'row': 2, 'column': 'Center', 'description': 'Column "Center" is not populated'},
            {'sheet': 'Analysis', 'row': 2, 'column': 'Analysis Title',
             'description': 'Column "Analysis Title" is not populated'},
            {'sheet': 'Analysis', 'row': 2, 'column': 'Description',
             'description': 'Column "Description" is not populated'},
            {'sheet': 'Analysis', 'row': 2, 'column': 'Experiment Type',
             'description': 'Column "Experiment Type" is not populated'},
            {'sheet': 'Analysis', 'row': 2, 'column': 'Reference',
             'description': 'Column "Reference" is not populated'},
            {'sheet': 'Sample', 'row': 3, 'column': 'Sample Accession',
             'description': 'Column "Sample Accession" is not populated'}
        ],
        'spreadsheet_report_path': '/path/to/metadata/metadata_spreadsheet_validation.txt',
    },

    'evidence_type_check': {
        'run_status': True,
        'pass': False,
        'report_path': '/path/to/evidence_type.yml',
        'Analysis A': {
            'evidence_type': None,
            'errors': 'VCF file evidence type could not be determined: vcf_files_1, vcf_files_2'
        },
        'Analysis B': {
            'evidence_type': None,
            'errors': 'Multiple evidence types found: genotype, allele_frequency'
        }
    }
}

validation_results_json = {
    "ready_for_submission_to_eva": False,
    "version": "0.5.1",
    "trim_down": False,
    "assembly_check": {
        'run_status': True,
        "input_passed.vcf": {
            "report_path": "/path/to/assembly_passed/report",
            "error_list": [],
            "match": 247,
            "mismatch_list": [],
            "nb_error": 0,
            "nb_mismatch": 0,
            "total": 247,
        },
        "input_fail.vcf": {
            "report_path": "/path/to/assembly_failed/report",
            "error_list": ["The assembly checking could not be completed: Contig 'chr23' not found in assembly report"],
            "match": 26,
            "mismatch_list": [
                "Chromosome 1, position 35549, reference allele 'G' does not match the reference sequence, expected 'c'",
                "Chromosome 1, position 35595, reference allele 'G' does not match the reference sequence, expected 'a'",
                "Chromosome 1, position 35618, reference allele 'G' does not match the reference sequence, expected 'c'",
                "Chromosome 1, position 35626, reference allele 'A' does not match the reference sequence, expected 'g'",
                "Chromosome 1, position 35639, reference allele 'T' does not match the reference sequence, expected 'c'",
                "Chromosome 1, position 35643, reference allele 'T' does not match the reference sequence, expected 'g'",
                "Chromosome 1, position 35717, reference allele 'T' does not match the reference sequence, expected 'g'",
                "Chromosome 1, position 35819, reference allele 'T' does not match the reference sequence, expected 'a'",
                "Chromosome 1, position 35822, reference allele 'T' does not match the reference sequence, expected 'c'",
            ],
            "nb_error": 1,
            "nb_mismatch": 10,
            "total": 36,
        },
        "pass": False,
    },
    "vcf_check": {
        'run_status': True,
        "input_passed.vcf": {
            'report_path': '/path/to/vcf_passed/report',
            "error_count": 0,
            "error_list": [],
            "valid": True,
            "warning_count": 0,
        },
        "input_fail.vcf": {
            'report_path': '/path/to/vcf_failed/report',
            "critical_count": 1,
            "critical_list": ["Line 4: Error in meta-data section."],
            "error_count": 1,
            "error_list": [
                "Sample #11, field AD does not match the meta specification Number=R (expected 2 value(s)). AD=.."],
            "valid": False,
            "warning_count": 0,
        },
        "pass": False,
    },
    "sample_check": {
        'run_status': True,
        'report_path': '/path/to/sample/report',
        'overall_differences': True,
        'results_per_analysis': {
            'Analysis A': {
                'difference': True,
                'more_metadata_submitted_files': [' SampleA1', 'SampleA2 ', 'SampleA3', 'SampleA4', 'SampleA5',
                                                  'SampleA6', 'SampleA7', 'SampleA8', 'SampleA9', 'SampleA10'],
                'more_per_submitted_files_metadata': {},
                'more_submitted_files_metadata': ['A1Sample ', ' A2Sample', 'A3Sample', 'A4Sample', 'A5Sample',
                                                  'A6Sample', 'A7Sample', 'A8Sample', 'A9Sample', 'A10Sample']
            },
            'Analysis B': {
                'difference': False,
                'more_metadata_submitted_files': [],
                'more_per_submitted_files_metadata': {},
                'more_submitted_files_metadata': []
            },
            'Analysis C': {
                'difference': True,
                'more_metadata_submitted_files': ['SampleC1 ', ' SampleC2', 'SampleC3', 'SampleC4'],
                'more_per_submitted_files_metadata': {},
                'more_submitted_files_metadata': ['C1Sample ', ' C2Sample', 'C3Sample', 'C4Sample']
            }
        },
        "pass": False,
    },
    # NB. obviously this doesn't make sense for the number of analyses in this report, but demonstrates the possible
    # outputs for this check.
    "fasta_check": {
        'run_status': True,
        "pass": False,
        'not_all_insdc.fa': {
            'report_path': '/path/to/not_all_insdc_check.yml',
            'all_insdc': False,
            'sequences': [
                {'sequence_name': '1', 'sequence_md5': 'hsjvchdhdo3ate83jdfd76rp2', 'insdc': True},
                {'sequence_name': '2', 'sequence_md5': 'hjfdoijsfc47hfg0gh9qwjrve', 'insdc': False}
            ],
            'metadata_assembly_compatible': True,
            'possible_assemblies': {'GCA_1'},
            'assembly_in_metadata': 'GCA_1',
            'associated_analyses': ['Analysis A']
        },
        'metadata_asm_not_found.fa': {
            'report_path': '/path/to/metadata_asm_not_found.yml',
            'all_insdc': True,
            'sequences': [
                {'sequence_name': '1', 'sequence_md5': 'hsjvchdhdo3ate83jdfd76rp2', 'insdc': True},
                {'sequence_name': '2', 'sequence_md5': 'hjfdoijsfc47hfg0gh9qwjrve', 'insdc': True}
            ],
            'possible_assemblies': {'GCA_1'}
        },
        'metadata_asm_not_match.fa': {
            'report_path': '/path/to/metadata_asm_not_match.yml',
            'all_insdc': True,
            'sequences': [
                {'sequence_name': '1', 'sequence_md5': 'hsjvchdhdo3ate83jdfd76rp2', 'insdc': True},
                {'sequence_name': '2', 'sequence_md5': 'hjfdoijsfc47hfg0gh9qwjrve', 'insdc': True}
            ],
            'metadata_assembly_compatible': False,
            'possible_assemblies': {'GCA_1'},
            'assembly_in_metadata': 'GCA_2',
            'associated_analyses': ['Analysis B']
        },
        'metadata_asm_match.fa': {
            'report_path': '/path/to/metadata_asm_match.yml',
            'all_insdc': True,
            'sequences': [
                {'sequence_name': '1', 'sequence_md5': 'hsjvchdhdo3ate83jdfd76rp2', 'insdc': True},
                {'sequence_name': '2', 'sequence_md5': 'hjfdoijsfc47hfg0gh9qwjrve', 'insdc': True}
            ],
            'metadata_assembly_compatible': True,
            'possible_assemblies': {'GCA_1'},
            'assembly_in_metadata': 'GCA_1',
            'associated_analyses': ['Analysis A']
        },
        'metadata_error.fa': {
            'report_path': '/path/to/metadata_error.yml',
            'all_insdc': True,
            'sequences': [
                {'sequence_name': '1', 'sequence_md5': 'hsjvchdhdo3ate83jdfd76rp2', 'insdc': True},
                {'sequence_name': '2', 'sequence_md5': 'hjfdoijsfc47hfg0gh9qwjrve', 'insdc': True}
            ],
            'metadata_assembly_compatible': True,
            'possible_assemblies': {'GCA_1'},
            'assembly_in_metadata': 'GCA_1',
            'associated_analyses': ['Analysis C'],
            'connection_error': '500 Server Error: Internal Server Error for url: https://www.ebi.ac.uk/eva/webservices/contig-alias/v1/chromosomes/md5checksum/hjfdoijsfc47hfg0gh9qwjrve'
        }
    },
    'metadata_check': {
        'run_status': True,
        "pass": False,
        'json_errors': [
            {'property': '.files', 'description': "should have required property 'files'"},
            {'property': '/project.title', 'description': "should have required property 'title'"},
            {'property': '/project.description', 'description': "should have required property 'description'"},
            {'property': '/project.taxId', 'description': "should have required property 'taxId'"},
            {'property': '/project.centre', 'description': "should have required property 'centre'"},
            {'property': '/analysis/0.analysisTitle', 'description': "should have required property 'analysisTitle'"},
            {'property': '/analysis/0.description', 'description': "should have required property 'description'"},
            {'property': '/analysis/0.experimentType', 'description': "should have required property 'experimentType'"},
            {'property': '/analysis/0.referenceGenome',
             'description': "should have required property 'referenceGenome'"},
            {'property': '/sample/0.bioSampleAccession',
             'description': "should have required property 'bioSampleAccession'"},
            {'property': '/sample/0.bioSampleObject', 'description': "should have required property 'bioSampleObject'"},
            {'property': '/sample/0', 'description': 'should match exactly one schema in oneOf'}
        ],
        'json_report_path': '/path/to/json/metadata/report'
    },

    'evidence_type_check': {
        'run_status': True,
        'pass': False,
        'report_path': '/path/to/evidence_type.yml',
        'Analysis A': {
            'evidence_type': None,
            'errors': 'VCF file evidence type could not be determined: vcf_files_1, vcf_files_2'
        },
        'Analysis B': {
            'evidence_type': None,
            'errors': 'Multiple evidence types found: genotype, allele_frequency'
        },
    }
}


class TestReport(TestCase):
    resource_dir = os.path.join(os.path.dirname(__file__), 'resources')
    expected_report_metadata_xlsx = os.path.join(resource_dir, 'validation_reports',
                                                 'expected_report_metadata_xlsx.html')
    expected_report_metadata_json = os.path.join(resource_dir, 'validation_reports',
                                                 'expected_report_metadata_json.html')
    expected_report_metadata_json_process_not_run = os.path.join(resource_dir, 'validation_reports',
                                                                 'expected_report_metadata_json_process_not_run.html')
    expected_report_metadata_xlsx_shallow = os.path.join(resource_dir, 'validation_reports',
                                                         'expected_shallow_metadata_xlsx_report.html')
    expected_text_report_metadata_xlsx = os.path.join(resource_dir, 'validation_reports',
                                                      'expected_report_metadata_xlsx.txt')
    expected_text_report_metadata_json = os.path.join(resource_dir, 'validation_reports',
                                                      'expected_report_metadata_json.txt')
    expected_text_report_metadata_json_process_not_run = os.path.join(resource_dir, 'validation_reports',
                                                                      'expected_report_metadata_json_process_not_run.txt')
    expected_text_report_metadata_xlsx_shallow = os.path.join(resource_dir, 'validation_reports',
                                                              'expected_shallow_metadata_xlsx_report.txt')
    test_project_name = "My cool project"
    test_validation_date = datetime.datetime(2023, 8, 31, 12, 34, 56)
    test_submission_dir = "/test/submission/dir"
    test_vcf_fasta_analysis_mapping = []
    test_vcf_fasta_analysis_mapping.append(
        {'vcf_file': 'input_fail.vcf', 'fasta_file': 'input_fail.fa', 'analysis': 'A'})
    test_vcf_fasta_analysis_mapping.append(
        {'vcf_file': 'input_pass.vcf', 'fasta_file': 'input_pass.fa', 'analysis': 'B'})
    test_vcf_fasta_analysis_mapping.append(
        {'vcf_file': 'input_test.vcf', 'fasta_file': 'input_test.fa', 'analysis': 'could not be linked'})

    def check_report_vs_expected(self, validation_results, output_report, expected_report, html=True):
        if html:
            report = generate_html_report(validation_results, self.test_validation_date, self.test_submission_dir,
                                          self.test_vcf_fasta_analysis_mapping, self.test_project_name, True)
        else:
            report = generate_text_report(validation_results, self.test_validation_date, self.test_submission_dir,
                                          self.test_vcf_fasta_analysis_mapping, self.test_project_name, True)
        with open(output_report, 'w') as open_file:
            open_file.write(report)

        with open(expected_report) as open_expected_file:
            expected_report_text = open_expected_file.read()
            # Inject the version in the expected report
            expected_report_text = expected_report_text.replace('cligeneratedversion', eva_sub_cli.__version__)
            assert report == expected_report_text

        # Remove output file if assert passes
        if os.path.exists(output_report):
            os.remove(output_report)

    def test_generate_html_report_metadata_xlsx(self):
        self.check_report_vs_expected(
            validation_results_xlsx,
            'metadata_xlsx_report.html',
            self.expected_report_metadata_xlsx
        )

    def test_generate_html_report_metadata_json(self):
        self.check_report_vs_expected(
            validation_results_json,
            'metadata_json_report.html',
            self.expected_report_metadata_json
        )

    def test_generate_html_report_metadata_json_metadata_report_not_run_yet(self):
        validation_result = {
            'vcf_check': {RUN_STATUS_KEY: False},
            'evidence_type_check': {RUN_STATUS_KEY: False},
            'assembly_check': {RUN_STATUS_KEY: False},
            'fasta_check': {RUN_STATUS_KEY: False},
            'metadata_check': {RUN_STATUS_KEY: False},
            'sample_check': {RUN_STATUS_KEY: False}
        }

        self.check_report_vs_expected(
            validation_result,
            'metadata_json_report.html',
            self.expected_report_metadata_json_process_not_run
        )

    def test_generate_html_report_metadata_xlsx_shallow(self):
        shallow_validation_results_xlsx = copy.deepcopy(validation_results_xlsx)
        shallow_validation_results_xlsx[TRIM_DOWN] = True
        shallow_validation_results_xlsx['shallow_validation'] = {
            'metrics': {
                'input_fail.vcf': {'trim_down_vcf_record': 10000, 'number_sequence_found': 24,
                                   'trim_down_required': True},
                'input_passed.vcf': {'trim_down_vcf_record': 10000, 'number_sequence_found': 24,
                                     'trim_down_required': True}
            }}
        self.check_report_vs_expected(
            shallow_validation_results_xlsx,
            'shallow_metadata_xlsx_report.html',
            self.expected_report_metadata_xlsx_shallow
        )

    def test_generate_text_report_metadata_xlsx(self):
        self.check_report_vs_expected(
            validation_results_xlsx,
            'metadata_xlsx_report.txt',
            self.expected_text_report_metadata_xlsx,
            html=False
        )

    def test_generate_text_report_metadata_json(self):
        self.check_report_vs_expected(
            validation_results_json,
            'metadata_json_report.txt',
            self.expected_text_report_metadata_json,
            html=False
        )

    def test_generate_text_report_metadata_json_report_not_run(self):
        validation_result = {
            'vcf_check': {RUN_STATUS_KEY: False},
            'evidence_type_check': {RUN_STATUS_KEY: False},
            'assembly_check': {RUN_STATUS_KEY: False},
            'fasta_check': {RUN_STATUS_KEY: False},
            'metadata_check': {RUN_STATUS_KEY: False},
            'sample_check': {RUN_STATUS_KEY: False}
        }

        self.check_report_vs_expected(
            validation_result,
            'metadata_json_report.txt',
            self.expected_text_report_metadata_json_process_not_run,
            html=False
        )

    def test_generate_text_report_metadata_xlsx_shallow(self):
        shallow_validation_results_xlsx = copy.deepcopy(validation_results_xlsx)
        shallow_validation_results_xlsx[TRIM_DOWN] = True
        shallow_validation_results_xlsx['shallow_validation'] = {
            'metrics': {
                'input_fail.vcf': {'trim_down_vcf_record': 10000, 'number_sequence_found': 24,
                                   'trim_down_required': True},
                'input_passed.vcf': {'trim_down_vcf_record': 10000, 'number_sequence_found': 24,
                                     'trim_down_required': True}
            }}
        self.check_report_vs_expected(
            shallow_validation_results_xlsx,
            'shallow_metadata_xlsx_report.txt',
            self.expected_text_report_metadata_xlsx_shallow,
            html=False
        )
