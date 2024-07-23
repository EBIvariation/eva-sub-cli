import os.path
from unittest import TestCase

from eva_sub_cli.validators.validator import Validator, VALIDATION_OUTPUT_DIR
from tests.test_utils import create_mapping_file


class TestValidator(TestCase):
    resource_dir = os.path.join(os.path.dirname(__file__), 'resources')
    vcf_files = os.path.join(resource_dir, 'vcf_files')
    fasta_files = os.path.join(resource_dir, 'fasta_files')
    assembly_reports = os.path.join(resource_dir, 'assembly_reports')
    output_dir = os.path.join(resource_dir, 'validation_reports')
    mapping_file = os.path.join(output_dir, 'vcf_files_mapping.csv')
    metadata_xlsx_file = os.path.join(output_dir, 'EVA_Submission_test.xlsx')

    def setUp(self) -> None:
        # create vcf mapping file
        os.makedirs(self.output_dir, exist_ok=True)
        create_mapping_file(self.mapping_file,
                            [os.path.join(self.vcf_files, 'input_passed.vcf')],
                            [os.path.join(self.fasta_files, 'input_passed.fa')],
                            [os.path.join(self.assembly_reports, 'input_passed.txt')])
        self.validator = Validator(self.mapping_file, self.output_dir, metadata_xlsx=self.metadata_xlsx_file)
        self.validator_json = Validator(self.mapping_file, self.output_dir)

    def tearDown(self) -> None:
        files_from_tests = [
            self.mapping_file,
            os.path.join(self.output_dir, VALIDATION_OUTPUT_DIR, 'other_validations', 'metadata_spreadsheet_validation.txt'),
            os.path.join(self.output_dir, VALIDATION_OUTPUT_DIR, 'report.html')
        ]
        for f in files_from_tests:
            if os.path.exists(f):
                os.remove(f)

    def test__collect_validation_workflow_results_with_metadata_xlsx(self):
        expected_results = {
            'vcf_check': {
                'input_passed.vcf': {'valid': True, 'error_list': [], 'error_count': 0, 'warning_count': 0, 'critical_count': 0, 'critical_list': []}
            },
            'assembly_check': {
                'input_passed.vcf': {'error_list': [], 'mismatch_list': [], 'nb_mismatch': 0, 'nb_error': 0, 'match': 247, 'total': 247}
            },
            'sample_check': {
                'overall_differences': False,
                'results_per_analysis': {
                    'AA': {
                        'difference': False,
                        'more_metadata_submitted_files': [],
                        'more_per_submitted_files_metadata': {},
                        'more_submitted_files_metadata': []
                    }
                }
            },
            'fasta_check': {
                'input_passed.fa': {'all_insdc': False, 'sequences': [
                    {'sequence_name': 1, 'insdc': True, 'sequence_md5': '6681ac2f62509cfc220d78751b8dc524'},
                    {'sequence_name': 2, 'insdc': False, 'sequence_md5': 'd2b3f22704d944f92a6bc45b6603ea2d'}
                ]},
            },
            'metadata_check': {
                'json_errors': [
                    {'property': '/files', 'description': "should have required property 'files'"},
                    {'property': '/project/title', 'description': "should have required property 'title'"},
                    {'property': '/project/taxId', 'description': "must have required property 'taxId'"},
                    {'property': '/project/holdDate', 'description': 'must match format "date"'},
                    {'property': '/analysis/0/description', 'description': "should have required property 'description'"},
                    {'property': '/analysis/0/referenceGenome', 'description': "should have required property 'referenceGenome'"},
                    {'property': '/sample/0/bioSampleAccession', 'description': "should have required property 'bioSampleAccession'"},
                    {'property': '/sample/0/bioSampleObject', 'description': "should have required property 'bioSampleObject'"},
                    {'property': '/sample/0', 'description': 'should match exactly one schema in oneOf'},
                    {'property': '/project/childProjects/1', 'description': 'PRJEBNA does not exist or is private'},
                    {'property': '/sample/2/bioSampleObject/characteristics/taxId',
                     'description': '1234 is not a valid taxonomy code'},
                    {'property': '/sample/analysisAlias', 'description': 'alias1 present in Analysis not in Samples'},
                    {'property': '/sample/analysisAlias',
                     'description': 'alias_1,alias_2 present in Samples not in Analysis'},
                ],
                'spreadsheet_errors': [
                    # NB. Wouldn't normally get conversion error + validation errors together, but it is supported.
                    {'sheet': 'Project', 'row': '', 'column': 'Tax ID',
                     'description': 'Worksheet Project is missing required header Tax ID'},
                    {'sheet': 'Files', 'row': '', 'column': '', 'description': 'Sheet "Files" is missing'},
                    {'sheet': 'Project', 'row': '', 'column': 'Project Title',
                     'description': 'In sheet "Project", column "Project Title" is not populated'},
                    {'sheet': 'Project', 'row': '', 'column': 'Tax ID',
                     'description': 'In sheet "Project", column "Tax ID" is not populated'},
                    {'sheet': 'Project', 'row': '', 'column': 'Hold Date',
                     'description': 'must match format "date"'},
                    {'sheet': 'Analysis', 'row': 2, 'column': 'Description',
                     'description': 'In sheet "Analysis", row "2", column "Description" is not populated'},
                    {'sheet': 'Analysis', 'row': 2, 'column': 'Reference',
                     'description': 'In sheet "Analysis", row "2", column "Reference" is not populated'},
                    {'sheet': 'Sample', 'row': 3, 'column': 'Sample Accession',
                     'description': 'In sheet "Sample", row "3", column "Sample Accession" is not populated'},
                    {'sheet': 'Project', 'row': '', 'column': 'Child Project(s)',
                     'description': 'PRJEBNA does not exist or is private'},
                    {'sheet': 'Sample', 'row': 5, 'column': 'Tax Id',
                     'description': '1234 is not a valid taxonomy code'},
                    {'sheet': 'Sample', 'row': '', 'column': 'Analysis Alias',
                     'description': 'alias1 present in Analysis not in Samples'},
                    {'sheet': 'Sample', 'row': '', 'column': 'Analysis Alias',
                     'description': 'alias_1,alias_2 present in Samples not in Analysis'}
                ]
            }
        }

        self.validator._collect_validation_workflow_results()
        # Drop report paths from comparison (test will fail if missing)
        del self.validator.results['metadata_check']['json_report_path']
        del self.validator.results['metadata_check']['spreadsheet_report_path']
        del self.validator.results['sample_check']['report_path']
        for file in self.validator.results['vcf_check'].values():
            del file['report_path']
        for file in self.validator.results['assembly_check'].values():
            del file['report_path']

        assert self.validator.results == expected_results

    def test__collect_validation_workflow_results_with_metadata_json(self):
        expected_results = {
            'vcf_check': {
                'input_passed.vcf': {'valid': True, 'error_list': [], 'error_count': 0, 'warning_count': 0,
                                     'critical_count': 0, 'critical_list': []}
            },
            'assembly_check': {
                'input_passed.vcf': {'error_list': [], 'mismatch_list': [], 'nb_mismatch': 0, 'nb_error': 0,
                                     'match': 247, 'total': 247}
            },
            'sample_check': {
                'overall_differences': False,
                'results_per_analysis': {
                    'AA': {
                        'difference': False,
                        'more_metadata_submitted_files': [],
                        'more_per_submitted_files_metadata': {},
                        'more_submitted_files_metadata': []
                    }
                }
            },
            'fasta_check': {
                'input_passed.fa': {'all_insdc': False, 'sequences': [
                    {'sequence_name': 1, 'insdc': True, 'sequence_md5': '6681ac2f62509cfc220d78751b8dc524'},
                    {'sequence_name': 2, 'insdc': False, 'sequence_md5': 'd2b3f22704d944f92a6bc45b6603ea2d'}
                ]},
            },
            'metadata_check': {
                'json_errors': [
                    {'property': '/files', 'description': "should have required property 'files'"},
                    {'property': '/project/title', 'description': "should have required property 'title'"},
                    {'property': '/project/taxId', 'description': "must have required property 'taxId'"},
                    {'property': '/project/holdDate', 'description': 'must match format "date"'},
                    {'property': '/analysis/0/description',
                     'description': "should have required property 'description'"},
                    {'property': '/analysis/0/referenceGenome',
                     'description': "should have required property 'referenceGenome'"},
                    {'property': '/sample/0/bioSampleAccession',
                     'description': "should have required property 'bioSampleAccession'"},
                    {'property': '/sample/0/bioSampleObject',
                     'description': "should have required property 'bioSampleObject'"},
                    {'property': '/sample/0', 'description': 'should match exactly one schema in oneOf'},
                    {'property': '/project/childProjects/1', 'description': 'PRJEBNA does not exist or is private'},
                    {'property': '/sample/2/bioSampleObject/characteristics/taxId',
                     'description': '1234 is not a valid taxonomy code'},
                    {'property': '/sample/analysisAlias', 'description': 'alias1 present in Analysis not in Samples'},
                    {'property': '/sample/analysisAlias',
                     'description': 'alias_1,alias_2 present in Samples not in Analysis'},
                ],
                'spreadsheet_errors': [
                    {'sheet': 'Project', 'row': '', 'column': 'Tax ID',
                     'description': 'Worksheet Project is missing required header Tax ID'}
                ]
            }
        }

        self.validator_json._collect_validation_workflow_results()
        # Drop report paths from comparison (test will fail if missing)
        del self.validator_json.results['metadata_check']['json_report_path']
        del self.validator_json.results['sample_check']['report_path']
        for file in self.validator_json.results['vcf_check'].values():
            del file['report_path']
        for file in self.validator_json.results['assembly_check'].values():
            del file['report_path']

        assert self.validator_json.results == expected_results

    def test_create_report(self):
        self.validator._collect_validation_workflow_results()
        report_path = self.validator.create_reports()
        assert os.path.exists(report_path)

    def test_vcf_check_errors_is_critical(self):
        errors = [
            'INFO AC does not match the specification Number=A (expected 1 value(s)). AC=100,37.',
            'Sample #10, field PL does not match the meta specification Number=G (expected 2 value(s)). PL=.. It must derive its number of values from the ploidy of GT (if present), or assume diploidy. Contains 1 value(s), expected 2 (derived from ploidy 1).',
            'Sample #102, field AD does not match the meta specification Number=R (expected 3 value(s)). AD=..'
        ]
        expected_return = [False, True, True]
        for i, error in enumerate(errors):
            assert self.validator.vcf_check_errors_is_critical(error) == expected_return[i]

    def test_parse_biovalidator_validation_results(self):
        self.validator.results['metadata_check'] = {}
        self.validator._parse_biovalidator_validation_results()
        assert self.validator.results['metadata_check']['json_errors'] == [
            {'property': '/files', 'description': "should have required property 'files'"},
            {'property': '/project/title', 'description': "should have required property 'title'"},
            {'property': '/project/taxId', 'description': "must have required property 'taxId'"},
            {'property': '/project/holdDate', 'description': 'must match format "date"'},
            {'property': '/analysis/0/description', 'description': "should have required property 'description'"},
            {'property': '/analysis/0/referenceGenome', 'description': "should have required property 'referenceGenome'"},
            {'property': '/sample/0/bioSampleAccession', 'description': "should have required property 'bioSampleAccession'"},
            {'property': '/sample/0/bioSampleObject', 'description': "should have required property 'bioSampleObject'"},
            {'property': '/sample/0', 'description': 'should match exactly one schema in oneOf'}
        ]

    def test_convert_biovalidator_validation_to_spreadsheet(self):
        self.validator.results['metadata_check'] = {
            'json_errors': [
                {'property': '/files', 'description': "should have required property 'files'"},
                {'property': '/project/title', 'description': "should have required property 'title'"},
                {'property': '/project/taxId', 'description': "must have required property 'taxId'"},
                {'property': '/project/holdDate', 'description': 'must match format "date"'},
                {'property': '/analysis/0/description',
                 'description': "should have required property 'description'"},
                {'property': '/analysis/0/referenceGenome',
                 'description': "should have required property 'referenceGenome'"},
                {'property': '/sample/0/bioSampleAccession',
                 'description': "should have required property 'bioSampleAccession'"},
                {'property': '/sample/0/bioSampleObject',
                 'description': "should have required property 'bioSampleObject'"},
                {'property': '/sample/0', 'description': 'should match exactly one schema in oneOf'},
                # Semantic checks
                {'property': '/project/childProjects/1', 'description': 'PRJEBNA does not exist or is private'},
                {'property': '/sample/2/bioSampleObject/characteristics/taxId',
                 'description': '1234 is not a valid taxonomy code'},
                {'property': '/sample/analysisAlias', 'description': 'alias1 present in Analysis not in Samples'},
                {'property': '/sample/analysisAlias',
                 'description': 'alias_1,alias_2 present in Samples not in Analysis'}
            ]
        }
        self.validator._convert_biovalidator_validation_to_spreadsheet()

        assert self.validator.results['metadata_check']['spreadsheet_errors'] == [
            {'sheet': 'Files', 'row': '', 'column': '', 'description': 'Sheet "Files" is missing'},
            {'sheet': 'Project', 'row': '', 'column': 'Project Title',
             'description': 'In sheet "Project", column "Project Title" is not populated'},
            {'sheet': 'Project', 'row': '', 'column': 'Tax ID',
             'description': 'In sheet "Project", column "Tax ID" is not populated'},
            {'sheet': 'Project', 'row': '', 'column': 'Hold Date',
             'description': 'must match format "date"'},
            {'sheet': 'Analysis', 'row': 2, 'column': 'Description',
             'description': 'In sheet "Analysis", row "2", column "Description" is not populated'},
            {'sheet': 'Analysis', 'row': 2, 'column': 'Reference',
             'description': 'In sheet "Analysis", row "2", column "Reference" is not populated'},
            {'sheet': 'Sample', 'row': 3, 'column': 'Sample Accession',
             'description': 'In sheet "Sample", row "3", column "Sample Accession" is not populated'},
            {'sheet': 'Project', 'row': '', 'column': 'Child Project(s)',
             'description': 'PRJEBNA does not exist or is private'},
            {'sheet': 'Sample', 'row': 5, 'column': 'Tax Id', 'description': '1234 is not a valid taxonomy code'},
            {'sheet': 'Sample', 'row': '', 'column': 'Analysis Alias',
             'description': 'alias1 present in Analysis not in Samples'},
            {'sheet': 'Sample', 'row': '', 'column': 'Analysis Alias',
             'description': 'alias_1,alias_2 present in Samples not in Analysis'}
        ]

    def test_parse_assembly_check_log(self):
        assembly_check_log = os.path.join(self.resource_dir, 'assembly_check', 'invalid.vcf.assembly_check.log')
        error_list, nb_error, match, total = self.validator.parse_assembly_check_log(assembly_check_log)
        assert error_list == ["The assembly checking could not be completed: Contig 'chr23' not found in assembly report"]

    def test_parse_assembly_check_report(self):
        assembly_check_report = os.path.join(self.resource_dir, 'assembly_check', 'invalid.vcf.text_assembly_report.txt')
        mismatch_list, nb_mismatch, error_list, nb_error = self.validator.parse_assembly_check_report(assembly_check_report)
        assert mismatch_list[0] == "Line 43: Chromosome chr1, position 955679, reference allele 'T' does not match the reference sequence, expected 'C'"
        assert nb_mismatch == 12
        assert error_list == []
        assert nb_error == 0

    def test_collect_conversion_errors(self):
        self.validator.results['metadata_check'] = {}
        self.validator._load_spreadsheet_conversion_errors()
        assert self.validator.results['metadata_check']['spreadsheet_errors'] == [{
                'column': 'Tax ID',
                'description': 'Worksheet Project is missing required header Tax ID',
                'row': '',
                'sheet': 'Project'
            }]
