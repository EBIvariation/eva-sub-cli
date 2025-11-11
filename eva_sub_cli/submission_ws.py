import os

import requests
from ebi_eva_common_pyutils.logger import AppLogger
from requests import HTTPError
from retry import retry

from eva_sub_cli import SUBMISSION_WS_VAR
from eva_sub_cli.auth import get_auth
from eva_sub_cli.exceptions.submission_upload_exception import SubmissionUploadException


class SubmissionWSClient(AppLogger):
    """
    Python client for interfacing with the Submission WS API.
    """

    def __init__(self, username=None, password=None):
        self.auth = get_auth(username, password)
        self.base_url = self._submission_ws_url

    SUBMISSION_WS_URL = 'https://www.ebi.ac.uk/eva/webservices/submission-ws/v1/'
    SUBMISSION_INITIATE_PATH = 'submission/initiate'
    SUBMISSION_UPLOADED_PATH = 'submission/{submissionId}/uploaded'
    SUBMISSION_STATUS_PATH = 'submission/{submissionId}/status'

    @property
    def _submission_ws_url(self):
        """Retrieve the base URL for the submission web services.
        In order of preference from the environment variable or the hardcoded value."""
        if os.environ.get(SUBMISSION_WS_VAR):
            return os.environ.get(SUBMISSION_WS_VAR)
        else:
            return self.SUBMISSION_WS_URL

    def _submission_initiate_url(self):
        return os.path.join(self.base_url, self.SUBMISSION_INITIATE_PATH)

    def _submission_uploaded_url(self, submission_id):
        return os.path.join(self.base_url, self.SUBMISSION_UPLOADED_PATH.format(submissionId=submission_id))

    def _submission_status_url(self, submission_id):
        return os.path.join(self.base_url, self.SUBMISSION_STATUS_PATH.format(submissionId=submission_id))

    def mark_submission_uploaded(self, submission_id, metadata_json):
        response = requests.put(self._submission_uploaded_url(submission_id),
                            headers={'Accept': 'application/json', 'Authorization': 'Bearer ' + self.auth.token},
                            json=metadata_json)
        if 400 <= response.status_code < 500:
            raise SubmissionUploadException(f"There was an error in uploading the submission {submission_id}."
                                            f"Status: {response.status_code}. Error: {response.text}")
        else:
            response.raise_for_status()
            return response.json()

    def initiate_submission(self):
        response = requests.post(self._submission_initiate_url(), headers={'Accept': 'application/json',
                                                                           'Authorization': 'Bearer ' + self.auth.token})
        response.raise_for_status()
        return response.json()

    @retry(exceptions=(HTTPError,), tries=3, delay=2, backoff=1.2, jitter=(1, 3))
    def get_submission_status(self, submission_id):
        response = requests.get(self._submission_status_url(submission_id))
        response.raise_for_status()
        return response.text
