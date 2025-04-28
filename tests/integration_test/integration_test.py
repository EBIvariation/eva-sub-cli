import logging
import os
import shutil
from unittest import TestCase

from ebi_eva_common_pyutils.command_utils import run_command_with_output
from ebi_eva_common_pyutils.logger import logging_config

logger = logging_config.get_logger(__name__)

eva_sub_cli_container_image = 'eva_sub_cli'
eva_sub_cli_container_tag = 'test-latest'


class IntegrationTest(TestCase):
    docker_path = 'docker'
    integration_test_dir = os.path.join(os.path.dirname(__file__))
    docker_compose_file = os.path.join(integration_test_dir, "docker-compose.yml")

    integration_test_run_dir = os.path.join(integration_test_dir, "test_run")

    expected_component_images_and_tags = [
        {
            'image': eva_sub_cli_container_image,
            'tag': eva_sub_cli_container_tag
        }
    ]

    def setUp(self):
        self.build_docker_components_for_testing()

    def tearDown(self):
        for d in [self.integration_test_run_dir]:
            if os.path.exists(d):
                shutil.rmtree(d)

    def build_docker_components_for_testing(self):
        # remove existing component images build previously
        self.remove_existing_component_images()

        # build fresh component images using docker compose
        self._run_quiet_command(
            "build docker components using docker compose file",
            f"{self.docker_path} compose -f {self.docker_compose_file} build"
        )

        # verify all the images are build successfully
        self.verify_all_components_created_successfully()

    @staticmethod
    def _run_quiet_command(command_description, command, **kwargs):
        return run_command_with_output(command_description, command, stdout_log_level=logging.DEBUG,
                                       stderr_log_level=logging.DEBUG, **kwargs)

    def remove_existing_component_images(self):
        # remove component images build previously
        for expected in self.expected_component_images_and_tags:
            self._run_quiet_command(
                "remove existing component image",
                f"{self.docker_path} rmi {expected['image']}:{expected['tag']} || true"
            )

    def verify_all_components_created_successfully(self):
        container_images_cmd_ouptut = self._run_quiet_command(
            "list docker images",
            f"{self.docker_path} images",
            return_process_output=True
        )

        # Assert each expected image:tag is found in docker images cmd output
        for expected in self.expected_component_images_and_tags:
            image = expected['image']
            tag = expected['tag']
            # check if both image and tag appear together in a line
            found = any(
                image in line and tag in line
                for line in container_images_cmd_ouptut.splitlines()
            )

            assert found, f"Expected image '{image}:{tag}' not found in docker images output."

    def test_everything_setup_successfully(self):
        pass
