import json
import os
from datetime import datetime
from unittest import TestCase

import jsonschema
import yaml

from eva_sub_cli import ETC_DIR
from eva_sub_cli.executables.xlsx2json import XlsxParser, create_xls_template_from_yaml


class TestXlsReader(TestCase):
    resource_dir = os.path.join(os.path.dirname(__file__), 'resources')
    conf_filename = os.path.join(ETC_DIR, 'spreadsheet2json_conf.yaml')
    conf_filename_v2 = os.path.join(ETC_DIR, 'spreadsheet2json_conf_V2.yaml')
    eva_schema = os.path.abspath(os.path.join(__file__, "../../eva_sub_cli/etc/eva_schema.json", ))

    def tearDown(self):
        files_from_tests = [
            os.path.join(self.resource_dir, 'EVA_Submission_test_output.json'),
            os.path.join(self.resource_dir, 'EVA_Submission_test_output_v2.json'),
            os.path.join(self.resource_dir, 'metadata_not_existing.xlsx'),
            os.path.join(self.resource_dir, 'EVA_Submission_test_errors.yml'),
            os.path.join(self.resource_dir, 'EVA_Submission_test_errors_v2.yml'),
            os.path.join(self.resource_dir, 'EVA_Submission_test_with_project_accession.yml'),
            os.path.join(self.resource_dir, 'EVA_Submission_test_with_project_accession_output.json')
        ]
        for f in files_from_tests:
            if os.path.exists(f):
                os.remove(f)

    def test_cast_value(self):
        # list
        assert XlsxParser.cast_value('1', 'list') == ['1']
        assert XlsxParser.cast_value('1, 2, 3, 4, ', 'list') == ['1', '2', '3', '4']
        # boolean
        assert XlsxParser.cast_value('None', 'boolean') == False
        assert XlsxParser.cast_value('1', 'boolean') == True
        assert XlsxParser.cast_value("'1'", 'boolean') == True
        assert XlsxParser.cast_value('', 'boolean') == False
        # date
        assert XlsxParser.cast_value(datetime(2025, 5, 27, 14, 44), 'date') == '2025-05-27'
        assert XlsxParser.cast_value('2025-05-27', 'date') == '2025-05-27'

    def test_conversion_2_json(self) -> None:
        xls_filename = os.path.join(self.resource_dir, 'EVA_Submission_test.xlsx')
        self.parser = XlsxParser(xls_filename, self.conf_filename)
        output_json = os.path.join(self.resource_dir, 'EVA_Submission_test_output.json')
        errors_yaml = os.path.join(self.resource_dir, 'EVA_Submission_test_errors.yml')
        self.parser.json(output_json)
        self.parser.save_errors(errors_yaml)

        # confirm no errors
        with open(errors_yaml) as open_file:
            errors_data = yaml.safe_load(open_file)
            assert errors_data == []

        with open(output_json) as open_file:
            json_data = json.load(open_file)
            # assert json file is created with expected data
            assert sorted(json_data.keys()) == ['$schema', 'analysis', 'files', 'project', 'sample', 'submitterDetails']
            json_data.pop('$schema', None)
            self.assertEqual(self.get_expected_json(), json_data)

        # assert json schema
        with open(self.eva_schema) as eva_schema_file:
            eva_json_schema = json.load(eva_schema_file)

        # assert created json file conform to eva_schema
        jsonschema.validate(json_data, eva_json_schema)


    def test_conversion_2_json_V2(self) -> None:
        xls_filename = os.path.join(self.resource_dir, 'EVA_Submission_test_V2.xlsx')
        self.parser = XlsxParser(xls_filename, self.conf_filename_v2)
        output_json = os.path.join(self.resource_dir, 'EVA_Submission_test_output_v2.json')
        errors_yaml = os.path.join(self.resource_dir, 'EVA_Submission_test_errors_v2.yml')
        self.parser.json(output_json)
        self.parser.save_errors(errors_yaml)

        # confirm no errors
        with open(errors_yaml) as open_file:
            errors_data = yaml.safe_load(open_file)
            assert errors_data == []

        with open(output_json) as open_file:
            json_data = json.load(open_file)
            # assert json file is created with expected data
            assert sorted(json_data.keys()) == ['$schema', 'analysis', 'files', 'project', 'sample', 'submitterDetails']
            json_data.pop('$schema', None)
            self.assertEqual(self.get_expected_json(), json_data)

        # assert json schema
        with open(self.eva_schema) as eva_schema_file:
            eva_json_schema = json.load(eva_schema_file)

        jsonschema.validate(json_data, eva_json_schema)

    def test_conversion_2_json_with_project_accession(self) -> None:
        xls_filename = os.path.join(self.resource_dir, 'EVA_Submission_test_with_project_accession.xlsx')
        self.parser = XlsxParser(xls_filename, self.conf_filename)
        output_json = os.path.join(self.resource_dir, 'EVA_Submission_test_with_project_accession_output.json')
        errors_yaml = os.path.join(self.resource_dir, 'EVA_Submission_test_with_project_accession.yml')
        self.parser.json(output_json)
        self.parser.save_errors(errors_yaml)

        # confirm no errors
        with open(errors_yaml) as open_file:
            errors_data = yaml.safe_load(open_file)
            assert errors_data == []

        with open(output_json) as open_file:
            json_data = json.load(open_file)
            # assert json file is created with expected data
            assert sorted(json_data.keys()) == ['$schema', 'analysis', 'files', 'project', 'sample', 'submitterDetails']
            json_data.pop('$schema', None)
            # get expected json and remove other fields apart from project accession for comparison
            expected_json = self.get_expected_json()
            expected_json['project'] = {'projectAccession': 'PRJEB12345'}
            self.assertEqual(expected_json, json_data)

        # assert json schema
        with open(self.eva_schema) as eva_schema_file:
            eva_json_schema = json.load(eva_schema_file)

        jsonschema.validate(json_data, eva_json_schema)

    def test_create_xls_template(self):
        metadata_file = os.path.join(self.resource_dir, 'metadata_not_existing.xlsx')
        create_xls_template_from_yaml(metadata_file, self.conf_filename)
        assert os.path.exists(metadata_file)

    def test_json_conversion_succeeds_with_invalid_metadata(self):
        xls_filename = os.path.join(self.resource_dir, 'EVA_Submission_test_fails.xlsx')
        self.parser = XlsxParser(xls_filename, self.conf_filename)
        output_json = os.path.join(self.resource_dir, 'EVA_Submission_test_output.json')
        errors_yaml = os.path.join(self.resource_dir, 'EVA_Submission_test_errors.yml')
        self.parser.json(output_json)
        self.parser.save_errors(errors_yaml)

        # confirm no errors
        with open(errors_yaml) as open_file:
            errors_data = yaml.safe_load(open_file)
            assert errors_data == []

        # json file exists but missing fields
        assert os.path.exists(output_json)
        with open(output_json) as open_file:
            json_data = json.load(open_file)
            assert sorted(json_data.keys()) == ['$schema', 'analysis', 'files', 'project', 'sample', 'submitterDetails']
            # required field taxId is missing
            assert 'taxId' not in json_data['project']
            # novel sample is missing scientific name in characteristics and sample name
            novel_sample = json_data['sample'][3]['bioSampleObject']
            assert 'name' not in novel_sample
            assert 'species' not in novel_sample['characteristics']

    def test_json_validation_fails_for_large_project_title_and_project_description(self) -> None:
        with open(self.eva_schema) as eva_schema_file:
            eva_json_schema = json.load(eva_schema_file)

        # test fails for title
        json_data = self.get_expected_json()
        json_data['project']['title'] = self.build_large_string_of_length(600)

        assert len(json_data['project']['title']) == 600
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(json_data, eva_json_schema)

        # test fails for description
        json_data = self.get_expected_json()
        json_data['project']['description'] = self.build_large_string_of_length(6000)

        assert len(json_data['project']['description']) == 6000
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(json_data, eva_json_schema)

    def build_large_string_of_length(self, length):
        return "A" * length

    def get_expected_json(self):
        return {
            "submitterDetails": [
                {
                    "lastName": "Smith",
                    "firstName": "John",
                    "email": "john.smith@example.com",
                    "laboratory": "Genomics Lab",
                    "centre": "University of Example",
                    "address": "1 street address"
                },
                {
                    "lastName": "Doe",
                    "firstName": "Jane",
                    "email": "jane.doe@example.com",
                    "laboratory": "Bioinformatics Lab",
                    "centre": "University of Example",
                    "address": "1 street address"
                }
            ],
            "project": {
                "title": "Example Project",
                "description": "An example project for demonstration purposes",
                "centre": "University of Example",
                "taxId": 9606,
                "holdDate": "2023-12-31",
                'parentProject': 'PRJEB00001',
                'childProjects': ['PRJEB00002', 'PRJEB00003']
            },
            "analysis": [
                {
                    "analysisTitle": "Variant Detection 1",
                    "analysisAlias": "VD1",
                    "description": "An example analysis for demonstration purposes",
                    "experimentType": "Whole genome sequencing",
                    "referenceGenome": "GCA_000001405.27",
                    "referenceFasta": "GCA_000001405.27_fasta.fa",
                    "platform": "BGISEQ-500",
                    "imputation": True,
                },
                {
                    "analysisTitle": "Variant Detection 2",
                    "analysisAlias": "VD2",
                    "description": "An example analysis for demonstration purposes",
                    "experimentType": "Whole genome sequencing",
                    "referenceGenome": "GCA_000001405.27",
                    "referenceFasta": "GCA_000001405.27_fasta.fa",
                    "platform": "BGISEQ-500",
                    'phasing': True,
                },
                {
                    "analysisTitle": "Variant Detection 3",
                    "analysisAlias": "VD3",
                    "description": "An example analysis for demonstration purposes",
                    "experimentType": "Whole genome sequencing",
                    "referenceGenome": "GCA_000001405.27",
                    "referenceFasta": "GCA_000001405.27_fasta.fa",
                    "platform": "BGISEQ-500"
                }
            ],
            "sample": [
                {
                    "analysisAlias": ["VD1", "VD2", "VD3"],
                    "sampleInVCF": "sample1",
                    "bioSampleAccession": "SAME00001"
                },
                {
                    "analysisAlias": ["VD1", "VD2", "VD3"],
                    "sampleInVCF": "sample2",
                    "bioSampleAccession": "SAME00002"
                },
                {
                    "analysisAlias": ["VD3"],
                    "sampleInVCF": "sample3",
                    "bioSampleAccession": "SAME00003"
                },
                {
                    "analysisAlias": ["VD4", "VD5"],
                    "sampleInVCF": "sample4",
                    "bioSampleObject": {
                        "name": "Lm_17_S8",
                        "characteristics": {
                            "title": [
                                {"text": "Bastet normal sample"}
                            ],
                            "description": [
                                {"text": "Test Description"}
                            ],
                            "taxId": [
                                {"text": "9447"}
                            ],
                            "scientific name": [
                                {"text": "Lemur catta"}
                            ],
                            "sex": [
                                {"text": "Female"}
                            ],
                            "tissue_type": [
                                {"text": "skin"}
                            ],
                            "species": [
                                {"text": "Lemur catta"}
                            ],
                            'collection date': [
                                {'text': '2021-03-12'}
                            ],
                            'geographic location (country and/or sea)': [
                                {'text': 'Afghanistan'}
                            ]
                        }
                    }
                }
            ],
            "files": [
                {
                    "analysisAlias": "VD1",
                    "fileName": "example1.vcf.gz",
                },
                {
                    "analysisAlias": "VD2",
                    "fileName": "example2.vcf",
                },
                {
                    "analysisAlias": "VD3",
                    "fileName": "example3.vcf",
                }
            ]
        }
