import json
import os
import shutil
import unittest
from unittest.mock import MagicMock, patch, Mock

import yaml
from ebi_eva_common_pyutils.config import WritableConfig

from eva_sub_cli.eva_sub_cli import SUB_CLI_CONFIG_FILE
from eva_sub_cli.reporter import READY_FOR_SUBMISSION_TO_EVA
from eva_sub_cli.submit import StudySubmitter, SUB_CLI_CONFIG_KEY_SUBMISSION_ID, SUB_CLI_CONFIG_KEY_SUBMISSION_UPLOAD_URL


class TestSubmit(unittest.TestCase):
    resource_dir = os.path.join(os.path.dirname(__file__), 'resources')
    test_sub_dir = os.path.join(resource_dir, 'test_sub_dir')
    config_file = os.path.join(test_sub_dir, SUB_CLI_CONFIG_FILE)

    def setUp(self) -> None:
        self.token = 'a token'
        with patch('eva_sub_cli.submit.get_auth', return_value=Mock(token=self.token)):
            vcf_files = [os.path.join(self.resource_dir, 'vcf_files', 'example2.vcf.gz')]
            metadata_file = os.path.join(self.resource_dir, 'EVA_Submission_template.V1.1.4.xlsx')
            self.submitter = StudySubmitter(submission_dir=self.test_sub_dir, vcf_files=vcf_files,
                                            metadata_file=metadata_file)

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
        with patch('eva_sub_cli.submit.requests.post', return_value=mock_submit_response) as mock_post, \
                patch.object(StudySubmitter, 'upload_submission'), \
                patch.object(StudySubmitter, 'verify_submission_dir'), \
                patch.object(StudySubmitter, 'update_config_with_submission_id_and_upload_url'), \
                patch.object(self.submitter, 'sub_config', {READY_FOR_SUBMISSION_TO_EVA: True}), \
                patch.object(self.submitter, 'submission_dir', self.test_sub_dir):
            self.submitter.submit()
        mock_post.assert_called_once_with('http://www.ebi.ac.uk/eva/v1/submission/initiate',
                                          headers={'Accept': 'application/hal+json', 'Authorization': 'Bearer a token'})

    def test_submit_with_config(self):
        mock_submit_response = MagicMock()
        mock_submit_response.status_code = 200
        mock_submit_response.json.return_value = {
            "submissionId": "mock_submission_id",
            "uploadUrl": "directory to use for upload",
        }

        self.submitter.verify_submission_dir(self.test_sub_dir)
        sub_config = WritableConfig(self.config_file, version='version1.0')
        sub_config.set(READY_FOR_SUBMISSION_TO_EVA, value=True)
        sub_config.write()

        with patch('eva_sub_cli.submit.requests.post', return_value=mock_submit_response) as mock_post, \
                patch.object(StudySubmitter, 'upload_submission'):
            with self.submitter as submitter:
                submitter.submit()

        assert os.path.exists(self.test_sub_dir)
        assert os.path.exists(self.config_file)
        # assert backup file is created
        assert os.path.exists(f"{self.config_file}.1")
        with (open(self.config_file, 'r') as f):
            sub_config_data = yaml.safe_load(f)
            assert sub_config_data[SUB_CLI_CONFIG_KEY_SUBMISSION_ID] == "mock_submission_id"
            assert sub_config_data[SUB_CLI_CONFIG_KEY_SUBMISSION_UPLOAD_URL] == "directory to use for upload"

    def test_verify_submission_dir(self):
        self.submitter.verify_submission_dir(self.test_sub_dir)
        assert os.path.exists(self.test_sub_dir)

    def test_sub_config_file_creation(self):
        self.submitter.verify_submission_dir(self.test_sub_dir)
        self.submitter.sub_config.set('test_key', value='test_value')
        self.submitter.sub_config.write()

        assert os.path.exists(self.config_file)
        assert self.submitter.sub_config['test_key'] == 'test_value'

    def test_sub_config_passed_as_param(self):
        with patch('eva_sub_cli.submit.get_auth', return_value=Mock(token=self.token)):
            sub_config = WritableConfig(self.config_file)
            with StudySubmitter(self.test_sub_dir, vcf_files=None, metadata_file=None, submission_config=sub_config) as submitter:
                submitter.verify_submission_dir(self.test_sub_dir)
                submitter.sub_config.set('test_key', value='test_value')

            assert os.path.exists(self.config_file)
            assert submitter.sub_config['test_key'] == 'test_value'

    def test_upload_submission(self):
        mock_submit_response = MagicMock()
        mock_submit_response.status_code = 200
        test_url = 'http://example.com/'
        with patch.object(StudySubmitter, 'upload_file') as mock_upload_file, \
            patch.object(self.submitter, 'sub_config', {READY_FOR_SUBMISSION_TO_EVA: True}):

            self.submitter.upload_submission(submission_upload_url=test_url)
        for vcf_file in self.submitter.vcf_files:
            mock_upload_file.assert_any_call(test_url, vcf_file)
        mock_upload_file.assert_called_with(test_url, self.submitter.metadata_file)

    def test_upload_file(self):
        test_url = 'http://example.com/'
        with patch('eva_sub_cli.submit.requests.put') as mock_put:
            file_to_upload = os.path.join(self.resource_dir, 'EVA_Submission_template.V1.1.4.xlsx')
            self.submitter.upload_file(submission_upload_url=test_url, input_file=file_to_upload)
            assert mock_put.mock_calls[0][1][0] == test_url + os.path.basename(file_to_upload)
            # Cannot test the content of the upload as opening the same file twice give different object
