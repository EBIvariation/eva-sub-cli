import json
import unittest
from unittest.mock import MagicMock, patch

from cli import LSRI_CLIENT_ID
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
            self.submitter.ena_auth_url,
            headers={"accept": "*/*", "Content-Type": "application/json"},
            data=json.dumps({"authRealms": ["ENA"], "username": "mock_username", "password": "mock_password"}),
        )

        # Check if the WEBIN_SUBMIT_ENDPOINT was called with the correct parameters
        mock_post.assert_any_call(
            self.submitter.submission_initiate_webin_url, headers={'Accept': 'application/hal+json',
                                                                  'Authorization': 'Bearer ' + 'mock_webin_token'}
        )

        # Check the total number of calls to requests.post
        assert mock_post.call_count == 2

    @patch("cli.submit.requests.post")
    def test_submit_with_lsri_auth(self, mock_post):
        # Mock the response for OAuth device flow initiation
        # see get_auth_response() in LSRIAuth class
        mock_auth_response = MagicMock()
        mock_auth_response.status_code = 200
        mock_auth_response.json.return_value = {"device_code": "device_code", "user_code": "user_code",
                                                "verification_uri": "verification_uri", "expires_in": 600}

        # Mock the response for post-authentication response from eva-submission-ws
        # see get_auth_response() in LSRIAuth class
        mock_submit_response = MagicMock()
        mock_submit_response.status_code = 200
        mock_submit_response.text = json.dumps({"submissionId": "mock_submission_id", "uploadUrl": "mock_upload_url"})

        # Set the side_effect attribute to return different responses
        mock_post.side_effect = [mock_auth_response, mock_submit_response]
        self.submitter.submit_with_lsri_auth()

        # Check if the device initiation flow was called with the correct parameters
        device_authorization_url = "https://login.elixir-czech.org/oidc/devicecode"
        print(mock_post.mock_calls)
        mock_post.assert_any_call(device_authorization_url,
                                  data={'client_id': LSRI_CLIENT_ID, 'scope': 'openid'})

        # Check if the post-authentication call to eva-submission-ws was called with the correct parameters
        mock_post.assert_any_call(
            self.submitter.submission_initiate_lsri_url, headers={'Accept': 'application/hal+json'},
            params={'deviceCode': 'device_code', 'expiresIn': 600}
        )

        # Check the total number of calls to requests.post
        assert mock_post.call_count == 2
