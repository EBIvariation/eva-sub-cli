#!/usr/bin/env python
import json
import os

import requests
from ebi_eva_common_pyutils.config import WritableConfig
from ebi_eva_common_pyutils.logger import AppLogger
from retry import retry

from eva_sub_cli import SUB_CLI_CONFIG_FILE, __version__
from eva_sub_cli.submission_ws import SubmissionWSClient
from eva_sub_cli.validators.validator import READY_FOR_SUBMISSION_TO_EVA

SUB_CLI_CONFIG_KEY_SUBMISSION_ID = "submission_id"
SUB_CLI_CONFIG_KEY_SUBMISSION_UPLOAD_URL = "submission_upload_url"
SUB_CLI_CONFIG_KEY_COMPLETE = "submission_complete"


class StudySubmitter(AppLogger):
    def __init__(self, submission_dir, submission_config: WritableConfig = None, username=None, password=None):
        self.submission_ws_client = SubmissionWSClient(username, password)
        self.submission_dir = submission_dir
        if submission_config:
            self.sub_config = submission_config
        else:
            config_file = os.path.join(submission_dir, SUB_CLI_CONFIG_FILE)
            self.sub_config = WritableConfig(config_file, version=__version__)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.sub_config.backup()
        self.sub_config.write()

    @property
    def metadata_json_file(self):
        return self.sub_config.get('metadata_json')

    @property
    def metadata_json(self):
        with open(self.metadata_json_file) as open_file:
            return json.load(open_file)

    @property
    def vcf_files(self):
        return self.sub_config.get('vcf_files')

    def update_config_with_submission_id_and_upload_url(self, submission_id, upload_url):
        self.sub_config.set(SUB_CLI_CONFIG_KEY_SUBMISSION_ID, value=submission_id)
        self.sub_config.set(SUB_CLI_CONFIG_KEY_SUBMISSION_UPLOAD_URL, value=upload_url)

    def _upload_submission(self):
        if READY_FOR_SUBMISSION_TO_EVA not in self.sub_config or not self.sub_config[READY_FOR_SUBMISSION_TO_EVA]:
            raise Exception(f'There are still validation errors that needs to be addressed. '
                            f'Please review, address and re-validate before uploading.')

        submission_upload_url = self.sub_config[SUB_CLI_CONFIG_KEY_SUBMISSION_UPLOAD_URL]

        self._upload_file(submission_upload_url, self.metadata_json_file)

        for f in self.vcf_files:
            self._upload_file(submission_upload_url, f)

    @retry(tries=5, delay=10, backoff=5)
    def _upload_file(self, submission_upload_url, input_file):
        base_name = os.path.basename(input_file)
        self.debug(f'Transfer {base_name} to EVA FTP')
        with open(input_file, 'rb') as f:
            r = requests.put(os.path.join(submission_upload_url, base_name), data=f)
        r.raise_for_status()
        self.debug(f'Upload of {base_name} completed')

    def _initiate_submission(self):
        response_json = self.submission_ws_client.initiate_submission()
        self.debug(f'Submission ID {response_json["submissionId"]} received!!')
        # update config with submission id and upload url
        self.update_config_with_submission_id_and_upload_url(response_json["submissionId"], response_json["uploadUrl"])

    def _complete_submission(self):
        self.submission_ws_client.mark_submission_uploaded(self.sub_config.get(SUB_CLI_CONFIG_KEY_SUBMISSION_ID), self.metadata_json)
        self.debug("Submission ID {} Complete".format(self.sub_config.get(SUB_CLI_CONFIG_KEY_SUBMISSION_ID)))
        # update config with completion of the submission
        self.sub_config.set(SUB_CLI_CONFIG_KEY_COMPLETE, value=True)

    def is_submission_status_open(self):
        submission_id = self.sub_config.get(SUB_CLI_CONFIG_KEY_SUBMISSION_ID)
        if submission_id:
            status = self.submission_ws_client.get_submission_status(submission_id)
            return status == 'OPEN'
        return False

    def submit(self):
        if READY_FOR_SUBMISSION_TO_EVA not in self.sub_config or not self.sub_config[READY_FOR_SUBMISSION_TO_EVA]:
            raise Exception(f'There are still validation errors that need to be addressed. '
                            f'Please review, address and re-validate before submitting.')
        if not self.sub_config.get(SUB_CLI_CONFIG_KEY_SUBMISSION_UPLOAD_URL):
            self.info(f'Initiate submission')
            self._initiate_submission()

        if not self.is_submission_status_open():
            self.warning(f'You requested the submission using {self.submission_dir}. '
                         f'This directory contains an already completed submission. '
                         f'Please create a new submission directory to resubmit.')
            return

        # upload submission
        self.info(f'Start Uploading data')
        self._upload_submission()
        self.info(f'Data Uploaded successfully')

        # Complete the submission
        self._complete_submission()
        self.info(f'Submission completed successfully')
