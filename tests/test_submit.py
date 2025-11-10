import json
import os
import shutil
import unittest
from unittest.mock import MagicMock, patch, Mock

import yaml
from ebi_eva_common_pyutils.config import WritableConfig

from eva_sub_cli import SUB_CLI_CONFIG_FILE
from eva_sub_cli.file_utils import is_submission_dir_writable
from eva_sub_cli.submission_ws import SubmissionWSClient
from eva_sub_cli.validators.validator import READY_FOR_SUBMISSION_TO_EVA
from eva_sub_cli.submit import StudySubmitter, SUB_CLI_CONFIG_KEY_SUBMISSION_ID, \
    SUB_CLI_CONFIG_KEY_SUBMISSION_UPLOAD_URL


class TestSubmit(unittest.TestCase):
    resource_dir = os.path.join(os.path.dirname(__file__), 'resources')
    test_sub_dir = os.path.join(resource_dir, 'test_sub_dir')
    config_file = os.path.join(test_sub_dir, SUB_CLI_CONFIG_FILE)

    def setUp(self) -> None:
        self.token = 'a token'
        vcf_files = [os.path.join(self.resource_dir, 'vcf_files', 'example2.vcf.gz')]
        metadata_json_file = os.path.join(self.resource_dir, 'EVA_Submission_test.json')
        self.submitter = StudySubmitter(submission_dir=self.test_sub_dir)
        self.submitter.sub_config.set('metadata_json', value=metadata_json_file)
        self.submitter.sub_config.set('vcf_files', value=vcf_files)
        with open(metadata_json_file) as open_file:
            self.metadata_json = json.load(open_file)

        shutil.rmtree(self.test_sub_dir, ignore_errors=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.test_sub_dir, ignore_errors=True)

    def test_submit(self):
        # Mock the response for post-authentication response from eva-submission-ws
        mock_initiate_response = MagicMock()
        mock_initiate_response.status_code = 200
        mock_initiate_response.json.return_value = {"submissionId": "mock_submission_id",
                                                    "uploadUrl": "directory to use for upload"}

        mock_uploaded_response = MagicMock()
        mock_uploaded_response.status_code = 200

        test_submission_ws_client = SubmissionWSClient()

        with patch.object(test_submission_ws_client, 'auth') as mocked_auth:
            with patch.object(self.submitter, 'submission_ws_client', test_submission_ws_client), \
                    patch.object(test_submission_ws_client, 'get_submission_status', return_value='OPEN'), \
                    patch('eva_sub_cli.submission_ws.requests.post', return_value=mock_initiate_response) as mock_post, \
                    patch('eva_sub_cli.submission_ws.requests.put', return_value=mock_uploaded_response) as mock_put, \
                    patch.object(StudySubmitter, '_upload_submission'):
                mocked_auth.token = self.token
                self.submitter.sub_config.set(READY_FOR_SUBMISSION_TO_EVA, value=True)
                self.submitter.submit()

                mock_post.assert_called_once_with(
                    os.path.join(test_submission_ws_client.SUBMISSION_WS_URL, 'submission/initiate'),
                    headers={'Accept': 'application/json', 'Authorization': 'Bearer a token'})

                mock_put.assert_called_once_with(
                    os.path.join(test_submission_ws_client.SUBMISSION_WS_URL, 'submission/mock_submission_id/uploaded'),
                    headers={'Accept': 'application/json', 'Authorization': 'Bearer a token'},
                    json=self.metadata_json)

    def test_submit_with_config(self):
        mock_initiate_response = MagicMock()
        mock_initiate_response.status_code = 200
        mock_initiate_response.json.return_value = {
            "submissionId": "mock_submission_id",
            "uploadUrl": "directory to use for upload",
        }
        mock_uploaded_response = MagicMock()
        mock_uploaded_response.status_code = 200

        assert is_submission_dir_writable(self.test_sub_dir)
        assert not os.path.exists(self.config_file)
        sub_config = WritableConfig(self.config_file, version='version1.0')
        sub_config.set('metadata_json', value=os.path.join(self.resource_dir, 'EVA_Submission_test.json'))
        sub_config.set(READY_FOR_SUBMISSION_TO_EVA, value=True)
        sub_config.write()
        self.submitter = StudySubmitter(submission_dir=self.test_sub_dir, submission_config=sub_config)

        test_submission_ws_client = SubmissionWSClient()

        with patch.object(test_submission_ws_client, 'auth') as mocked_auth:
            with patch.object(self.submitter, 'submission_ws_client', test_submission_ws_client), \
                    patch.object(test_submission_ws_client, 'get_submission_status', return_value='OPEN'), \
                    patch('eva_sub_cli.submission_ws.requests.post', return_value=mock_initiate_response) as mock_post, \
                    patch('eva_sub_cli.submission_ws.requests.put', return_value=mock_uploaded_response) as mock_put, \
                    patch.object(StudySubmitter, '_upload_submission'):
                mocked_auth.token = self.token
                with self.submitter as submitter:
                    submitter.submit()

        assert os.path.exists(self.test_sub_dir)
        assert os.path.exists(self.config_file)
        # assert backup file is created
        assert os.path.exists(f"{self.config_file}.1")
        with open(self.config_file, 'r') as f:
            sub_config_data = yaml.safe_load(f)
            assert sub_config_data[SUB_CLI_CONFIG_KEY_SUBMISSION_ID] == "mock_submission_id"
            assert sub_config_data[SUB_CLI_CONFIG_KEY_SUBMISSION_UPLOAD_URL] == "directory to use for upload"

    def test_submit_when_already_completed(self):
        test_submission_ws_client = SubmissionWSClient()

        with patch.object(self.submitter, 'submission_ws_client', test_submission_ws_client), \
                patch.object(test_submission_ws_client, 'get_submission_status', return_value='UPLOADED') as mock_get_submission_status, \
                patch.object(self.submitter, '_initiate_submission') as mock_initiate, \
                patch.object(self.submitter, '_upload_submission') as mock_upload, \
                patch.object(self.submitter, '_complete_submission') as mock_complete, \
                patch.object(self.submitter, 'warning') as mock_warning:

            self.submitter.sub_config.set(READY_FOR_SUBMISSION_TO_EVA, value=True)
            self.submitter.sub_config.set(SUB_CLI_CONFIG_KEY_SUBMISSION_UPLOAD_URL, value='directory to use for upload')
            self.submitter.submit()
            # No call was made to the end point or the upload because the submission status is 'UPLOADED'
            mock_initiate.assert_not_called()
            mock_upload.assert_not_called()
            mock_complete.assert_not_called()
            mock_warning.assert_called_once_with(
                f'You requested the submission using {self.test_sub_dir}. This directory contains an already completed '
                f'submission. Please create a new submission directory to resubmit.')

    def test_sub_config_file_creation(self):
        assert is_submission_dir_writable(self.test_sub_dir)
        self.submitter.sub_config.set('test_key', value='test_value')
        self.submitter.sub_config.write()

        assert os.path.exists(self.config_file)
        assert self.submitter.sub_config['test_key'] == 'test_value'

    def test_sub_config_passed_as_param(self):
        assert is_submission_dir_writable(self.test_sub_dir)
        sub_config = WritableConfig(self.config_file)
        with StudySubmitter(self.test_sub_dir, submission_config=sub_config) as submitter:
            submitter.sub_config.set('test_key', value='test_value')

        assert os.path.exists(self.config_file)
        assert submitter.sub_config['test_key'] == 'test_value'

    def test_upload_submission(self):
        mock_submit_response = MagicMock()
        mock_submit_response.status_code = 200
        test_url = 'http://example.com/'
        with patch.object(StudySubmitter, '_upload_file') as mock_upload_file:
            self.submitter.sub_config.set(READY_FOR_SUBMISSION_TO_EVA, value=True)
            self.submitter.sub_config.set(SUB_CLI_CONFIG_KEY_SUBMISSION_UPLOAD_URL, value=test_url)
            self.submitter._upload_submission()
        for vcf_file in self.submitter.vcf_files:
            mock_upload_file.assert_any_call(test_url, vcf_file)

        mock_upload_file.assert_any_call(test_url, self.submitter.metadata_json_file)

    def test_upload_file(self):
        test_url = 'http://example.com/'
        with patch('eva_sub_cli.submit.requests.put') as mock_put:
            file_to_upload = os.path.join(self.resource_dir, 'EVA_Submission_test.json')
            self.submitter._upload_file(submission_upload_url=test_url, input_file=file_to_upload)
            assert mock_put.mock_calls[0][1][0] == test_url + os.path.basename(file_to_upload)
            # Cannot test the content of the upload as opening the same file twice give different object
