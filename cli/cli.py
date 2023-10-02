from argparse import ArgumentParser

from ebi_eva_common_pyutils.logger import logging_config

from cli.submit import StudySubmitter

if __name__ == "__main__":
    argparse = ArgumentParser(description='EVA Submission CLI')
    argparse.add_argument('--submission-dir', required=True, type=str,
                          help='Full path to the submission directory where all submission info is/will be stored')
    argparse.add_argument('--resume', action='store_true', default=False, help='resume an existing submission')
    args = argparse.parse_args()

    logging_config.add_stdout_handler()

    submitter = StudySubmitter()
    if args.resume:
        submitter.upload_submission(args.submission_dir)
    else:
        submitter.submit(args.submission_dir)
