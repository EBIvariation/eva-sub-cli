#!/usr/bin/env python
import json
import requests

from cli import LSRI_CLIENT_ID
from ebi_eva_common_pyutils.logger import logging_config
from getpass import getpass
from cli.lsri_auth import LSRIAuth

logger = logging_config.get_logger(__name__)
ENA_AUTH_URL="https://www.ebi.ac.uk/ena/submit/webin/auth/token",
SUBMISSION_INITIATE_WEBIN_URL ="http://www.ebi.ac.uk/eva/v1/submission/initiate/webin",
SUBMISSION_INITIATE_LSRI_URL ="http://www.ebi.ac.uk/eva/v1/submission/initiate/lsri"


class StudySubmitter:
    def __init__(self, ena_auth_url=ENA_AUTH_URL, submission_initiate_webin_url = SUBMISSION_INITIATE_WEBIN_URL,
                 submission_initiate_lsri_url = SUBMISSION_INITIATE_LSRI_URL):
        self.ena_auth_url = ena_auth_url
        self.submission_initiate_webin_url = submission_initiate_webin_url
        self.submission_initiate_lsri_url = submission_initiate_lsri_url

    def submit_with_lsri_auth(self):
        logger.info("Proceeding with LSRI authentication...")
        # For now, it is OK for client ID to be hardcoded because, unlike client secret, it is not sensitive information
        response = LSRIAuth(client_id=LSRI_CLIENT_ID,
                            device_authorization_url="https://login.elixir-czech.org/oidc/devicecode",
                            submission_initiation_url=self.submission_initiate_lsri_url).get_auth_response()
        if response.status_code == 200:
            logger.info("LSRI authentication successful!")
            response_json = json.loads(response.text)
            logger.info("Submission ID {} received!!".format(response_json["submissionId"]))
            self.upload_submission(response_json["submissionId"], response_json["uploadUrl"])
        else:
            raise RuntimeError("Could not perform LSRI Authentication! Please try running this script again.")

    # TODO
    def upload_submission(self, submission_id, submission_upload_url):
        pass

    @staticmethod
    def _get_webin_credentials():
        username = input("Enter your ENA Webin username: ")
        password = getpass("Enter your ENA Webin password: ")
        return username, password

    def submit_with_webin_auth(self, username, password):
        logger.info("Proceeding with ENA Webin authentication...")

        headers = {"accept": "*/*", "Content-Type": "application/json"}
        data = {"authRealms": ["ENA"], "username": username, "password": password}
        response = requests.post(self.ena_auth_url, headers=headers, data=json.dumps(data))

        if response.status_code == 200:
            logger.info("Webin authentication successful!")
            webin_token = response.text
            response = requests.post(self.submission_initiate_webin_url,
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
            webin_username, webin_password = StudySubmitter._get_webin_credentials()
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
