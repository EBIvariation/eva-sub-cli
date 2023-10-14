import json
import os
from unittest import TestCase

import jsonschema

from eva_sub_cli import ETC_DIR
from bin.xlsx2json import XlsxParser, create_xls_template_from_yaml


class TestXlsReader(TestCase):
    resource_dir = os.path.join(os.path.dirname(__file__), 'resources')
    conf_filename = os.path.join(ETC_DIR, 'spreadsheet2json_conf.yaml')
    eva_schema = os.path.abspath(os.path.join(__file__, "../../eva_sub_cli/etc/eva_schema.json", ))
    biosample_schema = os.path.abspath(os.path.join(__file__, "../../eva_sub_cli/etc/eva-biosamples.json", ))

    def test_conversion_2_json(self) -> None:
        xls_filename = os.path.join(self.resource_dir, 'EVA_Submission_template.V1.1.4.xlsx')
        self.parser = XlsxParser(xls_filename, self.conf_filename)
        output_json = os.path.join(self.resource_dir, 'EVA_Submission_template.V1.1.4.json')
        self.parser.json(output_json)

        with open(output_json) as open_file:
            json_data = json.load(open_file)
            # assert json file is created with expected data
            assert sorted(json_data.keys()) == ['analysis', 'files', 'project', 'sample', 'submitterDetails']
            self.assertTrue(self.get_expected_json() == json_data)

        # assert json schema
        with open(self.eva_schema) as eva_schema_file:
            eva_json_schema = json.load(eva_schema_file)
        with open(self.biosample_schema) as biosample_schema_file:
            biosample_json_schema = json.load(biosample_schema_file)

        # assert created json file sample field conforms to eva-biosamples schema
        jsonschema.validate(json_data['sample'][7]['bioSampleObject'], biosample_json_schema)

        # assert created json file conform to eva_schema
        resolver = jsonschema.RefResolver.from_schema(eva_json_schema)
        resolver.store['eva-biosamples.json'] = biosample_json_schema
        jsonschema.validate(json_data, eva_json_schema, resolver=resolver)

    def test_create_xls_template(self):
        metadata_file = os.path.join(self.resource_dir, 'metadata_not_existing.xlsx')
        create_xls_template_from_yaml(metadata_file, self.conf_filename)
        assert os.path.exists(metadata_file)

    def get_expected_json(self):
        return {
            "submitterDetails": [
                {
                    "lastName": "Smith",
                    "firstName": "John",
                    "telephone": "+1234567890",
                    "email": "john.smith@example.com",
                    "laboratory": "Genomics Lab",
                    "centre": "University of Example",
                    "address": "1 street address"
                },
                {
                    "lastName": "Doe",
                    "firstName": "Jane",
                    "telephone": "+1234567890",
                    "email": "jane.doe@example.com",
                    "laboratory": "Bioinformatics Lab",
                    "centre": "University of Example",
                    "address": "1 street address"
                }
            ],
            "project": {
                "title": "Example Project",
                "projectAlias": "EP",
                "description": "An example project for demonstration purposes",
                "centre": "University of Example",
                "taxId": 9606,
                "holdDate": "2023-12-31T00:00:00"
            },
            "analysis": [
                {
                    "analysisTitle": "Variant Detection 1",
                    "analysisAlias": "VD1",
                    "description": "An example analysis for demonstration purposes",
                    "ProjectTitle": "Example Project",
                    "experimentType": "Whole genome sequencing",
                    "referenceGenome": "GCA_000001405.27",
                    "platform": "BGISEQ-500"
                },
                {
                    "analysisTitle": "Variant Detection 2",
                    "analysisAlias": "VD2",
                    "description": "An example analysis for demonstration purposes",
                    "ProjectTitle": "Example Project",
                    "experimentType": "Whole genome sequencing",
                    "referenceGenome": "GCA_000001405.27",
                    "platform": "BGISEQ-500"
                },
                {
                    "analysisTitle": "Variant Detection 3",
                    "analysisAlias": "VD3",
                    "description": "An example analysis for demonstration purposes",
                    "ProjectTitle": "Example Project",
                    "experimentType": "Whole genome sequencing",
                    "referenceGenome": "GCA_000001405.27",
                    "platform": "BGISEQ-500"
                }
            ],
            "sample": [
                {
                    "analysisAlias": "VD1",
                    "sampleInVCF": "sample1",
                    "bioSampleAccession": "SAME00001"
                },
                {
                    "analysisAlias": "VD2",
                    "sampleInVCF": "sample1",
                    "bioSampleAccession": "SAME00001"
                },
                {
                    "analysisAlias": "VD3",
                    "sampleInVCF": "sample1",
                    "bioSampleAccession": "SAME00001"
                },
                {
                    "analysisAlias": "VD1",
                    "sampleInVCF": "sample2",
                    "bioSampleAccession": "SAME00002"
                },
                {
                    "analysisAlias": "VD2",
                    "sampleInVCF": "sample2",
                    "bioSampleAccession": "SAME00002"
                },
                {
                    "analysisAlias": "VD3",
                    "sampleInVCF": "sample2",
                    "bioSampleAccession": "SAME00002"
                },
                {
                    "analysisAlias": "VD3",
                    "sampleInVCF": "sample3",
                    "bioSampleAccession": "SAME00003"
                },
                {
                    "analysisAlias": "VD4",
                    "sampleInVCF": "sample4",
                    "bioSampleObject": {
                      "name": "Lm_17_S8",
                      "characteristics": {
                        "bioSampleName": "Lm_17_S8",
                        "title": [
                          "Bastet normal sample"
                        ],
                        "description": [
                          "Test Description"
                        ],
                        "taxId": [
                          9447
                        ],
                        "scientificName": [
                          "Lemur catta"
                        ],
                        "sex": "Female",
                        "tissueType": "skin",
                        "species": [
                          "Lemur catta"
                        ]
                      }
                    }
                 },
                {
                    "analysisAlias": "VD5",
                    "sampleInVCF": "sample4",
                    "bioSampleObject": {
                      "name": "Lm_17_S8",
                      "characteristics": {
                        "bioSampleName": "Lm_17_S8",
                        "title": [
                          "Bastet normal sample"
                        ],
                        "description": [
                          "Test Description"
                        ],
                        "taxId": [
                          9447
                        ],
                        "scientificName": [
                          "Lemur catta"
                        ],
                        "sex": "Female",
                        "tissueType": "skin",
                        "species": [
                          "Lemur catta"
                        ]
                      }
                    }
                }
            ],
            "files": [
                {
                    "analysisAlias": "VD1",
                    "fileName": "example1.vcf.gz",
                    "fileType": "vcf"
                },
                {
                    "analysisAlias": "VD2",
                    "fileName": "example2.vcf",
                    "fileType": "vcf"
                },
                {
                    "analysisAlias": "VD3",
                    "fileName": "example3.vcf",
                    "fileType": "vcf"
                }
            ]
        }
