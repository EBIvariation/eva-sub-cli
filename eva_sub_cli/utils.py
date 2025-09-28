from ebi_eva_common_pyutils.ena_utils import download_xml_from_ena
from requests import HTTPError


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


