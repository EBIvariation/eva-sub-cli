import csv
import os
import shutil
import unittest
from unittest.mock import patch

from ebi_eva_common_pyutils.config import WritableConfig

from eva_sub_cli import SUB_CLI_CONFIG_FILE
from eva_sub_cli.main import orchestrate_process, VALIDATE, SUBMIT, DOCKER
from eva_sub_cli.validators.validator import READY_FOR_SUBMISSION_TO_EVA


class TestMain(unittest.TestCase):
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

    def test_orchestrate_validate(self):
        with patch('eva_sub_cli.main.get_vcf_files') as m_get_vcf,  \
                patch('eva_sub_cli.main.WritableConfig') as m_config, \
                patch('eva_sub_cli.main.create_vcf_files_mapping') as m_create_mapping_file, \
                patch('eva_sub_cli.main.DockerValidator') as m_docker_validator:
            m_create_mapping_file.return_value = self.mapping_file
            orchestrate_process(
                self.test_sub_dir, None, None, self.metadata_json, self.metadata_xlsx,
                tasks=[VALIDATE], executor=DOCKER, resume=False
            )
            m_create_mapping_file.assert_called_once_with(self.test_sub_dir, None, None, self.metadata_json, self.metadata_xlsx)
            m_get_vcf.assert_called_once_with(self.mapping_file)
            m_docker_validator.assert_any_call(
                self.mapping_file, self.test_sub_dir, self.metadata_json, self.metadata_xlsx,
                submission_config=m_config.return_value
            )
            m_docker_validator().validate_and_report.assert_called_once_with()

    def test_orchestrate_validate_submit(self):
        with patch('eva_sub_cli.main.get_vcf_files') as m_get_vcf, \
                patch('eva_sub_cli.main.WritableConfig') as m_config, \
                patch('eva_sub_cli.main.create_vcf_files_mapping') as m_create_mapping_file, \
                patch('eva_sub_cli.main.DockerValidator') as m_docker_validator, \
                patch('eva_sub_cli.main.StudySubmitter') as m_submitter:
            # Empty config
            config = WritableConfig()
            m_config.return_value = config
            m_create_mapping_file.return_value = self.mapping_file

            orchestrate_process(
                self.test_sub_dir, None, None, self.metadata_json, self.metadata_xlsx,
                tasks=[SUBMIT], executor=DOCKER, resume=False
            )
            m_get_vcf.assert_called_once_with(self.mapping_file)
            # Validate was run because the config show it was not run successfully before
            m_docker_validator.assert_any_call(
                self.mapping_file, self.test_sub_dir, self.metadata_json, self.metadata_xlsx,
                submission_config=m_config.return_value
            )
            m_docker_validator().validate_and_report.assert_called_once_with()

            # Submit was created
            m_submitter.assert_any_call(self.test_sub_dir, submission_config=m_config.return_value,
                                        username=None, password=None)
            with m_submitter() as submitter:
                submitter.submit.assert_called_once_with(resume=False)

    def test_orchestrate_submit_no_validate(self):
        with patch('eva_sub_cli.main.get_vcf_files') as m_get_vcf, \
                patch('eva_sub_cli.main.WritableConfig') as m_config, \
                patch('eva_sub_cli.main.create_vcf_files_mapping') as m_create_mapping_file, \
                patch('eva_sub_cli.main.DockerValidator') as m_docker_validator, \
                patch('eva_sub_cli.main.StudySubmitter') as m_submitter:
            # Empty config
            m_config.return_value = {READY_FOR_SUBMISSION_TO_EVA: True}
            m_create_mapping_file.return_value = self.mapping_file

            orchestrate_process(
                self.test_sub_dir, None, None, self.metadata_json, self.metadata_xlsx,
                tasks=[SUBMIT], executor=DOCKER, resume=False
            )
            m_get_vcf.assert_called_once_with(self.mapping_file)
            # Validate was not run because the config showed it was run successfully before
            assert m_docker_validator.call_count == 0

            # Submit was created
            m_submitter.assert_any_call(self.test_sub_dir, submission_config=m_config.return_value,
                                        username=None, password=None)
            with m_submitter() as submitter:
                submitter.submit.assert_called_once_with(resume=False)

    def test_orchestrate_with_vcf_files(self):
        with patch('eva_sub_cli.main.WritableConfig') as m_config, \
                patch('eva_sub_cli.main.DockerValidator') as m_docker_validator:
            orchestrate_process(
                self.test_sub_dir, self.vcf_files, self.reference_fasta, self.metadata_json, self.metadata_xlsx,
                tasks=[VALIDATE], executor=DOCKER, resume=False
            )
            # Mapping file was created from the vcf and assembly files
            assert os.path.exists(self.mapping_file)
            with open(self.mapping_file) as open_file:
                reader = csv.DictReader(open_file, delimiter=',')
                for row in reader:
                    assert row['vcf'].__contains__('vcf_file')
                    assert row['report'] == None
            m_docker_validator.assert_any_call(
                self.mapping_file, self.test_sub_dir, self.metadata_json, self.metadata_xlsx,
                submission_config=m_config.return_value
            )
            m_docker_validator().validate_and_report.assert_called_once_with()


    def test_orchestrate_with_metadata_json_without_asm_report(self):
        with patch('eva_sub_cli.main.WritableConfig') as m_config, \
                patch('eva_sub_cli.main.DockerValidator') as m_docker_validator:
            orchestrate_process(
                self.test_sub_dir, None, None, self.metadata_json, None,
                tasks=[VALIDATE], executor=DOCKER, resume=False
            )
            # Mapping file was created from the metadata_json
            assert os.path.exists(self.mapping_file)
            with open(self.mapping_file) as open_file:
                reader = csv.DictReader(open_file, delimiter=',')
                for row in reader:
                    assert row['vcf'].__contains__('example')
                    assert row['report'] == ''
            m_docker_validator.assert_any_call(
                self.mapping_file, self.test_sub_dir, self.metadata_json, None,
                submission_config=m_config.return_value
            )
            m_docker_validator().validate_and_report.assert_called_once_with()

    def test_orchestrate_with_metadata_json_with_asm_report(self):
        shutil.copy(os.path.join(self.resource_dir, 'EVA_Submission_test_with_asm_report.json'), self.metadata_json)

        with patch('eva_sub_cli.main.WritableConfig') as m_config, \
                patch('eva_sub_cli.main.DockerValidator') as m_docker_validator:
            orchestrate_process(
                self.test_sub_dir, None, None, self.metadata_json, None,
                tasks=[VALIDATE], executor=DOCKER, resume=False
            )
            # Mapping file was created from the metadata_json
            assert os.path.exists(self.mapping_file)
            with open(self.mapping_file) as open_file:
                reader = csv.DictReader(open_file, delimiter=',')
                for row in reader:
                    assert row['vcf'].__contains__('example')
                    assert row['report'].__contains__('GCA_000001405.27_report.txt')
            m_docker_validator.assert_any_call(
                self.mapping_file, self.test_sub_dir, self.metadata_json, None,
                submission_config=m_config.return_value
            )
            m_docker_validator().validate_and_report.assert_called_once_with()


    def test_orchestrate_vcf_files_takes_precedence_over_metadata(self):
        shutil.copy(os.path.join(self.resource_dir, 'EVA_Submission_test_with_asm_report.json'), self.metadata_json)

        with patch('eva_sub_cli.main.WritableConfig') as m_config, \
                patch('eva_sub_cli.main.DockerValidator') as m_docker_validator:
            orchestrate_process(
                self.test_sub_dir, self.vcf_files, self.reference_fasta, self.metadata_json, None,
                tasks=[VALIDATE], executor=DOCKER, resume=False
            )
            # Mapping file was created from the metadata_json
            assert os.path.exists(self.mapping_file)
            with open(self.mapping_file) as open_file:
                reader = csv.DictReader(open_file, delimiter=',')
                for row in reader:
                    assert row['vcf'].__contains__('vcf_file')
                    assert row['report'] == None
            m_docker_validator.assert_any_call(
                self.mapping_file, self.test_sub_dir, self.metadata_json, None,
                submission_config=m_config.return_value
            )
            m_docker_validator().validate_and_report.assert_called_once_with()



    def test_orchestrate_with_metadata_xlsx(self):
        shutil.copy(os.path.join(self.resource_dir, 'EVA_Submission_test.xlsx'), self.metadata_xlsx)

        with patch('eva_sub_cli.main.WritableConfig') as m_config, \
                patch('eva_sub_cli.main.DockerValidator') as m_docker_validator:
            orchestrate_process(
                self.test_sub_dir, None, None, None, self.metadata_xlsx,
                tasks=[VALIDATE], executor=DOCKER, resume=False
            )
            # Mapping file was created from the metadata_xlsx
            assert os.path.exists(self.mapping_file)
            with open(self.mapping_file) as open_file:
                reader = csv.DictReader(open_file, delimiter=',')
                for row in reader:
                    assert row['vcf'].__contains__('example')
                    assert row['report'] == None
            m_docker_validator.assert_any_call(
                self.mapping_file, self.test_sub_dir, None, self.metadata_xlsx,
                submission_config=m_config.return_value
            )
            m_docker_validator().validate_and_report.assert_called_once_with()


    def test_metadata_file_does_not_exist_error(self):
        with self.assertRaises(Exception) as context:
            orchestrate_process(
                    self.test_sub_dir, None, None, None, self.metadata_xlsx,
                    tasks=[VALIDATE], executor=DOCKER, resume=False
            )
        self.assertRegex(str(context.exception),r"The provided metadata file .*/resources/test_sub_dir/sub_metadata.xlsx does not exist")


