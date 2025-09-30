from unittest import TestCase
from unittest.mock import patch
from requests import HTTPError, Response

import pytest
from ebi_eva_common_pyutils.biosamples_communicators import NoAuthHALCommunicator

from eva_sub_cli.semantic_metadata import SemanticMetadataChecker

metadata = {
    "sample": [
        {"bioSampleAccession": "SAME00001"},
        {"bioSampleAccession": "SAME00002"},
        {"bioSampleAccession": "SAME00003"},
        {"bioSampleAccession": "SAME00004"},
        {"bioSampleAccession": "SAME00005"},
        {"bioSampleAccession": "SAME00006"}
    ]
}
valid_sample = {
    'accession': 'SAME00001',
    'name': 'sample1',
    'characteristics': {
        'organism': [{'text': 'Viridiplantae'}],
        'collection date': [{'text': '2018'}],
        'geographic location (country and/or sea)': [{'text': 'France'}]
    }
}
invalid_sample1 = {
    'accession': 'SAME00003',
    'name': 'sample3',
    "create": "2023-10-10T08:45:15.310Z",
    'characteristics': {
        'organism': [{'text': 'Viridiplantae'}],
        'geographic location (country and/or sea)': [{'text': 'France: Montferrier-sur-Lez'}],
    }
}
invalid_sample2 = {
    'accession': 'SAME00004',
    'name': 'sample3',
    "create": "2023-10-10T08:45:15.310Z",
    'characteristics': {
        'organism': [{'text': 'Viridiplantae'}],
        'collection date': [{'text': 'November 2011'}]
    }
}
old_invalid_sample = {
    'accession': 'SAME00005',
    'name': 'sample4',
    "create": "2011-10-10T08:45:15.310Z",
    'characteristics': {
        'organism': [{'text': 'Viridiplantae'}]
    }
}

old_invalid_sample2 = {
    'accession': 'SAME00005',
    'name': 'sample4',
    "create": "2011-10-10T08:45:15Z",
    'characteristics': {
        'organism': [{'text': 'Viridiplantae'}]
    }
}


class TestSemanticMetadata(TestCase):

    def test_check_project_exists_and_public_in_ena_true(self):
        metadata = {
            "project": {
                "projectAccession": "PRJEB12345"
            }
        }
        checker = SemanticMetadataChecker(metadata)
        with patch('eva_sub_cli.semantic_metadata.download_xml_from_ena') as m_ena_download:
            m_ena_download.side_effect = [True, HTTPError('problem downloading', response=Response())]
            checker.check_all_project_accessions()
            self.assertEqual(checker.errors, [])

    def test_check_project_exists_and_public_in_ena_false(self):
        metadata = {
            "project": {
                "projectAccession": "PRJEBXYZ99"
            }
        }
        checker = SemanticMetadataChecker(metadata)
        with patch('eva_sub_cli.semantic_metadata.download_xml_from_ena') as m_ena_download:
            m_ena_download.side_effect = [HTTPError('problem downloading', response=Response())]
            checker.check_all_project_accessions()
            self.assertEqual(checker.errors, [
                {'property': '/project/projectAccession',
                 'description': 'Project PRJEBXYZ99 does not exist in ENA or is private'}
            ])

    def test_check_all_project_accessions(self):
        metadata = {
            "project": {
                "parentProject": "PRJEB123",
                "childProjects": ["PRJEB456", "PRJEBNA"]
            },
        }
        checker = SemanticMetadataChecker(metadata)
        with patch('eva_sub_cli.semantic_metadata.download_xml_from_ena') as m_ena_download:
            m_ena_download.side_effect = [True, True, HTTPError('problem downloading', response=Response())]
            checker.check_all_project_accessions()
            self.assertEqual(checker.errors, [
                {'property': '/project/childProjects/1', 'description': 'Project PRJEBNA does not exist in ENA or is private'}
            ])

    def test_check_all_taxonomy_codes(self):
        metadata = {
            "project": {
                "taxId": 9606,
            },
            "sample": [
                {
                    "bioSampleAccession": "SAME00003"
                },
                {
                    "bioSampleObject": {
                        "characteristics": {
                            "taxId": [{"text": "9606"}]
                        }
                    }
                },
                {
                    "bioSampleObject": {
                        "characteristics": {
                            "taxId": [{"text": "1234"}]
                        }
                    }
                }
            ]
        }
        checker = SemanticMetadataChecker(metadata)
        with patch('eva_sub_cli.semantic_metadata.get_scientific_name_and_common_name') as m_get_sci_name:
            # Mock should only be called once per taxonomy code
            m_get_sci_name.side_effect = [('Homo sapiens', 'human'), Exception('problem downloading')]
            checker.check_all_taxonomy_codes()
            self.assertEqual(checker.errors, [
                {
                    'property': '/sample/2/bioSampleObject/characteristics/taxId',
                    'description': '1234 is not a valid taxonomy code'
                }
            ])

    def test_check_uniqueness_analysis_alias(self):
        metadata = {
            "analysis": [
                {"analysisAlias": "alias1"},
                {"analysisAlias": "alias2"},
                {"analysisAlias": "alias1"}
            ]
        }
        checker = SemanticMetadataChecker(metadata)
        checker.check_uniqueness_analysis_alias()
        self.assertEqual(checker.errors, [
            {
                'property': '/analysis/0/analysisAlias',
                'description': 'Analysis alias alias1 is present 2 times in the Analysis Sheet'
            }, {
                'property': '/analysis/2/analysisAlias',
                'description': 'Analysis alias alias1 is present 2 times in the Analysis Sheet'
            }
        ]
)

    def test_check_all_scientific_names(self):
        metadata = {
            "sample": [
                {
                    "bioSampleObject": {
                        "characteristics": {
                            "taxId": [{"text": "9606"}],
                            "Organism": [{"text": "homo sapiens"}]
                        }
                    }
                },
                {
                    "bioSampleObject": {
                        "characteristics": {
                            "taxId": [{"text": "9606"}],
                            "Organism": [{"text": "sheep sapiens"}]
                        }
                    }
                },
                {
                    "bioSampleObject": {
                        "characteristics": {
                            "taxId": [{"text": "1234"}]
                        }
                    }
                }
            ]
        }
        checker = SemanticMetadataChecker(metadata)
        checker.taxonomy_valid = {
            1234: False,
            9606: "Homo sapiens"
        }
        checker.check_all_scientific_names()
        self.assertEqual(checker.errors, [
            {
                'property': '/sample/1/bioSampleObject/characteristics/Organism',
                'description': 'Species sheep sapiens does not match taxonomy 9606 (Homo sapiens)'
            }
        ])

    def test_check_existing_biosamples_with_checklist(self):
        checker = SemanticMetadataChecker(metadata)
        with patch.object(SemanticMetadataChecker, '_get_biosample',
                          side_effect=[valid_sample, ValueError, invalid_sample1, invalid_sample2, old_invalid_sample, old_invalid_sample2]) as m_get_sample:
            checker.check_existing_biosamples()
            self.assertEqual(
                checker.errors[0],
                {'property': '/sample/1/bioSampleAccession', 'description': 'SAME00002 does not exist or is private'}
            )
            self.assertEqual(
                checker.errors[1],
                {'property': '/sample/2/bioSampleAccession',
                 'description': "Error validating existing sample SAME00003: must have required property 'collection date'"}
            )
            # error message lists all possible geographic locations
            self.assertTrue(checker.errors[2]['description'].startswith(
                'Error validating existing sample SAME00003: geographic location (country and~1or sea) must be equal to one of the allowed values:'))

            self.assertEqual(checker.errors[3]['description'],
                "Error validating existing sample SAME00004: must have required property 'geographic location (country and/or sea)'")

            # error message lists long regex for collection date
            self.assertTrue(checker.errors[4]['description'].startswith(
                'Error validating existing sample SAME00004: collection date must match pattern '))
            self.assertTrue(len(checker.errors) == 5)

    def test_check_existing_biosamples(self):
        checker = SemanticMetadataChecker(metadata, sample_checklist=None)
        with patch.object(NoAuthHALCommunicator, 'follows_link',
                          side_effect=[valid_sample, ValueError, invalid_sample1, invalid_sample2, old_invalid_sample, old_invalid_sample2]) as m_follows_link:
            checker.check_existing_biosamples()
            self.assertEqual(checker.errors, [
                {'description': 'SAME00002 does not exist or is private','property': '/sample/1/bioSampleAccession'},
                {'description': 'Existing sample SAME00003 does not have a valid collection date', 'property': '/sample/2/bioSampleAccession'},
                {'description': 'Existing sample SAME00004 does not have a valid collection date', 'property': '/sample/3/bioSampleAccession'},
                {'description': 'Existing sample SAME00004 does not have a valid geographic location', 'property': '/sample/3/bioSampleAccession'}])

    @pytest.mark.skip(reason='Contact BioSample API')
    def test_check_existing_real_biosamples(self):
        metadata = {
            "sample": [
                {"bioSampleAccession": "SAMN01894452"}
            ]
        }
        checker = SemanticMetadataChecker(metadata, sample_checklist=None)
        checker.check_existing_biosamples()
        print(checker.errors)

    def test_check_analysis_alias_coherence(self):
        metadata = {
            "analysis": [
                {"analysisAlias": "alias1"},
                {"analysisAlias": "alias2"}
            ],
            "sample": [
                {
                    "bioSampleAccession": "SAME00003",
                    "analysisAlias": ["alias_1", "alias_2"]
                },
                {
                    "bioSampleAccession": "SAME00004",
                    "analysisAlias": ["alias2"]
                }
            ],
            "files": [
                {
                    "analysisAlias": "alias1",
                    "fileName": "example1.vcf.gz"
                },
                {
                    "analysisAlias": "alias2",
                    "fileName": "example2.vcf.gz"
                }
            ]
        }
        checker = SemanticMetadataChecker(metadata)
        checker.check_analysis_alias_coherence()
        self.assertEqual(checker.errors, [
            {'property': '/sample/analysisAlias', 'description': 'alias1 present in Analysis not in Samples'},
            {'property': '/sample/analysisAlias', 'description': 'alias_1,alias_2 present in Samples not in Analysis'}
        ])

    def test_check_all_analysis_run_accessions(self):
        metadata = {
            "analysis": [
                {'runAccessions': ['SRR000001', 'SRR000002']}
            ]
        }
        checker = SemanticMetadataChecker(metadata)
        checker.check_all_analysis_run_accessions()
        assert checker.errors == []

        metadata["analysis"].append({'runAccessions': ['SRR00000000001']})

        checker.check_all_analysis_run_accessions()
        assert checker.errors == [
            {'property': '/analysis/1/runAccessions', 'description': 'Run SRR00000000001 does not exist in ENA or is private'}]

    def test_check_all_analysis_contain_samples(self):
        # all analysis contain samples
        metadata = {
            "analysis": [
                {"analysisAlias": "A1"},
                {"analysisAlias": "A2"}
            ],
            "sample": [
                {"analysisAlias": ["A1"]},
                {"analysisAlias": ["A2"]}
            ]
        }

        checker = SemanticMetadataChecker(metadata)
        checker.check_all_analysis_contain_samples()
        assert checker.errors == []

        # analysis missing samples
        metadata = {
            "analysis": [
                {"analysisAlias": "A1"},
                {"analysisAlias": "A2"},
                {"analysisAlias": "A3"}
            ],
            "sample": [
                {"analysisAlias": ["A1"]}
            ]
        }

        checker = SemanticMetadataChecker(metadata)
        checker.check_all_analysis_contain_samples()
        self.assertEqual(len(checker.errors), 2)
        self.assertEqual(checker.errors[0]["property"], "/analysis/1")
        self.assertEqual(checker.errors[1]["property"], "/analysis/2")
        self.assertEqual(checker.errors[0]["description"],
                         "No sample found for the analysis. Should have at the least one sample.")

        # no samples in metadata
        metadata = {
            "analysis": [
                {"analysisAlias": "A1"}
            ],
            "sample": []
        }

        checker = SemanticMetadataChecker(metadata)
        checker.check_all_analysis_contain_samples()
        self.assertEqual(len(checker.errors), 1)
        self.assertEqual(checker.errors[0]["property"], "/analysis/0")
        self.assertEqual(checker.errors[0]["description"],
                         "No sample found for the analysis. Should have at the least one sample.")