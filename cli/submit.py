#!/usr/bin/env python
import json
import requests

from ebi_eva_common_pyutils.logger import logging_config
from getpass import getpass

logger = logging_config.get_logger(__name__)


class StudySubmitter:
    def __init__(self, ENA_AUTH_URL="https://www.ebi.ac.uk/ena/submit/webin/auth/token",
                 SUBMISSION_INITIATE_ENDPOINT ="http://www.ebi.ac.uk/eva/v1/submission/initiate/webin"):
        self.ENA_AUTH_URL = ENA_AUTH_URL
        self.SUBMISSION_INITIATE_ENDPOINT = SUBMISSION_INITIATE_ENDPOINT

    # TODO
    def submit_with_lsri_auth(self):
        return NotImplementedError

    # TODO
    def upload_submission(self, submission_id, submission_upload_url):
        pass

    def _get_webin_credentials(self):
        username = input("Enter your ENA Webin username: ")
        password = getpass("Enter your ENA Webin password: ")
        return username, password

    def submit_with_webin_auth(self, username, password):
        logger.info("Proceeding with ENA Webin authentication...")

        headers = {"accept": "*/*", "Content-Type": "application/json"}
        data = {"authRealms": ["ENA"], "username": username, "password": password}
        response = requests.post(self.ENA_AUTH_URL, headers=headers, data=json.dumps(data))

        if response.status_code == 200:
            logger.info("Authentication successful!")
            webin_token = response.text
            response = requests.post(self.SUBMISSION_INITIATE_ENDPOINT,
                                     headers={'Accept': 'application/hal+json',
                                              'Authorization': 'Bearer ' + webin_token})
            response_json = json.loads(response.text)
            logger.info("Submission ID {} received!!".format(response_json["submissionId"]))
            self.upload_submission(response_json["submissionId"], response_json["uploadUrl"])
        else:
            logger.error("Authentication failed!")

    def auth_prompt(self):
        print("Choose an authentication method:")
        print("1. ENA Webin")
        print("2. LSRI")

        choice = int(input("Enter the number corresponding to your choice: "))

        if choice == 1:
            webin_username, webin_password = self._get_webin_credentials()
            self.submit_with_webin_auth(webin_username, webin_password)
        elif choice == 2:
            self.submit_with_lsri_auth()
        else:
            logger.error("Invalid choice! Try again!")
            self.auth_prompt()


if __name__ == "__main__":
    logging_config.add_stdout_handler()
    submitter = StudySubmitter()
    submitter.auth_prompt()
