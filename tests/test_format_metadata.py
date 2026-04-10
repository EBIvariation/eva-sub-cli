
from unittest import TestCase
from eva_sub_cli.executables import format_metadata
import tempfile
import json

class TestValidateMetadata(TestCase):

    def test_format_experiment_type_lowercase(self):
        clean_json =  {
            "submitterDetails": [{"lastName": "", "firstName": "", "email": "", "laboratory": "", "centre": ""}],
            "project": {"title": "", "description": "", "taxId": 9606, "centre": ""},
            "analysis": [{"analysisTitle": "", "analysisAlias": "", "description": "",
                    # CHANGING THE LINE BELOW
                    "experimentType": "genotyping_by_array",
                    "referenceGenome": ""}],
            "sample": [{"analysisAlias": [""], "sampleInVCF": "", "bioSampleObject": {"sample_title": "", "scientific_name": "", "tax_id": 9606, "collection date": "not provided", "geographic location (country and/or sea)": "not provided"}}],
            "files": [{"analysisAlias": "", "fileName": "", "fileSize": 1000, "md5": ""}]
        }
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_out_clean:
            temp_path_clean_output = tmp_out_clean.name
            tmp_out_clean.write('')
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
            json.dump(clean_json, tmp)
            temp_path_clean = tmp.name
        format_metadata.format_experiment_type_lowercase(temp_path_clean, temp_path_clean_output)
        with open(temp_path_clean_output, 'r') as f:
            result_data = json.load(f)
        expected = clean_json
        self.assertEqual(result_data, expected)

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
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_out_unclean:
            temp_path_unclean_output = tmp_out_unclean.name
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
            json.dump(unclean_json, tmp)
            temp_path_unclean = tmp.name
        format_metadata.format_experiment_type_lowercase(temp_path_unclean, temp_path_unclean_output)
        with open(temp_path_unclean_output, 'r') as f:
            result_data = json.load(f)
        expected = unclean_json
        self.assertNotEqual(result_data, expected)