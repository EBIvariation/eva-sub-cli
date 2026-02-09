import logging
import os
import traceback
import uuid
from datetime import datetime, timezone

import requests
from ebi_eva_common_pyutils.config import WritableConfig

from eva_sub_cli import __version__, SUBMISSION_WS_VAR, SUB_CLI_CONFIG_FILE
from eva_sub_cli.submission_ws import DEFAULT_SUBMISSION_WS_URL

logger = logging.getLogger(__name__)

CALL_HOME_PATH = 'call-home'
DEPLOYMENT_ID_DIR = os.path.join(os.path.expanduser('~'), '.eva-sub-cli')
DEPLOYMENT_ID_FILE = os.path.join(DEPLOYMENT_ID_DIR, 'deployment_id')

EVENT_START = 'START'
EVENT_VALIDATION_COMPLETED = 'VALIDATION_COMPLETED'
EVENT_END = 'END'
EVENT_FAILURE = 'FAILURE'


def _get_call_home_url():
    base_url = os.environ.get(SUBMISSION_WS_VAR) or DEFAULT_SUBMISSION_WS_URL
    return os.path.join(base_url, CALL_HOME_PATH)


def _get_or_create_deployment_id():
    try:
        if os.path.isfile(DEPLOYMENT_ID_FILE):
            with open(DEPLOYMENT_ID_FILE, 'r') as f:
                deployment_id = f.read().strip()
            if deployment_id:
                return deployment_id
        deployment_id = str(uuid.uuid4())
        os.makedirs(DEPLOYMENT_ID_DIR, exist_ok=True)
        with open(DEPLOYMENT_ID_FILE, 'w') as f:
            f.write(deployment_id)
        return deployment_id
    except Exception:
        logger.debug('Failed to read or create deployment ID file, using transient ID')
        return str(uuid.uuid4())


def _get_or_create_run_id(submission_dir):
    try:
        config_path = os.path.join(submission_dir, SUB_CLI_CONFIG_FILE)
        config = WritableConfig(config_path)
        run_id = config.get('run_id')
        if run_id:
            return str(run_id)
        run_id = str(uuid.uuid4())
        config.set('run_id', value=run_id)
        config.write()
        return run_id
    except Exception:
        logger.debug('Failed to read or create run ID in config, using transient ID')
        return str(uuid.uuid4())


class CallHomeClient:

    def __init__(self, submission_dir, executor, tasks):
        self.start_time = datetime.now(timezone.utc)
        self.deployment_id = _get_or_create_deployment_id()
        self.run_id = _get_or_create_run_id(submission_dir)
        self.executor = executor
        self.tasks = tasks

    def _build_payload(self, event_type, **kwargs):
        if event_type == EVENT_START:
            runtime_seconds = 0
        else:
            elapsed = datetime.now(timezone.utc) - self.start_time
            runtime_seconds = int(elapsed.total_seconds())
        payload = {
            'deploymentId': self.deployment_id,
            'runId': self.run_id,
            'eventType': event_type,
            'cliVersion': __version__,
            'createdAt': datetime.now(timezone.utc).isoformat(),
            'runtimeSeconds': runtime_seconds,
            'executor': self.executor,
            'tasks': self.tasks,
        }
        if kwargs:
            payload.update(kwargs)
        return payload

    def _send_event(self, event_type, **kwargs):
        try:
            payload = self._build_payload(event_type, **kwargs)
            requests.post(_get_call_home_url(), json=payload, timeout=5)
        except Exception:
            logger.debug('Failed to send %s call-home event', event_type)

    def send_start(self):
        self._send_event(EVENT_START)

    def send_validation_completed(self, validation_result):
        self._send_event(EVENT_VALIDATION_COMPLETED, validation_result=validation_result)

    def send_end(self):
        self._send_event(EVENT_END)

    def send_failure(self, exception=None):
        kwargs = {}
        if exception is not None:
            kwargs['exceptionMessage'] = str(exception)
            kwargs['exceptionStacktrace'] = ''.join(
                traceback.format_exception(type(exception), exception, exception.__traceback__)
            )
        self._send_event(EVENT_FAILURE, **kwargs)
