#!/usr/bin/env python
import json
import requests
from getpass import getpass


class StudySubmitter:
    def __init__(self, ENA_AUTH_URL="https://www.ebi.ac.uk/ena/submit/webin/auth/token",
                 WEBIN_SUBMIT_ENDPOINT ="http://www.ebi.ac.uk/eva/v1/submission/initiate/webin"):
        self.ENA_AUTH_URL = ENA_AUTH_URL
        self.WEBIN_SUBMIT_ENDPOINT = WEBIN_SUBMIT_ENDPOINT

    # TODO
    def initiate_submit_with_lsri_auth(self):
        return NotImplementedError

    # TODO
    def upload_submission(self, submission_id, submission_upload_url):
        pass

    def initiate_submit_with_webin_auth(self):
        print("Proceeding with ENA Webin authentication...")
        username = input("Enter your ENA Webin username: ")
        password = getpass("Enter your ENA Webin password: ")

        headers = {"accept": "*/*", "Content-Type": "application/json"}
        data = {"authRealms": ["ENA"], "username": username, "password": password}
        response = requests.post(self.ENA_AUTH_URL, headers=headers, data=json.dumps(data))

        if response.status_code == 200:
            print("Authentication successful")
            webin_token = response.text
            response = requests.post(self.WEBIN_SUBMIT_ENDPOINT + "/" + webin_token)
            response_json = json.loads(response.text)
            print("Submission ID {} received!!".format(response_json["submissionId"]))

        else:
            print("Authentication failed")

    def auth_prompt(self):
        print("Choose an authentication method:")
        print("1. ENA Webin")
        print("2. LSRI")

        choice = int(input("Enter the number corresponding to your choice: "))

        if choice == 1:
            self.initiate_submit_with_webin_auth()
        elif choice == 2:
            self.initiate_submit_with_lsri_auth()
        else:
            print("Invalid choice! Try again!")
            self.auth_prompt()


if __name__ == "__main__":
    submitter = StudySubmitter(WEBIN_SUBMIT_ENDPOINT="http://localhost:8080/v1/submission/initiate/webin")
    submitter.auth_prompt()
