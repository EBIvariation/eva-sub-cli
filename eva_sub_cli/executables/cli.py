import sys

from requests import HTTPError

from eva_sub_cli.exceptions.submission_upload_exception import SubmissionUploadException

if not sys.warnoptions:
    import warnings
    warnings.simplefilter("ignore")

import logging
import os
from argparse import ArgumentParser
from ebi_eva_common_pyutils.logger import logging_config

import eva_sub_cli
from eva_sub_cli import orchestrator
from eva_sub_cli.exceptions.metadata_template_version_exception import MetadataTemplateVersionException, \
    MetadataTemplateVersionNotFoundException
from eva_sub_cli.exceptions.submission_status_exception import SubmissionStatusException
from eva_sub_cli.exceptions.submission_not_found_exception import SubmissionNotFoundException
from eva_sub_cli.file_utils import is_submission_dir_writable, DirLockError, DirLock
from eva_sub_cli.orchestrator import VALIDATE, SUBMIT, DOCKER, NATIVE
from eva_sub_cli.validators.validator import ALL_VALIDATION_TASKS


def validate_command_line_arguments(args, argparser):
    fail = False
    if (args.vcf_files and not args.reference_fasta) or (not args.vcf_files and args.reference_fasta):
        print("When using --vcf_files and --reference_fasta, both need to be specified")
        fail = True

    if args.vcf_files:
        for vcf_file in args.vcf_files:
            if not os.path.isfile(vcf_file):
                print(f"VCF file {vcf_file} is not a file")
                fail = True

    if args.reference_fasta:
        if not os.path.isfile(args.reference_fasta):
            print(f"Fasta file {args.reference_fasta} is not a file")
            fail = True

    if args.metadata_xlsx:
        if not os.path.isfile(args.metadata_xlsx):
            print(f"Spreadsheet file {args.metadata_xlsx} is not a file")
            fail = True

    if args.metadata_json:
        if not os.path.isfile(args.metadata_json):
            print(f"JSON file {args.metadata_json} is not a file")
            fail = True

    if SUBMIT in args.tasks and (
            not (args.username or os.environ.get('ENAWEBINACCOUNT')) or
            not (args.password or os.environ.get('ENAWEBINPASSWORD'))):
        print("To submit your data, you need to provide a Webin username and password")
        fail = True

    if not is_submission_dir_writable(args.submission_dir):
        print(f"'{args.submission_dir}' does not have write permissions or is not a directory.")
        fail = True

    if args.nextflow_config and not os.path.isfile(args.nextflow_config):
        print(f"'{args.nextflow_config}' is not a file or does not exist.")
        fail = True

    if fail:
        argparser.print_usage()
        sys.exit(1)


def parse_args(cmd_line_args):
    argparser = ArgumentParser(prog='eva-sub-cli',
                               description='EVA Submission CLI - validate and submit data to EVA. '
                                           'For full details, please see https://github.com/EBIvariation/eva-sub-cli')
    argparser.add_argument('--version', action='version', version=f'%(prog)s {eva_sub_cli.__version__}')
    argparser.add_argument('--submission_dir', required=True, type=str,
                           help='Path to the directory where all processing is done and submission info is stored')
    vcf_group = argparser.add_argument_group(
        'Input VCF and assembly',
        "Specify the VCF files and associated assembly with the following options. If you used different assemblies "
        "for different VCF files, then you must include these in the metadata file rather than specifying them here."
    )
    vcf_group.add_argument('--vcf_files', nargs='+', help="One or more VCF files to validate")
    vcf_group.add_argument('--reference_fasta',
                           help="The FASTA file containing the reference genome from which the variants were derived")

    metadata_group = argparser.add_argument_group('Metadata', 'Specify the metadata in a spreadsheet or in a JSON file')
    metadata_group = metadata_group.add_mutually_exclusive_group(required=True)
    metadata_group.add_argument("--metadata_json",
                                help="JSON file that describes the project, analysis, samples and files")
    metadata_group.add_argument("--metadata_xlsx",
                                help="Excel spreadsheet that describes the project, analysis, samples and files")
    argparser.add_argument('--tasks', nargs='+', choices=[VALIDATE, SUBMIT], default=[SUBMIT], type=str.lower,
                           help='Select a task to perform (default SUBMIT). VALIDATE will run the validation'
                                ' regardless of the outcome of previous runs. SUBMIT will run validate only if'
                                ' the validation was not performed successfully before and then run the submission.')
    argparser.add_argument('--validation_tasks', nargs='+', choices=ALL_VALIDATION_TASKS, default=ALL_VALIDATION_TASKS,
                           type=str.lower, help='Select only a subset of the validation tasks to run. Note that all '
                                                'tasks need to be successful for the validation to pass')
    argparser.add_argument('--executor', choices=[DOCKER, NATIVE], default=NATIVE, type=str.lower,
                           help='Select the execution type for running validation (default native)')
    credential_group = argparser.add_argument_group('Credentials', 'Specify the ENA Webin credentials you want to use '
                                                                   'to submit to the EVA')
    credential_group.add_argument("--username", help="Username for your ENA Webin account")
    credential_group.add_argument("--password", help="Password for your ENA Webin account")
    argparser.add_argument('--shallow', action='store_true', default=False, dest='shallow_validation',
                           help='Set the validation to be performed on the first 10000 records of the VCF. '
                                'Only applies if the number of records exceed 10000')
    argparser.add_argument('--nextflow_config', type=str,
                           help='Path to the configuration file that will be applied to the Nextflow process. '
                                'This will override other nextflow configuration files you might have on your filesystem')
    argparser.add_argument('--debug', action='store_true', default=False,
                           help='Set the script to output debug messages')
    args = argparser.parse_args(cmd_line_args)
    validate_command_line_arguments(args, argparser)
    return args


def main():
    exit_status = 0
    args = parse_args(sys.argv[1:])

    args.submission_dir = os.path.abspath(args.submission_dir)

    if args.debug:
        logging_config.add_stdout_handler(logging.DEBUG)
    else:
        logging_config.add_stdout_handler(logging.INFO)

    try:
        # lock the submission directory
        with DirLock(os.path.join(args.submission_dir)) as lock:
            # Create the log file
            logging_config.add_file_handler(os.path.join(args.submission_dir, 'eva_submission.log'), logging.DEBUG)
            # Pass on all the arguments to the orchestrator
            orchestrator.orchestrate_process(**args.__dict__)
    except DirLockError:
        print(f'Could not acquire the lock file for {args.submission_dir} because another process is using this '
              f'directory or a previous process did not terminate correctly. '
              f'If the problem persists, remove the lock file manually.')
        exit_status = 65
    except FileNotFoundError as fne:
        print(fne)
        exit_status = 66
    except SubmissionNotFoundException as snfe:
        print(f'{snfe}. Please contact EVA Helpdesk')
        exit_status = 67
    except SubmissionStatusException as sse:
        print(f'{sse}. Please try again later. If the problem persists, please contact EVA Helpdesk')
        exit_status = 68
    except MetadataTemplateVersionException as mte:
        print(mte)
        exit_status = 69
    except MetadataTemplateVersionNotFoundException as mte:
        print(mte)
        exit_status = 70
    except SubmissionUploadException as sue:
        print(sue)
        exit_status = 71
    except HTTPError as http_err:
        print(http_err)
        if http_err.response is not None and http_err.response.text:
            print(http_err.response.text)
        exit_status = 72
    except Exception as ex:
        print(ex)
        exit_status = 73
    return exit_status
