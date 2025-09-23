import json
from collections import Counter
from copy import deepcopy
from datetime import datetime

import yaml
from ebi_eva_common_pyutils.biosamples_communicators import NoAuthHALCommunicator
from ebi_eva_common_pyutils.ena_utils import download_xml_from_ena, get_scientific_name_and_common_name
from ebi_eva_common_pyutils.logger import AppLogger
from requests import HTTPError
from retry import retry

from eva_sub_cli.date_utils import check_date

PROJECT_KEY = 'project'
ANALYSIS_KEY = 'analysis'
SAMPLE_KEY = 'sample'
FILES_KEY = 'files'
PROJECT_ACCESSION_KEY = 'projectAccession'
PARENT_PROJECT_KEY = 'parentProject'
CHILD_PROJECTS_KEY = 'childProjects'
PEER_PROJECTS_KEY = 'peerProjects'
BIOSAMPLE_OBJECT_KEY = 'bioSampleObject'
BIOSAMPLE_ACCESSION_KEY = 'bioSampleAccession'
CHARACTERISTICS_KEY = 'characteristics'
TAX_ID_KEY = 'taxId'
SCI_NAME_KEYS = ['species', 'Species', 'organism', 'Organism']
ANALYSIS_ALIAS_KEY = 'analysisAlias'
ANALYSIS_RUNS_KEY = 'runAccessions'

# Samples created before this date are not required to have collection date or geographic location
threshold_2023 = datetime(2023, 1, 1)


def cast_list(l, type_to_cast=str):
    for e in l:
        yield type_to_cast(e)


class SemanticMetadataChecker(AppLogger):

    def __init__(self, metadata, sample_checklist='ERC000011'):
        self.sample_checklist = sample_checklist
        self.metadata = metadata
        self.errors = []
        # Caches whether taxonomy code is valid or not, and maps to scientific name if valid
        self.taxonomy_valid = {}
        self.communicator = NoAuthHALCommunicator(bsd_url='https://www.ebi.ac.uk/biosamples')

    def write_result_yaml(self, output_path):
        with open(output_path, 'w') as open_yaml:
            yaml.safe_dump(data=self.errors, stream=open_yaml)

    def check_all(self):
        self.check_all_project_accessions()
        self.check_all_taxonomy_codes()
        self.check_all_scientific_names()
        self.check_existing_biosamples()
        self.check_all_analysis_run_accessions()
        self.check_analysis_alias_coherence()
        self.check_all_analysis_contain_samples()

    def check_all_project_accessions(self):
        """Check that ENA project accessions exist and are public."""
        project = self.metadata[PROJECT_KEY]
        if PROJECT_ACCESSION_KEY in project:
            self.check_project_accession(project[PROJECT_ACCESSION_KEY], f'/{PROJECT_KEY}/{PROJECT_ACCESSION_KEY}')
        if PARENT_PROJECT_KEY in project:
            self.check_project_accession(project[PARENT_PROJECT_KEY], f'/{PROJECT_KEY}/{PARENT_PROJECT_KEY}')
        for idx, accession in enumerate(project.get(CHILD_PROJECTS_KEY, [])):
            self.check_project_accession(accession, f'/{PROJECT_KEY}/{CHILD_PROJECTS_KEY}/{idx}')
        for idx, accession in enumerate(project.get(PEER_PROJECTS_KEY, [])):
            self.check_project_accession(accession, f'/{PROJECT_KEY}/{PEER_PROJECTS_KEY}/{idx}')

    def check_all_taxonomy_codes(self):
        """Check that taxonomy IDs are valid according to ENA."""
        project = self.metadata[PROJECT_KEY]
        if TAX_ID_KEY in project:
            self.check_taxonomy_code(project[TAX_ID_KEY], f'/{PROJECT_KEY}/{TAX_ID_KEY}')
        # Check sample taxonomies for novel samples
        for idx, sample in enumerate(self.metadata[SAMPLE_KEY]):
            if BIOSAMPLE_OBJECT_KEY in sample and TAX_ID_KEY in sample[BIOSAMPLE_OBJECT_KEY][CHARACTERISTICS_KEY]:
                self.check_taxonomy_code(sample[BIOSAMPLE_OBJECT_KEY][CHARACTERISTICS_KEY][TAX_ID_KEY][0]['text'],
                                         f'/{SAMPLE_KEY}/{idx}/{BIOSAMPLE_OBJECT_KEY}/{CHARACTERISTICS_KEY}/{TAX_ID_KEY}')

    def check_uniqueness_analysis_alias(self):
        analyses = self.metadata[ANALYSIS_KEY]
        analysis_aliases = [analysis.get(ANALYSIS_ALIAS_KEY) for analysis in analyses]
        if len(analysis_aliases) != len(set(analysis_aliases)):
            counter = Counter(analysis_aliases)
            for idx, analysis in enumerate(analyses):
                if counter[analysis.get(ANALYSIS_ALIAS_KEY)] > 1:
                    self.add_error(
                        f'/{ANALYSIS_KEY}/{idx}/{ANALYSIS_ALIAS_KEY}',
                        f'Analysis alias {analysis.get(ANALYSIS_ALIAS_KEY)} is present '
                        f'{counter[analysis.get(ANALYSIS_ALIAS_KEY)]} times in the Analysis Sheet')

    def check_all_scientific_names(self):
        """Check that all scientific names are consistent with taxonomy codes."""
        for idx, sample in enumerate(self.metadata[SAMPLE_KEY]):
            if BIOSAMPLE_OBJECT_KEY in sample and TAX_ID_KEY in sample[BIOSAMPLE_OBJECT_KEY][CHARACTERISTICS_KEY]:
                characteristics = sample[BIOSAMPLE_OBJECT_KEY][CHARACTERISTICS_KEY]
                # Get the scientific name from the taxonomy (if valid)
                tax_code = int(characteristics[TAX_ID_KEY][0]['text'])
                sci_name_from_tax = self.taxonomy_valid[tax_code]
                if not sci_name_from_tax:
                    continue
                # Check if scientific name in sample matches
                for sci_name_key in SCI_NAME_KEYS:
                    if sci_name_key in characteristics:
                        sci_name = characteristics[sci_name_key][0]['text']
                        if sci_name_from_tax.lower() != sci_name.lower():
                            self.add_error(
                                f'/{SAMPLE_KEY}/{idx}/{BIOSAMPLE_OBJECT_KEY}/{CHARACTERISTICS_KEY}/{sci_name_key}',
                                f'Species {sci_name} does not match taxonomy {tax_code} ({sci_name_from_tax})')

    def check_all_analysis_run_accessions(self):
        """Check that the Run accession are valid and exist in ENA"""
        for idx, analysis in enumerate(self.metadata[ANALYSIS_KEY]):
            json_path = f'/{ANALYSIS_KEY}/{idx}/{ANALYSIS_RUNS_KEY}'
            if ANALYSIS_RUNS_KEY in analysis and analysis[ANALYSIS_RUNS_KEY]:
                for run_acc in analysis[ANALYSIS_RUNS_KEY]:
                    self.check_accession_in_ena(run_acc, 'Run', json_path)

    @retry(tries=4, delay=2, backoff=1.2, jitter=(1, 3))
    def check_accession_in_ena(self, ena_accession, accession_type, json_path):
        try:
            res = download_xml_from_ena(f'https://www.ebi.ac.uk/ena/browser/api/xml/{ena_accession}')
        except HTTPError as e:
            # We cannot currently differentiate between the service returning an error and the accession not existing
            if e.response.status_code == 500:
                self.add_error(json_path, f'{accession_type} {ena_accession} does not exist in ENA or is private')
            else:
                self.add_error(json_path, f'{accession_type} {ena_accession} does not exist in ENA or is private')
        except Exception as e:
            self.add_error(json_path, f'Unexpected error occurred when checking {accession_type} {ena_accession}')

    def check_project_accession(self, project_acc, json_path):
        self.check_accession_in_ena(project_acc, 'Project', json_path)

    @retry(tries=4, delay=2, backoff=1.2, jitter=(1, 3))
    def check_taxonomy_code(self, taxonomy_code, json_path):
        taxonomy_code = int(taxonomy_code)
        if taxonomy_code in self.taxonomy_valid:
            if self.taxonomy_valid[taxonomy_code] is False:
                self.add_error(json_path, f'{taxonomy_code} is not a valid taxonomy code')
        else:
            try:
                sci_name, _ = get_scientific_name_and_common_name(taxonomy_code)
                self.taxonomy_valid[taxonomy_code] = sci_name
            except Exception:
                self.add_error(json_path, f'{taxonomy_code} is not a valid taxonomy code')
                self.taxonomy_valid[taxonomy_code] = False

    def add_error(self, property, description):
        """
        Add an error, conforming to the format of biovalidator errors.

        :param property: JSON property of the error. This will be converted to sheet/row/column in spreadsheet if needed.
        :param description: description of the error.
        """
        self.errors.append({'property': property, 'description': description})

    def _get_biosample(self, sample_accession, include_curation=False):
        if include_curation:
            append_to_url = sample_accession
        else:
            append_to_url = sample_accession + '?curationdomain='
        return self.communicator.follows_link('samples', join_url=append_to_url)

    def check_existing_biosamples(self):
        """Check that existing BioSamples are accessible and contain the required attributes."""
        for idx, sample in enumerate(self.metadata[SAMPLE_KEY]):
            if BIOSAMPLE_ACCESSION_KEY in sample:
                sample_accession = sample[BIOSAMPLE_ACCESSION_KEY]
                json_path = f'/{SAMPLE_KEY}/{idx}/{BIOSAMPLE_ACCESSION_KEY}'
                try:
                    sample_data = self._get_biosample(sample_accession)
                    if self.sample_checklist:
                        self._validate_biosample_against_checklist(sample_data, json_path, sample_accession)
                    else:
                        self._local_validate_existing_biosample(sample_data, json_path, sample_accession)

                except ValueError:
                    self.add_error(json_path, f'{sample_accession} does not exist or is private')

    def _validate_biosample_against_checklist(self, sample_data, json_path, accession=None):
        pre_acceptable_code = self.communicator.acceptable_code
        try:
            # Allow the communicator to accept failure
            self.communicator.acceptable_code = [200, 400]
            sample_data = deepcopy(sample_data)
            # Add checklist to the sample
            if 'characteristics' not in sample_data:
                sample_data['characteristics'] = {}
            if 'checklist' not in sample_data['characteristics']:
                sample_data['characteristics']['checklist'] = []
            sample_data['characteristics']['checklist'].append({'text': self.sample_checklist})
            text = self.communicator.follows_link('samples', join_url='validate', method='POST', json=sample_data,
                                                  text_only=True)
            response = json.loads(text)
            # Successful response returns the sample object, error response has a list of error objects.
            if isinstance(response, list):
                for error_dict in response:
                    error_property = ''
                    # Retrieve the property the error applied to in the datapath
                    if 'dataPath' in error_dict:
                        if error_dict['dataPath'].startswith('/characteristics/'):
                            error_property = error_dict['dataPath'].split('/')[2]
                        else:
                            error_property = error_dict['dataPath']
                    # Define the error
                    error_list = []
                    if accession:
                        error_list.append(f'Error validating existing sample {accession}:')
                    if error_property and error_property not in error_dict['errors'][0]:
                        error_list.append(error_property)
                    error_list.append(error_dict['errors'][0])
                    error = ' '.join(error_list)
                    if self._should_bypass_error(sample_data, error):
                        self.debug(f'bypass error {error} from {json_path}')
                        continue
                    self.add_error(json_path, error)

        finally:
            self.communicator.acceptable_code = pre_acceptable_code

    def _should_bypass_error(self, sample_data, error):
        try:
            try:
                created_dated = datetime.strptime(sample_data['create'], '%Y-%m-%dT%H:%M:%S.%fZ')
            except ValueError:
                created_dated = datetime.strptime(sample_data['create'], '%Y-%m-%dT%H:%M:%SZ')
            if created_dated < threshold_2023 and (
                    'collection date' in error or
                    'geographic location (country and/or sea)' in error
            ):
                return True
        except Exception:
            pass
        return False

    def _local_validate_existing_biosample(self, sample_data, json_path, accession):
        """Check if the existing sample has the expected fields present"""
        if self._should_bypass_error(sample_data, 'collection date'):
            return
        found_collection_date = False
        for key in ['collection_date', 'collection date']:
            if key in sample_data['characteristics'] and check_date(sample_data['characteristics'][key][0]['text']):
                found_collection_date = True
        if not found_collection_date:
            self.add_error(json_path, f'Existing sample {accession} does not have a valid collection date')

        found_geo_loc = False
        for key in ['geographic location (country and/or sea)', 'geo loc name']:
            if key in sample_data['characteristics'] and sample_data['characteristics'][key][0]['text']:
                found_geo_loc = True
        if not found_geo_loc:
            self.add_error(json_path, f'Existing sample {accession} does not have a valid geographic location')

    def check_analysis_alias_coherence(self):
        """Check that the same analysis aliases are used in analysis, sample, and files."""
        analysis_aliases = [analysis[ANALYSIS_ALIAS_KEY] for analysis in self.metadata[ANALYSIS_KEY]]
        aliases_in_samples = [alias for sample in self.metadata[SAMPLE_KEY] for alias in sample[ANALYSIS_ALIAS_KEY]]
        aliases_in_files = [file[ANALYSIS_ALIAS_KEY] for file in self.metadata[FILES_KEY]]

        self.same_set(analysis_aliases, aliases_in_samples, 'Analysis', 'Samples',
                      f'/{SAMPLE_KEY}/{ANALYSIS_ALIAS_KEY}')
        self.same_set(analysis_aliases, aliases_in_files, 'Analysis', 'Files',
                      f'/{FILES_KEY}/{ANALYSIS_ALIAS_KEY}')

    def same_set(self, list1, list2, list1_desc, list2_desc, json_path):
        """
        Compare contents of two lists and add error messages.

        :param list1: first list to compare
        :param list2: second list to compare
        :param list1_desc: text description of first list, used only in error message
        :param list2_desc: text description of second list, used only in error message
        :param json_path: property where the error message will appear
        """
        if not set(list1) == set(list2):
            list1_list2 = sorted(cast_list(set(list1).difference(list2)))
            list2_list1 = sorted(cast_list(set(list2).difference(list1)))
            if list1_list2:
                self.add_error(
                    property=json_path,
                    description=f'{",".join(list1_list2)} present in {list1_desc} not in {list2_desc}'
                )
            if list2_list1:
                self.add_error(
                    property=json_path,
                    description=f'{",".join(list2_list1)} present in {list2_desc} not in {list1_desc}'
                )

    def check_all_analysis_contain_samples(self):
        sample_analysis_aliases_set = set()
        for sample in self.metadata.get(SAMPLE_KEY, []):
            for analysis_alias in sample.get(ANALYSIS_ALIAS_KEY, []):
                sample_analysis_aliases_set.add(analysis_alias)

        for idx, analysis in enumerate(self.metadata.get(ANALYSIS_KEY, [])):
            analysis_alias = analysis.get(ANALYSIS_ALIAS_KEY)
            if analysis_alias and analysis_alias not in sample_analysis_aliases_set:
                json_path = f'/{ANALYSIS_KEY}/{idx}'
                self.add_error(property=json_path,
                               description=f'No sample found for the analysis. Should have at the least one sample.')
