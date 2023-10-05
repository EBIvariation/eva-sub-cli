#!/usr/bin/env python
import os

import requests
import yaml
from ebi_eva_common_pyutils.logger import logging_config

from cli.auth import get_auth

logger = logging_config.get_logger(__name__)
SUB_CLI_CONFIG_FILE = ".eva-sub-cli-config.yml"
SUB_CLI_CONFIG_KEY_SUBMISSION_ID = "submission_id"
SUB_CLI_CONFIG_KEY_SUBMISSION_UPLOAD_URL = "submission_upload_url"
SUBMISSION_INITIATE_URL = "http://www.ebi.ac.uk/eva/v1/submission/initiate"


class StudySubmitter:
    def __init__(self, submission_initiate_url=SUBMISSION_INITIATE_URL):
        self.auth = get_auth()
        self.submission_initiate_url = submission_initiate_url

    def create_submission_config_file(self, submission_dir, submission_id, submission_upload_url):
        submission_config_file = os.path.join(submission_dir, SUB_CLI_CONFIG_FILE)
        config_data = {
            SUB_CLI_CONFIG_KEY_SUBMISSION_ID: submission_id,
            SUB_CLI_CONFIG_KEY_SUBMISSION_UPLOAD_URL: submission_upload_url
        }
        with open(submission_config_file, 'w') as open_file:
            yaml.safe_dump(config_data, open_file)

    def get_submission_id_and_upload_url(self, submission_dir):
        submission_config_file = os.path.join(submission_dir, SUB_CLI_CONFIG_FILE)
        if submission_config_file:
            with (open(submission_config_file, 'r') as f):
                submission_config_data = yaml.safe_load(f)
                return submission_config_data[SUB_CLI_CONFIG_KEY_SUBMISSION_ID], submission_config_data[
                    SUB_CLI_CONFIG_KEY_SUBMISSION_UPLOAD_URL]
        else:
            raise FileNotFoundError(f'Could not upload. No config file found for the submission in {submission_dir}.')

    # TODO
    def upload_submission(self, submission_dir, submission_id=None, submission_upload_url=None):
        if not submission_id or not submission_upload_url:
            submission_id, submission_upload_url = self.get_submission_id_and_upload_url(submission_dir)
        pass

    def verify_submission_dir(self, submission_dir):
        if not os.path.exists(submission_dir):
            os.makedirs(submission_dir)
        if not os.access(submission_dir, os.W_OK):
            raise Exception(f"The directory '{submission_dir}' does not have write permissions.")


    def submit(self, submission_dir):
        self.verify_submission_dir(submission_dir)
        response = requests.post(self.submission_initiate_url,
                                 headers={'Accept': 'application/hal+json',
                                          'Authorization': 'Bearer ' + self.auth.token})
        response.raise_for_status()
        response_json = response.json()
        logger.info("Submission ID {} received!!".format(response_json["submissionId"]))
        self.create_submission_config_file(submission_dir, response_json["submissionId"], response_json["uploadUrl"])
        self.upload_submission(submission_dir, response_json["submissionId"], response_json["uploadUrl"])
