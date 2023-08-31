import os.path
import shutil
from unittest import TestCase

from cli.reporter import Reporter


class TestReporter(TestCase):
    resource_dir = os.path.join(os.path.dirname(__file__), 'resources')

    def setUp(self) -> None:
        output_dir = os.path.join(self.resource_dir, 'validation_reports')
        self.reporter = Reporter(['input_passed.vcf'], output_dir)

    def tearDown(self) -> None:
        report_path = 'expected_report.html'
        if os.path.exists(report_path):
            shutil.rmtree(report_path)

    def test__collect_validation_workflow_results(self):
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
            'metadata_check': {
                'json_errors': [
                    {'property': '.files', 'description': "should have required property 'files'"},
                    {'property': '/project.title', 'description': "should have required property 'title'"},
                    {'property': '/analysis/0.description', 'description': "should have required property 'description'"},
                    {'property': '/analysis/0.referenceGenome', 'description': "should have required property 'referenceGenome'"},
                    {'property': '/sample/0.bioSampleAccession', 'description': "should have required property 'bioSampleAccession'"},
                    {'property': '/sample/0.bioSampleObject', 'description': "should have required property 'bioSampleObject'"},
                    {'property': '/sample/0', 'description': 'should match exactly one schema in oneOf'}
                ]
            }
        }
        self.reporter._collect_validation_workflow_results()

        # Drop report paths from comparison (test will fail if missing)
        del self.reporter.results['metadata_check']['report_path']
        del self.reporter.results['sample_check']['report_path']
        for file in self.reporter.results['vcf_check'].values():
            del file['report_path']
        for file in self.reporter.results['assembly_check'].values():
            del file['report_path']

        assert self.reporter.results == expected_results

    def test_create_report(self):
        self.reporter._collect_validation_workflow_results()
        report_path = self.reporter.create_reports()
        assert os.path.exists(report_path)

    def test_vcf_check_errors_is_critical(self):
        errors = [
            'INFO AC does not match the specification Number=A (expected 1 value(s)). AC=100,37.',
            'Sample #10, field PL does not match the meta specification Number=G (expected 2 value(s)). PL=.. It must derive its number of values from the ploidy of GT (if present), or assume diploidy. Contains 1 value(s), expected 2 (derived from ploidy 1).',
            'Sample #102, field AD does not match the meta specification Number=R (expected 3 value(s)). AD=..'
        ]
        expected_return = [False, True, True]
        for i, error in enumerate(errors):
            assert self.reporter.vcf_check_errors_is_critical(error) == expected_return[i]

    def test_parse_metadata_validation_results(self):
        self.reporter._parse_metadata_validation_results()
        assert self.reporter.results['metadata_check']['json_errors'] == [
            {'property': '.files', 'description': "should have required property 'files'"},
            {'property': '/project.title', 'description': "should have required property 'title'"},
            {'property': '/analysis/0.description', 'description': "should have required property 'description'"},
            {'property': '/analysis/0.referenceGenome', 'description': "should have required property 'referenceGenome'"},
            {'property': '/sample/0.bioSampleAccession', 'description': "should have required property 'bioSampleAccession'"},
            {'property': '/sample/0.bioSampleObject', 'description': "should have required property 'bioSampleObject'"},
            {'property': '/sample/0', 'description': 'should match exactly one schema in oneOf'}
        ]

