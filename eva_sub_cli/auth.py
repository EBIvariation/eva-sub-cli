import json
from functools import cached_property
from getpass import getpass

import requests
from ebi_eva_common_pyutils.logger import AppLogger
from urllib3.exceptions import ResponseError

from eva_sub_cli import LSRI_CLIENT_ID

ENA_AUTH_URL = "https://www.ebi.ac.uk/ena/submit/webin/auth/token",
LSRI_AUTH_URL = "http://www.ebi.ac.uk/eva/v1/submission/auth/lsri"
DEVICE_AUTHORISATION_URL ="https://login.elixir-czech.org/oidc/devicecode"


class LSRIAuth(AppLogger):
    def __init__(self, client_id=LSRI_CLIENT_ID, device_authorization_url=DEVICE_AUTHORISATION_URL, auth_url=LSRI_AUTH_URL):
        self.client_id = client_id
        self.device_authorization_url = device_authorization_url
        self.auth_url = auth_url

    @cached_property
    def token(self):
        # Step 1: Get device code using device auth url
        payload = {
            'client_id': self.client_id,
            'scope': 'openid'
        }
        response = requests.post(self.device_authorization_url, data=payload)
        response.raise_for_status()

        response_json = response.json()
        device_code = response_json['device_code']
        user_code = response_json['user_code']
        verification_uri = response_json['verification_uri']
        expires_in = response_json['expires_in']

        # Display the user code and verification URI to the user
        print(f'Please visit {verification_uri} and enter this user code: {user_code}')
        # Delegate subsequent post-authentication processing (which requires LSRI client secret) to eva-submission-ws
        # so that we can avoid storing that client secret in eva-sub-eva_sub_cli
        response = requests.post(self.auth_url, timeout=expires_in,
                                 headers={'Accept': 'application/hal+json'},
                                 params={"deviceCode": device_code, "expiresIn": expires_in})
        if response.status_code == 200:
            self.info("LSRI authentication successful!")
            return response.text
        else:
            raise ResponseError('LSRI Authentication Error')


class WebinAuth(AppLogger):

    def __init__(self, ena_auth_url=ENA_AUTH_URL):
        self.ena_auth_url = ena_auth_url

    @cached_property
    def token(self):
        self.info("Proceeding with ENA Webin authentication...")
        username, password = self._get_webin_username_password()
        headers = {"accept": "*/*", "Content-Type": "application/json"}
        data = {"authRealms": ["ENA"], "username": username, "password": password}
        response = requests.post(self.ena_auth_url, headers=headers, data=json.dumps(data))

        if response.status_code == 200:
            self.info("Webin authentication successful!")
            return response.text
        else:
            raise ResponseError('Webin Authentication Error')

    def _get_webin_username_password(self):
        username = input("Enter your ENA Webin username: ")
        password = getpass("Enter your ENA Webin password: ")
        return username, password


# Global auth for the session
auth = None


def get_auth():
    global auth
    if auth:
        return auth
    print("Choose an authentication method:")
    print("1. ENA Webin")
    print("2. LSRI")

    choice = int(input("Enter the number corresponding to your choice: "))

    if choice == 1:
        auth = WebinAuth()
    elif choice == 2:
        auth = LSRIAuth()
    else:
        print("Invalid choice! Try again!")
        get_auth()
    return auth
