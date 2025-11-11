import copy
import logging
import os
import shutil
import sys
from unittest import TestCase
from unittest.mock import patch, Mock

from requests import HTTPError

from eva_sub_cli import orchestrator
from eva_sub_cli.exceptions.metadata_template_version_exception import MetadataTemplateVersionException, \
    MetadataTemplateVersionNotFoundException
from eva_sub_cli.exceptions.submission_not_found_exception import SubmissionNotFoundException
from eva_sub_cli.exceptions.submission_status_exception import SubmissionStatusException
from eva_sub_cli.exceptions.submission_upload_exception import SubmissionUploadException
from eva_sub_cli.executables import cli
from eva_sub_cli.file_utils import DirLockError
from tests.test_utils import touch


class TestCli(TestCase):

    resources_folder = os.path.join(os.path.dirname(__file__), 'resources')
    submission_dir = os.path.abspath(os.path.join(resources_folder, 'submission_dir'))

    def setUp(self) -> None:
        os.makedirs(self.submission_dir, exist_ok=True)

    def tearDown(self) -> None:
        if os.path.exists(self.submission_dir):
            shutil.rmtree(self.submission_dir)

    def test_main(self):
        args = Mock(submission_dir=self.submission_dir,
                    vcf_files=[], reference_fasta='', metadata_json=None, metadata_xlsx='',
                    tasks='validate', executor='native', debug=False)
        with patch('eva_sub_cli.executables.cli.parse_args', return_value=args), \
                patch('eva_sub_cli.orchestrator.orchestrate_process'):
            exit_status = cli.main()
            # Check that the debug message is shown
            logger = orchestrator.logger
            logger.debug('test')
            assert exit_status == 0
            # Log file should contain the log message
            log_file = os.path.join(self.submission_dir, 'eva_submission.log')
            with open(log_file) as open_log_file:
                all_lines = open_log_file.readlines()
                all_lines[0].endswith('[eva_sub_cli.orchestrator][DEBUG] test\n')

    def test_validate_args(self):
        vcf_file = os.path.join(self.submission_dir,'test.vcf')
        fasta_file = os.path.join(self.submission_dir, 'test.fasta')
        json_file = os.path.join(self.submission_dir, 'test.json')
        touch(vcf_file)
        touch(fasta_file)
        touch(json_file)
        cmd_args = [
            '--submission_dir', self.submission_dir,
            '--vcf_files', vcf_file,
            '--reference_fasta', fasta_file,
            '--metadata_json', json_file,
            '--tasks', 'validate',
            '--executor', 'native',
            '--debug'
        ]
        args = cli.parse_args(cmd_args)
        assert args.submission_dir == self.submission_dir


        with patch('sys.exit') as m_exit:
            cli.parse_args(cmd_args[:2]+cmd_args[4:])
            m_exit.assert_called_once_with(1)

    def test_main_exception_handling(self):
        mock_response = Mock()
        mock_response.text = "Error while submitting submission"
        http_error = HTTPError("500 Internal Server Error", response=mock_response)

        test_cases = [
            (DirLockError(f'Could not acquire the lock file for {self.submission_dir} because another process is '
                          f'using this directory or a previous process did not terminate correctly. '
                          f'If the problem persists, remove the lock file manually.'), 65),
            (FileNotFoundError("The test_file does not exist"), 66),
            (SubmissionNotFoundException("submission not found"), 67),
            (SubmissionStatusException("can't get submission status"), 68),
            (MetadataTemplateVersionException("Metadata template version lower than expected"), 69),
            (MetadataTemplateVersionNotFoundException("Metadata template version not found"), 70),
            (SubmissionUploadException("Error while uploading submission: File size in metadata json does not match with the size of the file uploaded"), 71),
            (http_error, 72),
            (Exception("Exception occurred while processing"), 73),
        ]

        for exception, expected_exit in test_cases:
            with self.subTest(exception=exception):
                args = Mock(
                    submission_dir=self.submission_dir,
                    vcf_files=[], reference_fasta='', metadata_json=None, metadata_xlsx='',
                    tasks=['submit'], executor='native', debug=False
                )

                with patch('eva_sub_cli.executables.cli.parse_args', return_value=args), \
                        patch('eva_sub_cli.executables.cli.orchestrator.orchestrate_process', side_effect=exception), \
                        patch('builtins.print') as mock_print:
                    exit_status = cli.main()

                    self.assertEqual(exit_status, expected_exit)

                    printed_texts = " ".join(
                        " ".join(str(arg) for arg in call.args)
                        for call in mock_print.call_args_list
                    )
                    self.assertIn(str(exception), printed_texts)

                    if (isinstance(exception, HTTPError)):
                        self.assertIn(exception.response.text, printed_texts)
