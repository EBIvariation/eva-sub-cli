
from unittest import TestCase
from eva_sub_cli.executables import format_metadata


class TestValidateMetadata(TestCase):

    def test_format_experiment_type_lowercase(self):
        clean_json = {
            "submitterDetails": [{"lastName": "", "firstName": "", "email": "", "laboratory": "", "centre": ""}],
            "project": {"title": "", "description": "", "taxId": 9606, "centre": ""},
            "analysis": [{"analysisTitle": "", "analysisAlias": "", "description": "",
                    # CHANGING THE LINE BELOW
                    "experimentType": "genotyping_by_array",
                    "referenceGenome": ""}],
            "sample": [{"analysisAlias": [""], "sampleInVCF": "", "bioSampleObject": {"sample_title": "", "scientific_name": "", "tax_id": 9606, "collection date": "not provided", "geographic location (country and/or sea)": "not provided"}}],
            "files": [{"analysisAlias": "", "fileName": "", "fileSize": 1000, "md5": ""}]
        }
        validated_result = format_metadata.format_experiment_type_lowercase(clean_json)
        expected = clean_json
        self.assertEqual(validated_result, expected)

        unclean_json = {
            "submitterDetails": [{"lastName": "", "firstName": "", "email": "", "laboratory": "", "centre": ""}],
            "project": {"title": "", "description": "", "taxId": 9606, "centre": "",},
            "analysis": [{"analysisTitle": "", "analysisAlias": "", "description": "",
                    # CHANGING THE LINE BELOW
                    "experimentType": "Genotyping_by_array",
                    "referenceGenome": ""}],
            "sample": [{"analysisAlias": [""], "sampleInVCF": "", "bioSampleObject": {"sample_title": "", "scientific_name": "", "tax_id": 9606, "collection date": "not provided", "geographic location (country and/or sea)": "not provided"}}],
            "files": [{"analysisAlias": "", "fileName": "", "fileSize": 1000, "md5": ""}]
        }
        validated_result = format_metadata.format_experiment_type_lowercase(unclean_json)
        expected = clean_json
        self.assertEqual(validated_result, expected)