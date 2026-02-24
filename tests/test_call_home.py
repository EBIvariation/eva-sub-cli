import json
import os
import shutil
import time
import uuid
from unittest import TestCase
from unittest.mock import patch

import jsonschema

from ebi_eva_common_pyutils.config import Configuration, WritableConfig
from requests.exceptions import ConnectionError, Timeout

from eva_sub_cli import SUB_CLI_CONFIG_FILE, ROOT_DIR
from eva_sub_cli.call_home import _get_or_create_deployment_id, _get_or_create_run_id, \
    CallHomeClient, EVENT_START, EVENT_FAILURE, EVENT_END
from tests.test_report import common_validation_results


class TestDeploymentId(TestCase):

    resources_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources')

    def setUp(self):
        self.config_dir = os.path.join(self.resources_dir, '.eva-sub-cli')
        self.deployment_file = os.path.join(self.config_dir, 'deployment_id')

    def tearDown(self):
        if os.path.exists(self.config_dir):(
            shutil.rmtree(self.config_dir))

    def test_creates_new_id_when_file_missing(self):
        with patch('eva_sub_cli.call_home.DEPLOYMENT_ID_DIR', self.config_dir), \
                patch('eva_sub_cli.call_home.DEPLOYMENT_ID_FILE', self.deployment_file):
            deployment_id = _get_or_create_deployment_id()
            # Should be a valid UUID
            uuid.UUID(deployment_id)
            # File should have been created
            self.assertTrue(os.path.isfile(self.deployment_file))
            with open(self.deployment_file) as f:
                self.assertEqual(f.read().strip(), deployment_id)

    def test_reads_existing_id(self):
        os.makedirs(self.config_dir, exist_ok=True)
        existing_id = str(uuid.uuid4())
        with open(self.deployment_file, 'w') as f:
            f.write(existing_id)

        with patch('eva_sub_cli.call_home.DEPLOYMENT_ID_DIR', self.config_dir), \
                patch('eva_sub_cli.call_home.DEPLOYMENT_ID_FILE', self.deployment_file):
            deployment_id = _get_or_create_deployment_id()
            self.assertEqual(deployment_id, existing_id)

    def test_handles_permission_error(self):
        with patch('eva_sub_cli.call_home.DEPLOYMENT_ID_DIR', '/nonexistent/path'), \
                patch('eva_sub_cli.call_home.DEPLOYMENT_ID_FILE', '/nonexistent/path/deployment_id'):
            deployment_id = _get_or_create_deployment_id()
            # Should return a transient UUID without raising
            uuid.UUID(deployment_id)

    def test_regenerates_on_empty_file(self):
        os.makedirs(self.config_dir, exist_ok=True)
        with open(self.deployment_file, 'w') as f:
            f.write('')

        with patch('eva_sub_cli.call_home.DEPLOYMENT_ID_DIR', self.config_dir), \
                patch('eva_sub_cli.call_home.DEPLOYMENT_ID_FILE', self.deployment_file):
            deployment_id = _get_or_create_deployment_id()
            uuid.UUID(deployment_id)
            with open(self.deployment_file) as f:
                self.assertEqual(f.read().strip(), deployment_id)


class TestRunId(TestCase):

    resources_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources')

    def setUp(self):
        self.submission_dir = os.path.join(self.resources_dir, 'submission_dir')
        os.makedirs(self.submission_dir, exist_ok=True)

    def tearDown(self):
        if os.path.exists(self.submission_dir):
            shutil.rmtree(self.submission_dir)

    def test_creates_new_id_when_config_has_no_run_id(self):
        run_id = _get_or_create_run_id(self.submission_dir)
        uuid.UUID(run_id)
        # Verify it was written to config
        config_path = os.path.join(self.submission_dir, SUB_CLI_CONFIG_FILE)
        self.assertTrue(os.path.isfile(config_path))
        config = Configuration(config_path)
        self.assertEqual(config.query('run_id'), run_id)

    def test_reads_existing_id_from_config(self):
        existing_id = str(uuid.uuid4())
        # Create config with an existing run_id
        config_path = os.path.join(self.submission_dir, SUB_CLI_CONFIG_FILE)
        config = WritableConfig(config_path)
        config.set('run_id', value=existing_id)
        config.write()

        run_id = _get_or_create_run_id(self.submission_dir)
        self.assertEqual(run_id, existing_id)

    def test_handles_unreadable_config(self):
        with patch('eva_sub_cli.call_home.WritableConfig', side_effect=Exception('Cannot read config')):
            run_id = _get_or_create_run_id(self.submission_dir)
            uuid.UUID(run_id)


class TestCallHomeClient(TestCase):

    resources_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources')

    def setUp(self):
        self.submission_dir = os.path.join(self.resources_dir, 'submission_dir')
        os.makedirs(self.submission_dir, exist_ok=True)

    def tearDown(self):
        if os.path.exists(self.submission_dir):
            shutil.rmtree(self.submission_dir)

    @patch('eva_sub_cli.call_home._get_or_create_run_id', return_value='test-run-id')
    @patch('eva_sub_cli.call_home._get_or_create_deployment_id', return_value='test-deployment-id')
    def _create_client(self, mock_dep_id, mock_run_id):
        return CallHomeClient(
            submission_dir=self.submission_dir,
            executor='native',
            tasks=['validate', 'submit']
        )

    def test_build_payload(self):
        client = self._create_client()
        payload = client._build_payload(EVENT_START)
        self.assertEqual(payload['runtimeSeconds'], 0)
        self.assertEqual(payload['eventType'], EVENT_START)
        self.assertEqual(payload['deploymentId'], 'test-deployment-id')
        self.assertEqual(payload['runId'], 'test-run-id')
        self.assertEqual(payload['executor'], 'native')
        self.assertEqual(payload['tasks'], ['validate', 'submit'])
        self.assertIn('cliVersion', payload)
        self.assertIn('createdAt', payload)

    def test_non_zero_runtime_on_non_start(self):
        client = self._create_client()
        time.sleep(1)
        payload = client._build_payload(EVENT_END)
        self.assertNotEqual(payload['runtimeSeconds'], 0)
        self.assertEqual(payload['eventType'], EVENT_END)

    @patch('eva_sub_cli.call_home.requests.post', side_effect=ConnectionError('connection refused'))
    def test_connection_error_swallowed(self, mock_post):
        client = self._create_client()
        # Should not raise
        client.send_start()

    @patch('eva_sub_cli.call_home.requests.post', side_effect=Timeout('timed out'))
    def test_timeout_swallowed(self, mock_post):
        client = self._create_client()
        client.send_end()

    @patch('eva_sub_cli.call_home.requests.post', side_effect=Exception('unexpected error'))
    def test_generic_exception_swallowed(self, mock_post):
        client = self._create_client()
        client.send_failure()

    @patch('eva_sub_cli.call_home.requests.post')
    def test_send_all_event_types(self, mock_post):
        schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   '..', 'eva_sub_cli', 'etc', 'call_home_payload_schema.json')
        with open(schema_path) as f:
            schema = json.load(f)

        client = self._create_client()
        client.send_start()
        client.send_validation_completed({'Results': common_validation_results})
        client.send_end()
        self.assertEqual(mock_post.call_count, 3)

        for call in mock_post.call_args_list:
            payload = call.kwargs['json']
            jsonschema.validate(instance=payload, schema=schema)


    @patch('eva_sub_cli.call_home.requests.post')
    def test_send_failure_event(self, mock_post):
        client = self._create_client()
        client.send_failure()
        payload = mock_post.call_args.kwargs['json']
        self.assertEqual(payload['eventType'], EVENT_FAILURE)
        self.assertNotIn('exceptionMessage', payload)
        self.assertNotIn('exceptionStacktrace', payload)

    @patch('eva_sub_cli.call_home.requests.post')
    def test_send_failure_with_exception(self, mock_post):
        client = self._create_client()
        try:
            raise ValueError('something went wrong')
        except ValueError as e:
            client.send_failure(exception=e)
        payload = mock_post.call_args.kwargs['json']
        self.assertEqual(payload['eventType'], EVENT_FAILURE)
        self.assertEqual(payload['exceptionMessage'], 'something went wrong')
        self.assertIn('ValueError', payload['exceptionStacktrace'])
        self.assertIn('something went wrong', payload['exceptionStacktrace'])
        self.assertNotIn(ROOT_DIR, payload['exceptionStacktrace'])
