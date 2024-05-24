import base64
import os.path

from jinja2 import Environment, FileSystemLoader

current_dir = os.path.dirname(__file__)


def get_logo_data():
    with open(os.path.join(current_dir, "etc/eva_logo.png"), "rb") as f:
        logo_data = base64.b64encode(f.read()).decode("utf-8")
        return logo_data


def generate_html_report(validation_results, validation_date, submission_dir, vcf_fasta_analysis_mapping, project_title=None):
    vcf_files = sorted(set([file_name
                            for check in validation_results if check in ["vcf_check", "assembly_check"]
                            for file_name in validation_results[check]
                            ]))
    fasta_files = sorted([file_name for file_name in validation_results['fasta_check']])
    template = Environment(
        loader=FileSystemLoader(os.path.join(current_dir, 'jinja_templates'))
    ).get_template('html_report.html')
    rendered_template = template.render(
        logo_data=get_logo_data(),
        project_title=project_title,
        validation_date=validation_date,
        vcf_files=vcf_files,
        fasta_files=fasta_files,
        submission_dir=submission_dir,
        vcf_fasta_analysis_mapping=vcf_fasta_analysis_mapping,
        validation_results=validation_results,
    )

    try:
        # minify-html is not included in conda installation currently
        from minify_html import minify_html
        return minify_html.minify(rendered_template, minify_js=True, remove_processing_instructions=True)
    except ImportError:
        return rendered_template
