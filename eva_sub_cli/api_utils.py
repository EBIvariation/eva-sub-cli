import os

import requests

from eva_sub_cli import SUBMISSION_WS_VAR

SUBMISSION_WS_URL = 'https://www.ebi.ac.uk/eva/webservices/submission-ws/v1/'
SUBMISSION_INITIATE_PATH = 'submission/initiate'
SUBMISSION_UPLOADED_PATH = 'submission/{submissionId}/uploaded'
SUBMISSION_STATUS_PATH = 'submission/{submissionId}/status'


def get_submission_ws_url(sub_ws_url=None):
    """Retrieve the base URL for the submission web services. In order of preference from the user of this class,
    the environment variable or the hardcoded value."""
    if sub_ws_url:
        return sub_ws_url
    if os.environ.get(SUBMISSION_WS_VAR):
        return os.environ.get(SUBMISSION_WS_VAR)
    else:
        return SUBMISSION_WS_URL


def get_submission_initiate_url(sub_ws_url=None):
    return os.path.join(get_submission_ws_url(sub_ws_url), SUBMISSION_INITIATE_PATH)


def get_submission_uploaded_url(submission_id, sub_ws_url=None):
    return os.path.join(get_submission_ws_url(sub_ws_url), SUBMISSION_UPLOADED_PATH.format(submissionId=submission_id))


def get_submission_status_url(submission_id, sub_ws_url=None):
    return os.path.join(get_submission_ws_url(sub_ws_url), SUBMISSION_STATUS_PATH.format(submissionId=submission_id))


def get_submission_status(submission_id, sub_ws_url=None):
    response = requests.get(get_submission_status_url(submission_id, sub_ws_url))
    response.raise_for_status()
    return response.text
