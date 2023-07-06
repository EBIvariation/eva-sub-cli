import requests


class LSRIAuth:
    def __init__(self, client_id, device_authorization_url, submission_initiation_url):
        self.client_id = client_id
        self.device_authorization_url = device_authorization_url
        self.submission_initiation_url = submission_initiation_url

    def get_auth_response(self):
        # Step 1: Get device code using device auth url
        payload = {
            'client_id': self.client_id,
            'scope': 'openid'
        }
        response = requests.post(self.device_authorization_url, data=payload)
        response_json = response.json()

        device_code = response_json['device_code']
        user_code = response_json['user_code']
        verification_uri = response_json['verification_uri']
        expires_in = response_json['expires_in']

        # Display the user code and verification URI to the user
        print(f'Please visit {verification_uri} and enter this user code: {user_code}')
        # Delegate subsequent post-authentication processing (which requires LSRI client secret) to eva-submission-ws
        # so that we can avoid storing that client secret in eva-sub-cli
        return requests.post(self.submission_initiation_url,
                             headers={'Accept': 'application/hal+json'},
                             params={"deviceCode": device_code, "expiresIn": expires_in})
