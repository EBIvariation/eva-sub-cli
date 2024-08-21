import sys

import eva_sub_cli
from eva_sub_cli.exceptions.submission_not_found_exception import SubmissionNotFoundException
from eva_sub_cli.exceptions.submission_status_exception import SubmissionStatusException

if not sys.warnoptions:
    import warnings
    warnings.simplefilter("ignore")

import logging
import os
from argparse import ArgumentParser
from ebi_eva_common_pyutils.logger import logging_config

from eva_sub_cli import orchestrator
from eva_sub_cli.orchestrator import VALIDATE, SUBMIT, DOCKER, NATIVE
from eva_sub_cli.file_utils import is_submission_dir_writable


def validate_command_line_arguments(args, argparser):
    if (args.vcf_files and not args.reference_fasta) or (not args.vcf_files and args.reference_fasta):
        print("When using --vcf_files and --reference_fasta, both need to be specified")
        argparser.print_usage()
        sys.exit(1)

    if SUBMIT in args.tasks and (
            not (args.username or os.environ.get('ENAWEBINACCOUNT')) or
            not (args.password or os.environ.get('ENAWEBINPASSWORD'))):
        print("To submit your data, you need to provide a Webin username and password")
        argparser.print_usage()
        sys.exit(1)

    if not is_submission_dir_writable(args.submission_dir):
        print(f"'{args.submission_dir}' does not have write permissions or is not a directory.")
        sys.exit(1)


def main():
    argparser = ArgumentParser(prog='eva-sub-cli', description='EVA Submission CLI - validate and submit data to EVA')
    argparser.add_argument('--version', action='version', version=f'%(prog)s {eva_sub_cli.__version__}')
    argparser.add_argument('--submission_dir', required=True, type=str,
                           help='Full path to the directory where all processing will be done '
                                'and submission info is/will be stored')
    vcf_group = argparser.add_argument_group(
        'Input VCF and assembly',
        "Specify the VCF files and associated assembly with the following options. If you used different assemblies "
        "for different VCF files then include these in the metadata file."
    )
    vcf_group.add_argument('--vcf_files', nargs='+', help="One or several vcf files to validate")
    vcf_group.add_argument('--reference_fasta',
                           help="The fasta file containing the reference genome from which the variants were derived")

    metadata_group = argparser.add_argument_group('Metadata', 'Specify the metadata in a spreadsheet or in a JSON file')
    metadata_group = metadata_group.add_mutually_exclusive_group(required=True)
    metadata_group.add_argument("--metadata_json",
                                help="Json file that describe the project, analysis, samples and files")
    metadata_group.add_argument("--metadata_xlsx",
                                help="Excel spreadsheet  that describe the project, analysis, samples and files")
    argparser.add_argument('--tasks', nargs='*', choices=[VALIDATE, SUBMIT], default=[SUBMIT], type=str.lower,
                           help='Select a task to perform. Selecting VALIDATE will run the validation regardless of the'
                                ' outcome of previous runs. Selecting SUBMIT will run validate only if the validation'
                                ' was not performed successfully before and then run the submission.')
    argparser.add_argument('--executor', choices=[DOCKER, NATIVE], default=NATIVE, type=str.lower,
                           help='Select an execution type for running validation (default native)')
    credential_group = argparser.add_argument_group('Credential', 'Specify the Webin credential you want to use to '
                                                                  'upload to the EVA')
    credential_group.add_argument("--username", help="Username used for connecting to the ENA webin account")
    credential_group.add_argument("--password", help="Password used for connecting to the ENA webin account")

    args = argparser.parse_args()

    validate_command_line_arguments(args, argparser)

    logging_config.add_stdout_handler()
    logging_config.add_file_handler(os.path.join(args.submission_dir, 'eva_submission.log'), logging.DEBUG)

    try:
        # Pass on all the arguments
        orchestrator.orchestrate_process(**args.__dict__)
    except FileNotFoundError as fne:
        print(fne)
    except SubmissionNotFoundException as snfe:
        print(f'{snfe}. Please contact EVA Helpdesk')
    except SubmissionStatusException as sse:
        print(f'{sse}. Please try again later. If the problem persists, please contact EVA Helpdesk')