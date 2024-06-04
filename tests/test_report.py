import os
import datetime
from unittest import TestCase

from eva_sub_cli.report import generate_html_report

validation_results = {
    "assembly_check": {
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
            "error_list": ["Sample #11, field AD does not match the meta specification Number=R (expected 2 value(s)). AD=.."],
            "valid": False,
            "warning_count": 0,
        },
    },
    "sample_check": {
        'report_path': '/path/to/sample/report',
        'overall_differences': True,
        'results_per_analysis': {
            'Analysis A': {
                'difference': True,
                'more_metadata_submitted_files': ['Sample1'],
                'more_per_submitted_files_metadata': {},
                'more_submitted_files_metadata': ['1Sample']
            }
        }
    },
    # NB. obviously this doesn't make sense for the number of analyses in this report, but demonstrates the possible
    # outputs for this check.
    "fasta_check": {
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
            'sequences': [
                {'sequence_name': '1', 'sequence_md5': 'hsjvchdhdo3ate83jdfd76rp2', 'insdc': True},
                {'sequence_name': '2', 'sequence_md5': 'hjfdoijsfc47hfg0gh9qwjrve', 'insdc': True}
            ],
            'possible_assemblies': {'GCA_1'},
            'error': '500 Server Error: Internal Server Error for url: https://www.ebi.ac.uk/eva/webservices/contig-alias/v1/chromosomes/md5checksum/hjfdoijsfc47hfg0gh9qwjrve'
        }
    },
    'metadata_check': {
        'json_errors': [
            {'property': '.files', 'description': "should have required property 'files'"},
            {'property': '/project.title', 'description': "should have required property 'title'"},
            {'property': '/project.description', 'description': "should have required property 'description'"},
            {'property': '/project.taxId', 'description': "should have required property 'taxId'"},
            {'property': '/project.centre', 'description': "should have required property 'centre'"},
            {'property': '/analysis/0.analysisTitle', 'description': "should have required property 'analysisTitle'"},
            {'property': '/analysis/0.description', 'description': "should have required property 'description'"},
            {'property': '/analysis/0.experimentType', 'description': "should have required property 'experimentType'"},
            {'property': '/analysis/0.referenceGenome', 'description': "should have required property 'referenceGenome'"},
            {'property': '/sample/0.bioSampleAccession', 'description': "should have required property 'bioSampleAccession'"},
            {'property': '/sample/0.bioSampleObject', 'description': "should have required property 'bioSampleObject'"},
            {'property': '/sample/0', 'description': 'should match exactly one schema in oneOf'}
        ],
        'json_report_path': '/path/to/metadata/report',
        'spreadsheet_errors': [
            {'sheet': 'Files', 'row': '', 'column': '', 'description': 'Sheet "Files" is missing'},
            {'sheet': 'Project', 'row': '', 'column': 'Project Title', 'description': 'In sheet "Project", column "Project Title" is not populated'},
            {'sheet': 'Project', 'row': '', 'column': 'Description', 'description': 'In sheet "Project", column "Description" is not populated'},
            {'sheet': 'Project', 'row': '', 'column': 'Tax ID', 'description': 'In sheet "Project", column "Tax ID" is not populated'},
            {'sheet': 'Project', 'row': '', 'column': 'Center', 'description': 'In sheet "Project", column "Center" is not populated'},
            {'sheet': 'Analysis', 'row': 2, 'column': 'Analysis Title', 'description': 'In sheet "Analysis", row "2", column "Analysis Title" is not populated'},
            {'sheet': 'Analysis', 'row': 2, 'column': 'Description', 'description': 'In sheet "Analysis", row "2", column "Description" is not populated'},
            {'sheet': 'Analysis', 'row': 2, 'column': 'Experiment Type', 'description': 'In sheet "Analysis", row "2", column "Experiment Type" is not populated'},
            {'sheet': 'Analysis', 'row': 2, 'column': 'Reference', 'description': 'In sheet "Analysis", row "2", column "Reference" is not populated'},
            {'sheet': 'Sample', 'row': 3, 'column': 'Sample Accession', 'description': 'In sheet "Sample", row "3", column "Sample Accession" is not populated'}
        ],
        'spreadsheet_report_path': '/path/to/metadata/metadata_spreadsheet_validation.txt',
    }
}


class TestReport(TestCase):
    resource_dir = os.path.join(os.path.dirname(__file__), 'resources')
    expected_report = os.path.join(resource_dir, 'validation_reports', 'expected_report.html')
    test_project_name = "My cool project"
    test_validation_date = datetime.datetime(2023, 8, 31, 12, 34, 56)
    test_submission_dir = "/test/submission/dir"
    test_vcf_fasta_analysis_mapping = []
    test_vcf_fasta_analysis_mapping.append({'vcf_file': 'input_fail.vcf', 'fasta_file': 'input_fail.fa', 'analysis': 'A'})
    test_vcf_fasta_analysis_mapping.append({'vcf_file': 'input_pass.vcf', 'fasta_file': 'input_pass.fa', 'analysis': 'B'})
    test_vcf_fasta_analysis_mapping.append({'vcf_file': 'input_test.vcf', 'fasta_file': 'input_test.fa', 'analysis': 'could not be linked'})
    def test_generate_html_report(self):
        report = generate_html_report(validation_results, self.test_validation_date, self.test_submission_dir,
                                      self.test_vcf_fasta_analysis_mapping, self.test_project_name)
        with open('report.html', 'w') as open_file:
            open_file.write(report)

        with open(self.expected_report) as open_html:
            assert report == open_html.read()

        # Remove output file if assert passes
        if os.path.exists('report.html'):
            os.remove('report.html')
