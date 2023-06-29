import json
import unittest
from unittest.mock import MagicMock, patch
from cli.submit import StudySubmitter


class TestStudySubmitter(unittest.TestCase):
    def setUp(self):
        self.submitter = StudySubmitter()

    @patch("cli.submit.requests.post")
    def test_submit_with_webin_auth(self, mock_post):
        # Mock the response for ENA authentication
        mock_auth_response = MagicMock()
        mock_auth_response.status_code = 200
        mock_auth_response.text = "mock_webin_token"

        # Mock the response for WEBIN_SUBMIT_ENDPOINT
        mock_submit_response = MagicMock()
        mock_submit_response.text = json.dumps({"submissionId": "mock_submission_id", "uploadUrl": "mock_upload_url"})

        # Set the side_effect attribute to return different responses
        mock_post.side_effect = [mock_auth_response, mock_submit_response]

        # Call the submit_with_webin_auth method
        self.submitter.submit_with_webin_auth("mock_username", "mock_password")

        # Check if the ENA_AUTH_URL was called with the correct parameters
        mock_post.assert_any_call(
            self.submitter.ENA_AUTH_URL,
            headers={"accept": "*/*", "Content-Type": "application/json"},
            data=json.dumps({"authRealms": ["ENA"], "username": "mock_username", "password": "mock_password"}),
        )

        # Check if the WEBIN_SUBMIT_ENDPOINT was called with the correct parameters
        mock_post.assert_any_call(
            self.submitter.SUBMISSION_INITIATE_ENDPOINT, headers={'Accept': 'application/hal+json',
                                                                  'Authorization': 'Bearer ' + 'mock_webin_token'}
        )

        # Check the total number of calls to requests.post
        assert mock_post.call_count == 2
