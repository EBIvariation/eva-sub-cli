import json
import os
import unittest
from unittest.mock import MagicMock, patch

from eva_sub_cli import LSRI_CLIENT_ID, ENA_WEBIN_ACCOUNT_VAR, ENA_WEBIN_PASSWORD_VAR
from eva_sub_cli.auth import WebinAuth, LSRIAuth


class TestWebinAuth(unittest.TestCase):

    def test_webin_auth(self):
        auth = WebinAuth()
        # Mock the response for ENA authentication
        mock_auth_response = MagicMock()
        mock_auth_response.status_code = 200
        mock_auth_response.text = "mock_webin_token"

        # Call the submit_with_webin_auth method
        with patch.object(WebinAuth, '_get_webin_username_password', return_value=("mock_username", "mock_password")), \
             patch("eva_sub_cli.auth.requests.post", return_value=mock_auth_response) as mock_post:
            token = auth.token

        # Check if the ENA_AUTH_URL was called with the correct parameters
        mock_post.assert_any_call(
            auth.ena_auth_url,
            headers={"accept": "*/*", "Content-Type": "application/json"},
            data=json.dumps({"authRealms": ["ENA"], "username": "mock_username", "password": "mock_password"}),
        )
        assert token == 'mock_webin_token'

    def test_get_webin_username_password_cmd_line(self):
        auth = WebinAuth(username='username', password='password')
        os.environ[ENA_WEBIN_ACCOUNT_VAR] = 'notusername'
        os.environ[ENA_WEBIN_PASSWORD_VAR] = 'notpassword'
        username, password = auth._get_webin_username_password()
        assert username == 'username'
        assert password == 'password'

    def test_get_webin_username_password_environ(self):
        os.environ[ENA_WEBIN_ACCOUNT_VAR] = 'username'
        os.environ[ENA_WEBIN_PASSWORD_VAR] = 'password'
        auth = WebinAuth()
        username, password = auth._get_webin_username_password()
        assert username == 'username'
        assert password == 'password'

    def test_get_webin_username_password_stdin(self):
        auth = WebinAuth()
        with patch("builtins.input", return_value="username"), \
             patch("eva_sub_cli.auth.getpass", return_value="password"):
            username, password = auth._get_webin_username_password()
        assert username == 'username'
        assert password == 'password'


class TestLSRIAuth(unittest.TestCase):

    def setUp(self):
        self.auth = LSRIAuth()

    @patch("eva_sub_cli.auth.requests.post")
    def test_auth_with_lsri_auth(self, mock_post):
        # Mock the response for OAuth device flow initiation
        mock_device_response = MagicMock()
        mock_device_response.status_code = 200
        mock_device_response.json.return_value = {"device_code": "device_code", "user_code": "user_code",
                                                "verification_uri": "verification_uri", "expires_in": 600}

        # Mock the response for post-authentication response from eva-submission-ws
        mock_auth_response = MagicMock()
        mock_auth_response.status_code = 200
        mock_auth_response.text = "mock_lsri_token"

        # Set the side_effect attribute to return different responses
        mock_post.side_effect = [mock_device_response, mock_auth_response]
        token = self.auth.token

        # Check if the device initiation flow was called with the correct parameters
        device_authorization_url = "https://login.elixir-czech.org/oidc/devicecode"
        mock_post.assert_any_call(device_authorization_url,
                                  data={'client_id': LSRI_CLIENT_ID, 'scope': 'openid'})

        # Check if the post-authentication call to eva-submission-ws was called with the correct parameters
        mock_post.assert_any_call(
            self.auth.auth_url, timeout=600 ,headers={'Accept': 'application/hal+json'},
            params={'deviceCode': 'device_code', 'expiresIn': 600}
        )
        # Check the total number of calls to requests.post
        assert mock_post.call_count == 2
        assert token == 'mock_lsri_token'
