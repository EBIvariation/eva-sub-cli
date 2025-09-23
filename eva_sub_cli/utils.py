from ebi_eva_common_pyutils.ena_utils import download_xml_from_ena
from requests import HTTPError
from retry import retry


@retry(tries=4, delay=2, backoff=1.2, jitter=(1, 3))
def get_project_title_from_ena(project_accession):
    try:
        xml_root = download_xml_from_ena(f'https://www.ebi.ac.uk/ena/browser/api/xml/{project_accession}')
        project_title = next(iter(xml_root.xpath('/PROJECT_SET/PROJECT/TITLE/text()')), None)
        if project_title:
            return project_title
        else:
            raise Exception(f"{project_accession} does not exist in ENA or is private")
    except HTTPError as e:
        # We cannot currently differentiate between the service returning an error and the accession not existing
        if e.response.status_code == 500:
            raise Exception(f"{project_accession} does not exist in ENA or is private")
        else:
            raise Exception(f"{project_accession} does not exist in ENA or is private")
    except Exception as e:
        raise Exception(f'Unexpected error occurred while getting project details from ENA for {project_accession}')
