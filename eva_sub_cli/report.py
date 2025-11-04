import base64
import os.path
import re

from jinja2 import Environment, FileSystemLoader

import eva_sub_cli

current_dir = os.path.dirname(__file__)


def get_logo_data():
    with open(os.path.join(current_dir, "etc/eva_logo.png"), "rb") as f:
        logo_data = base64.b64encode(f.read()).decode("utf-8")
        return logo_data


def generate_report(validation_results, validation_date, submission_dir, vcf_fasta_analysis_mapping, project_title,
                    consent_statement_required, subdir, template_file):

    from eva_sub_cli.validators.validator import RUN_STATUS_KEY, PASS

    results_for_report = {k: v for k, v in validation_results.items() if k != 'ready_for_submission_to_eva'}
    vcf_files = sorted(set([file_name
                            for check in results_for_report if check in ["vcf_check", "assembly_check"]
                            for file_name in results_for_report[check]
                            if file_name not in {RUN_STATUS_KEY, PASS}
                            ]))
    fasta_files = sorted([file_name for file_name in results_for_report['fasta_check'] if file_name not in {RUN_STATUS_KEY, PASS}])
    template = Environment(
        loader=FileSystemLoader(os.path.join(current_dir, 'jinja_templates', subdir))
    ).get_template(template_file)
    rendered_template = template.render(
        cli_version=eva_sub_cli.__version__,
        logo_data=get_logo_data(),
        project_title=project_title,
        validation_date=validation_date,
        vcf_files=vcf_files,
        fasta_files=fasta_files,
        submission_dir=submission_dir,
        consent_statement_required=consent_statement_required,
        vcf_fasta_analysis_mapping=vcf_fasta_analysis_mapping,
        validation_results=results_for_report
    )
    return re.sub('\s+\n', '\n', rendered_template)


def generate_html_report(validation_results, validation_date, submission_dir, vcf_fasta_analysis_mapping, project_title,
                         consent_statement_required):
    return generate_report(validation_results, validation_date, submission_dir, vcf_fasta_analysis_mapping,
                           project_title, consent_statement_required, subdir='html', template_file='report.html')


def generate_text_report(validation_results, validation_date, submission_dir, vcf_fasta_analysis_mapping, project_title,
                         consent_statement_required):
    return generate_report(validation_results, validation_date, submission_dir, vcf_fasta_analysis_mapping,
                           project_title, consent_statement_required, subdir='text', template_file='report.txt')
