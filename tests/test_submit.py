import json
import unittest
from unittest.mock import MagicMock, patch, Mock, PropertyMock

from cli import LSRI_CLIENT_ID
from cli.auth import WebinAuth, LSRIAuth
from cli.submit import StudySubmitter


class TestSubmit(unittest.TestCase):

    def setUp(self) -> None:
        self.token = 'a token'
        with patch('cli.submit.get_auth', return_value=Mock(token=self.token)):
            self.submitter = StudySubmitter()

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
