import requests
from packaging import version
from requests import HTTPError
from retry import retry

import eva_sub_cli
from ebi_eva_common_pyutils.ena_utils import download_xml_from_ena


def get_project_title_from_ena(project_accession):
    try:
        xml_root = download_xml_from_ena(f'https://www.ebi.ac.uk/ena/browser/api/xml/{project_accession}')
        project_title = next(iter(xml_root.xpath('/PROJECT_SET/PROJECT/TITLE/text()')), None)
    except HTTPError as e:
        # We cannot currently differentiate between the service returning an error and the accession not existing
        raise Exception(f"{project_accession} does not exist in ENA or is private")
    except Exception as e:
        raise Exception(f'Unexpected error occurred while getting project details from ENA for {project_accession}')

    if not project_title:
        raise Exception(f"{project_accession} does not exist in ENA or is private")

    return project_title


def get_sub_cli_version():
    if version.parse(eva_sub_cli.__version__).is_devrelease:
        version_values = [int(v) for v in version.parse(eva_sub_cli.__version__).base_version.split('.')]
        major = version_values[0]
        minor = version_values[1] if len(version_values) > 1 else 0
        patch = version_values[2] if len(version_values) > 2 else 0
        if patch > 0:
            patch -= 1
        elif minor > 0:
            minor -= 1
            patch = 0
        elif major > 0:
            major -= 1
            minor = 0
            patch = 0
        return f"{major}.{minor}.{patch}"
    else:
        return version.parse(eva_sub_cli.__version__).base_version


@retry(exceptions=(HTTPError,), tries=3, delay=2, backoff=1.2, jitter=(1, 3))
def get_sub_cli_github_tags():
    url = f"https://api.github.com/repos/EBIvariation/eva-sub-cli/tags"
    response = requests.get(url)
    if response.status_code == 200:
        tags = [tag["name"][1:] for tag in response.json()]
        return tags
    else:
        return []


def get_metadata_xlsx_template_link():
    sub_cli_version = get_sub_cli_version()
    sub_cli_tags = get_sub_cli_github_tags()
    if sub_cli_version in sub_cli_tags:
        return f'https://raw.githubusercontent.com/EBIvariation/eva-sub-cli/refs/tags/v{sub_cli_version}/eva_sub_cli/etc/EVA_Submission_template.xlsx'
    else:
        return 'https://raw.githubusercontent.com/EBIvariation/eva-sub-cli/main/eva_sub_cli/etc/EVA_Submission_template.xlsx'


def get_json_schema_link():
    sub_cli_version = get_sub_cli_version()
    sub_cli_tags = get_sub_cli_github_tags()
    if sub_cli_version in sub_cli_tags:
        return f'https://raw.githubusercontent.com/EBIvariation/eva-sub-cli/refs/tags/v{sub_cli_version}/eva_sub_cli/etc/eva_schema.json'
    else:
        return 'https://raw.githubusercontent.com/EBIvariation/eva-sub-cli/main/eva_sub_cli/etc/eva_schema.json'
