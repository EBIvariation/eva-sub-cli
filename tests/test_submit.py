import json
import os
import shutil
import unittest
from unittest.mock import MagicMock, patch, Mock, PropertyMock

import yaml

from cli import LSRI_CLIENT_ID
from cli.auth import WebinAuth, LSRIAuth
from cli.submit import StudySubmitter, SUB_CLI_CONFIG_FILE, SUB_CLI_CONFIG_KEY_SUBMISSION_ID, \
    SUB_CLI_CONFIG_KEY_SUBMISSION_UPLOAD_URL


class TestSubmit(unittest.TestCase):

    def setUp(self) -> None:
        self.token = 'a token'
        with patch('cli.submit.get_auth', return_value=Mock(token=self.token)):
            self.submitter = StudySubmitter()
        self.test_sub_dir = os.path.join(os.path.dirname(__file__), 'resources', 'test_sub_dir')
        shutil.rmtree(self.test_sub_dir, ignore_errors=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.test_sub_dir, ignore_errors=True)

    def test_submit(self):
        # Mock the response for post-authentication response from eva-submission-ws
        # see get_auth_response() in LSRIAuth class
        mock_submit_response = MagicMock()
        mock_submit_response.status_code = 200
        mock_submit_response.text = json.dumps({"submissionId": "mock_submission_id",
                                                'uploadUrl': 'directory to use for upload'})

        # Set the side_effect attribute to return different responses
        with patch('cli.submit.requests.post', return_value=mock_submit_response) as mock_post:
            with patch('cli.submit.StudySubmitter.create_submission_config_file'):
                self.submitter.submit('test_submission_directory')
        mock_post.assert_called_once_with('http://www.ebi.ac.uk/eva/v1/submission/initiate',
                                          headers={'Accept': 'application/hal+json', 'Authorization': 'Bearer a token'})

        # TODO: Check that upload_submission was called with submission id

    def test_verify_submission_dir(self):
        self.submitter.verify_submission_dir(self.test_sub_dir)
        assert os.path.exists(self.test_sub_dir)

    def test_verify_submission_dircreate_submission_config_file(self):
        self.submitter.verify_submission_dir(self.test_sub_dir)
        self.submitter.create_submission_config_file(self.test_sub_dir, 1234, "/sub/upload/url")

        sub_config_file = os.path.join(self.test_sub_dir, SUB_CLI_CONFIG_FILE)
        assert os.path.exists(sub_config_file)

        with (open(sub_config_file, 'r') as f):
            sub_config_data = yaml.safe_load(f)
            assert sub_config_data[SUB_CLI_CONFIG_KEY_SUBMISSION_ID] == 1234
            assert sub_config_data[SUB_CLI_CONFIG_KEY_SUBMISSION_UPLOAD_URL] == "/sub/upload/url"

    def test_get_submission_id_and_upload_url(self):
        self.submitter.verify_submission_dir(self.test_sub_dir)
        self.submitter.create_submission_config_file(self.test_sub_dir, 1234, "/sub/upload/url")

        submission_id, upload_url = self.submitter.get_submission_id_and_upload_url(self.test_sub_dir)

        assert submission_id == 1234
        assert upload_url == "/sub/upload/url"



    def test_submit(self):
        mock_submit_response = MagicMock()
        mock_submit_response.status_code = 200
        mock_submit_response.json.return_value = {
            "submissionId": "mock_submission_id",
            "uploadUrl": "directory to use for upload",
        }
        with patch('cli.submit.requests.post', return_value=mock_submit_response) as mock_post:
            self.submitter.submit(self.test_sub_dir)

        assert os.path.exists(self.test_sub_dir)
        sub_config_file = os.path.join(self.test_sub_dir, SUB_CLI_CONFIG_FILE)
        assert os.path.exists(sub_config_file)
        with (open(sub_config_file, 'r') as f):
            sub_config_data = yaml.safe_load(f)
            assert sub_config_data[SUB_CLI_CONFIG_KEY_SUBMISSION_ID] == "mock_submission_id"
            assert sub_config_data[SUB_CLI_CONFIG_KEY_SUBMISSION_UPLOAD_URL] == "directory to use for upload"



