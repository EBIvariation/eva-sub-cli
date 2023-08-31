import base64
import os.path

from jinja2 import Environment, FileSystemLoader
from minify_html import minify_html

current_dir = os.path.dirname(__file__)


def get_logo_data():
    with open(os.path.join(current_dir, "eva_logo.png"), "rb") as f:
        logo_data = base64.b64encode(f.read()).decode("utf-8")
        return logo_data


def generate_html_report(validation_results, validation_date, project_title=None):
    file_names = sorted(set([file_name
                             for check in validation_results if check in ["vcf_check", "assembly_check"]
                             for file_name in validation_results[check]
                             ]))

    template = Environment(
        loader=FileSystemLoader(os.path.join(current_dir, 'jinja_templates'))
    ).get_template('html_report.html')
    rendered_template = template.render(
        logo_data=get_logo_data(),
        project_title=project_title,
        validation_date=validation_date,
        file_names=file_names,
        validation_results=validation_results,
    )

    return minify_html.minify(rendered_template, minify_js=True, remove_processing_instructions=True)
