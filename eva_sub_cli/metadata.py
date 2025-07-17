import json
import os
from collections import defaultdict
from copy import deepcopy
from functools import cached_property

from ebi_eva_common_pyutils.logger import AppLogger


class EvaMetadataJson(AppLogger):

    def __init__(self, path_to_json):
        with open(path_to_json) as open_json:
            self.content = json.load(open_json)

    @property
    def project(self):
        return self.content.get('project', {})

    @property
    def submitter_details(self):
        return self.content.get('submitterDetails', {})

    @property
    def analyses(self):
        return self.content.get('analysis', [])

    @property
    def samples(self):
        return self.content.get('sample', [])

    @property
    def files(self):
        return self.content.get('files', [])

    @cached_property
    def resolved_files(self):
        """Returns list of files with fileName resolved to an absolute path."""
        mod_files = deepcopy(self.content.get('files', []))
        for file_info in mod_files:
            if 'fileName' in file_info:
                file_info['fileName'] = os.path.abspath(file_info['fileName'])
        return mod_files

    def set_files(self, file_list):
        assert isinstance(file_list, list)
        self.content['files'] = file_list
        # invalidate the cached property
        if self.resolved_files:
            del self.resolved_files

    def set_analyses(self, analysis_list):
        assert isinstance(analysis_list, list)
        self.content['analysis'] = analysis_list

    @cached_property
    def samples_per_analysis(self):
        """Returns mapping of analysis alias to sample names, based on metadata."""
        samples_per_analysis = defaultdict(list)
        for sample_info in self.samples:
            for analysis_alias in sample_info.get('analysisAlias', []):
                samples_per_analysis[analysis_alias].append(sample_info.get('sampleInVCF'))
        return {
            analysis_alias: set(samples)
            for analysis_alias, samples in samples_per_analysis.items()
        }

    @cached_property
    def files_per_analysis(self):
        """Returns mapping of analysis alias to filenames, based on metadata."""
        files_per_analysis = defaultdict(list)
        for file_info in self.resolved_files:
            files_per_analysis[file_info.get('analysisAlias')].append(file_info.get('fileName'))
        return {
            analysis_alias: set(filepaths)
            for analysis_alias, filepaths in files_per_analysis.items()
        }

    def get_reference_assembly_for_analysis(self, analysis_alias):
        """Returns the reference assembly for this analysis (does not validate format)."""
        for analysis in self.analyses:
            if analysis.get('analysisAlias') == analysis_alias:
                return analysis.get('referenceGenome')
        return None

    def get_analysis_for_vcf_file(self, vcf_file):
        """Returns list of analysis aliases associated with the vcf file path."""
        if not os.path.exists(vcf_file):
            raise FileNotFoundError(f'{vcf_file} cannot be resolved')
        analysis_aliases = [analysis_alias for analysis_alias in self.files_per_analysis
                            if vcf_file in self.files_per_analysis[analysis_alias]
                            or os.path.basename(vcf_file) in [
                                os.path.basename(p) for p in self.files_per_analysis[analysis_alias]
                            ]]
        return analysis_aliases

    def write(self, output_path):
        with open(output_path, 'w') as open_file:
            json.dump(self.content, open_file)
