from unittest import TestCase
from unittest.mock import patch

from ebi_eva_common_pyutils.biosamples_communicators import NoAuthHALCommunicator

from eva_sub_cli.semantic_metadata import SemanticMetadataChecker

metadata = {
    "sample": [
        {"bioSampleAccession": "SAME00001"},
        {"bioSampleAccession": "SAME00002"},
        {"bioSampleAccession": "SAME00003"}
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
invalid_sample = {
    'accession': 'SAME00003',
    'name': 'sample3',
    'characteristics': {
        'organism': [{'text': 'Viridiplantae'}],
        'geographic location (country and/or sea)': [{'text': 'France: Montferrier-sur-Lez'}]
    }
}


class TestSemanticMetadata(TestCase):

    def test_check_all_project_accessions(self):
        metadata = {
            "project": {
                "parentProject": "PRJEB123",
                "childProjects": ["PRJEB456", "PRJEBNA"]
            },
        }
        checker = SemanticMetadataChecker(metadata)
        with patch('eva_sub_cli.semantic_metadata.download_xml_from_ena') as m_ena_download:
            m_ena_download.side_effect = [True, True, Exception('problem downloading')]
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
                          side_effect=[valid_sample, ValueError, invalid_sample]) as m_get_sample:
            checker.check_existing_biosamples()
            self.assertEqual(
                checker.errors[0],
                {'property': '/sample/1/bioSampleAccession', 'description': 'SAME00002 does not exist or is private'}
            )
            self.assertEqual(
                checker.errors[1],
                {'property': '/sample/2/bioSampleAccession',
                 'description': "Existing sample SAME00003 Just one of the following properties must be specified: 'collection_date', 'collection date', 'Event Date/Time'"}
            )
            # Final error message lists all possible geographic locations
            self.assertTrue(checker.errors[2]['description'].startswith(
                'Existing sample SAME00003 must be equal to one of the allowed values:'))

    def test_check_existing_biosamples(self):
        checker = SemanticMetadataChecker(metadata, sample_checklist=None)
        with patch.object(NoAuthHALCommunicator, 'follows_link',
                          side_effect=[valid_sample, ValueError, invalid_sample]) as m_follows_link:
            checker.check_existing_biosamples()
            self.assertEqual(checker.errors, [
                {
                    'property': '/sample/1/bioSampleAccession',
                    'description': 'SAME00002 does not exist or is private'
                },
                {
                    'property': '/sample/2/bioSampleAccession',
                    'description': 'Existing sample SAME00003 does not have a valid collection date'
                }
            ])

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
