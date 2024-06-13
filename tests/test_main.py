import csv
import os
import shutil
import unittest
from unittest.mock import patch, Mock

from ebi_eva_common_pyutils.config import WritableConfig
from requests import HTTPError

from eva_sub_cli import SUB_CLI_CONFIG_FILE
from eva_sub_cli.exceptions.submission_not_found_exception import SubmissionNotFoundException
from eva_sub_cli.exceptions.submission_status_exception import SubmissionStatusException
from eva_sub_cli.main import orchestrate_process, VALIDATE, SUBMIT, DOCKER, check_validation_required
from eva_sub_cli.submit import SUB_CLI_CONFIG_KEY_SUBMISSION_ID
from eva_sub_cli.validators.validator import READY_FOR_SUBMISSION_TO_EVA


class TestMain(unittest.TestCase):
    project_title = 'Example Project'
    resource_dir = os.path.join(os.path.dirname(__file__), 'resources')
    test_sub_dir = os.path.join(resource_dir, 'test_sub_dir')
    config_file = os.path.join(test_sub_dir, SUB_CLI_CONFIG_FILE)

    mapping_file = os.path.join(test_sub_dir, 'vcf_mapping_file.csv')
    vcf_files = [os.path.join(test_sub_dir, 'vcf_file1.vcf'), os.path.join(test_sub_dir, 'vcf_file2.vcf')]
    reference_fasta = os.path.join(test_sub_dir, 'genome.fa')
    metadata_json = os.path.join(test_sub_dir, 'sub_metadata.json')
    metadata_xlsx = os.path.join(test_sub_dir, 'sub_metadata.xlsx')

    def setUp(self) -> None:
        if os.path.exists(self.test_sub_dir):
            shutil.rmtree(self.test_sub_dir)
        os.makedirs(self.test_sub_dir)
        shutil.copy(os.path.join(self.resource_dir, 'EVA_Submission_test.json'), self.metadata_json)


    def tearDown(self) -> None:
        shutil.rmtree(self.test_sub_dir)

    def test_check_validation_required(self):
        tasks = ['submit']

        sub_config = {READY_FOR_SUBMISSION_TO_EVA: False}
        self.assertTrue(check_validation_required(tasks, sub_config))

        sub_config = {READY_FOR_SUBMISSION_TO_EVA: True}
        self.assertFalse(check_validation_required(tasks, sub_config))

        with patch('eva_sub_cli.submission_ws.SubmissionWSClient.get_submission_status') as get_submission_status_mock:
            sub_config = {READY_FOR_SUBMISSION_TO_EVA: True,
                          SUB_CLI_CONFIG_KEY_SUBMISSION_ID: 'test123'}

            get_submission_status_mock.return_value = 'OPEN'
            self.assertFalse(check_validation_required(tasks, sub_config))

            get_submission_status_mock.return_value = 'FAILED'
            self.assertTrue(check_validation_required(tasks, sub_config))

            mock_response = Mock()
            mock_response.status_code = 404
            get_submission_status_mock.side_effect = HTTPError(response=mock_response)
            with self.assertRaises(SubmissionNotFoundException):
                check_validation_required(tasks, sub_config)

            mock_response = Mock()
            mock_response.status_code = 500
            get_submission_status_mock.side_effect = HTTPError(response=mock_response)
            with self.assertRaises(SubmissionStatusException):
                check_validation_required(tasks, sub_config)

    def test_orchestrate_validate(self):
        with patch('eva_sub_cli.main.get_vcf_files') as m_get_vcf,  \
                patch('eva_sub_cli.main.WritableConfig') as m_config, \
                patch('eva_sub_cli.main.get_project_title_and_create_vcf_files_mapping') as m_get_project_title_and_create_vcf_files_mapping, \
                patch('eva_sub_cli.main.DockerValidator') as m_docker_validator:
            m_get_project_title_and_create_vcf_files_mapping.return_value = self.project_title, self.mapping_file
            orchestrate_process(self.test_sub_dir, None, None, self.metadata_json,
                                self.metadata_xlsx, tasks=[VALIDATE], executor=DOCKER)
            m_get_project_title_and_create_vcf_files_mapping.assert_called_once_with(self.test_sub_dir, None, None, self.metadata_json, self.metadata_xlsx)
            m_get_vcf.assert_called_once_with(self.mapping_file)
            m_docker_validator.assert_any_call(
                self.mapping_file, self.test_sub_dir, self.project_title, self.metadata_json, self.metadata_xlsx,
                submission_config=m_config.return_value
            )
            m_docker_validator().validate_and_report.assert_called_once_with()

    def test_orchestrate_validate_submit(self):
        with patch('eva_sub_cli.main.get_vcf_files') as m_get_vcf, \
                patch('eva_sub_cli.main.WritableConfig') as m_config, \
                patch('eva_sub_cli.main.get_project_title_and_create_vcf_files_mapping') as m_get_project_title_and_create_vcf_files_mapping, \
                patch('eva_sub_cli.main.DockerValidator') as m_docker_validator, \
                patch('eva_sub_cli.main.StudySubmitter') as m_submitter:
            # Empty config
            config = WritableConfig()
            m_config.return_value = config
            m_get_project_title_and_create_vcf_files_mapping.return_value = self.project_title, self.mapping_file

            orchestrate_process(self.test_sub_dir, None, None, self.metadata_json,
                                self.metadata_xlsx, tasks=[SUBMIT], executor=DOCKER)
            m_get_vcf.assert_called_once_with(self.mapping_file)
            # Validate was run because the config show it was not run successfully before
            m_docker_validator.assert_any_call(
                self.mapping_file, self.test_sub_dir, self.project_title, self.metadata_json, self.metadata_xlsx,
                submission_config=m_config.return_value
            )
            m_docker_validator().validate_and_report.assert_called_once_with()

            # Submit was created
            m_submitter.assert_any_call(self.test_sub_dir, submission_config=m_config.return_value,
                                        username=None, password=None)
            with m_submitter() as submitter:
                submitter.submit.assert_called_once_with()

    def test_orchestrate_submit_no_validate(self):
        with patch('eva_sub_cli.main.get_vcf_files') as m_get_vcf, \
                patch('eva_sub_cli.main.WritableConfig') as m_config, \
                patch('eva_sub_cli.main.get_project_title_and_create_vcf_files_mapping') as m_get_project_title_and_create_vcf_files_mapping, \
                patch('eva_sub_cli.main.DockerValidator') as m_docker_validator, \
                patch('eva_sub_cli.main.StudySubmitter') as m_submitter:
            # Empty config
            m_config.return_value = {READY_FOR_SUBMISSION_TO_EVA: True}
            m_get_project_title_and_create_vcf_files_mapping.return_value = self.project_title, self.mapping_file

            orchestrate_process(self.test_sub_dir, None, None, self.metadata_json,
                self.metadata_xlsx, tasks=[SUBMIT], executor=DOCKER)
            m_get_vcf.assert_called_once_with(self.mapping_file)
            # Validate was not run because the config showed it was run successfully before
            assert m_docker_validator.call_count == 0

            # Submit was created
            m_submitter.assert_any_call(self.test_sub_dir, submission_config=m_config.return_value,
                                        username=None, password=None)
            with m_submitter() as submitter:
                submitter.submit.assert_called_once_with()

    def test_orchestrate_with_vcf_files(self):
        with patch('eva_sub_cli.main.WritableConfig') as m_config, \
                patch('eva_sub_cli.main.DockerValidator') as m_docker_validator:
            orchestrate_process( self.test_sub_dir, self.vcf_files, self.reference_fasta, self.metadata_json,
                                 self.metadata_xlsx, tasks=[VALIDATE], executor=DOCKER)
            # Mapping file was created from the vcf and assembly files
            assert os.path.exists(self.mapping_file)
            with open(self.mapping_file) as open_file:
                reader = csv.DictReader(open_file, delimiter=',')
                for row in reader:
                    assert row['vcf'].__contains__('vcf_file')
                    assert row['report'] == None
            m_docker_validator.assert_any_call(
                self.mapping_file, self.test_sub_dir, self.project_title, self.metadata_json, self.metadata_xlsx,
                submission_config=m_config.return_value
            )
            m_docker_validator().validate_and_report.assert_called_once_with()


    def test_orchestrate_with_metadata_json_without_asm_report(self):
        with patch('eva_sub_cli.main.WritableConfig') as m_config, \
                patch('eva_sub_cli.main.DockerValidator') as m_docker_validator:
            orchestrate_process(self.test_sub_dir, None, None, self.metadata_json,
                                None, tasks=[VALIDATE], executor=DOCKER)
            # Mapping file was created from the metadata_json
            assert os.path.exists(self.mapping_file)
            with open(self.mapping_file) as open_file:
                reader = csv.DictReader(open_file, delimiter=',')
                for row in reader:
                    assert row['vcf'].__contains__('example')
                    assert row['report'] == ''
            m_docker_validator.assert_any_call(
                self.mapping_file, self.test_sub_dir, self.project_title, self.metadata_json, None,
                submission_config=m_config.return_value
            )
            m_docker_validator().validate_and_report.assert_called_once_with()

    def test_orchestrate_with_metadata_json_with_asm_report(self):
        shutil.copy(os.path.join(self.resource_dir, 'EVA_Submission_test_with_asm_report.json'), self.metadata_json)

        with patch('eva_sub_cli.main.WritableConfig') as m_config, \
                patch('eva_sub_cli.main.DockerValidator') as m_docker_validator:
            orchestrate_process(self.test_sub_dir, None, None, self.metadata_json, None,
                tasks=[VALIDATE], executor=DOCKER)
            # Mapping file was created from the metadata_json
            assert os.path.exists(self.mapping_file)
            with open(self.mapping_file) as open_file:
                reader = csv.DictReader(open_file, delimiter=',')
                for row in reader:
                    assert row['vcf'].__contains__('example')
                    assert row['report'].__contains__('GCA_000001405.27_report.txt')
            m_docker_validator.assert_any_call(
                self.mapping_file, self.test_sub_dir, self.project_title, self.metadata_json, None,
                submission_config=m_config.return_value
            )
            m_docker_validator().validate_and_report.assert_called_once_with()


    def test_orchestrate_vcf_files_takes_precedence_over_metadata(self):
        shutil.copy(os.path.join(self.resource_dir, 'EVA_Submission_test_with_asm_report.json'), self.metadata_json)

        with patch('eva_sub_cli.main.WritableConfig') as m_config, \
                patch('eva_sub_cli.main.DockerValidator') as m_docker_validator:
            orchestrate_process(self.test_sub_dir, self.vcf_files, self.reference_fasta, self.metadata_json,
                                None, tasks=[VALIDATE], executor=DOCKER, resume=False)
            # Mapping file was created from the metadata_json
            assert os.path.exists(self.mapping_file)
            with open(self.mapping_file) as open_file:
                reader = csv.DictReader(open_file, delimiter=',')
                for row in reader:
                    assert row['vcf'].__contains__('vcf_file')
                    assert row['report'] == None
            m_docker_validator.assert_any_call(
                self.mapping_file, self.test_sub_dir, self.project_title, self.metadata_json, None,
                submission_config=m_config.return_value
            )
            m_docker_validator().validate_and_report.assert_called_once_with()



    def test_orchestrate_with_metadata_xlsx(self):
        shutil.copy(os.path.join(self.resource_dir, 'EVA_Submission_test.xlsx'), self.metadata_xlsx)

        with patch('eva_sub_cli.main.WritableConfig') as m_config, \
                patch('eva_sub_cli.main.DockerValidator') as m_docker_validator:
            orchestrate_process(self.test_sub_dir, None, None, None, self.metadata_xlsx,
                tasks=[VALIDATE], executor=DOCKER)
            # Mapping file was created from the metadata_xlsx
            assert os.path.exists(self.mapping_file)
            with open(self.mapping_file) as open_file:
                reader = csv.DictReader(open_file, delimiter=',')
                for row in reader:
                    assert row['vcf'].__contains__('example')
                    assert row['report'] == ''
            m_docker_validator.assert_any_call(
                self.mapping_file, self.test_sub_dir, self.project_title, None, self.metadata_xlsx,
                submission_config=m_config.return_value
            )
            m_docker_validator().validate_and_report.assert_called_once_with()


    def test_metadata_file_does_not_exist_error(self):
        with self.assertRaises(Exception) as context:
            orchestrate_process(self.test_sub_dir, None, None, None, self.metadata_xlsx,
                    tasks=[VALIDATE], executor=DOCKER)
        self.assertRegex(str(context.exception),r"The provided metadata file .*/resources/test_sub_dir/sub_metadata.xlsx does not exist")


