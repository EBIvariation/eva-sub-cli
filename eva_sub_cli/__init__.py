import os


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # This is your Project Root
PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
NEXTFLOW_DIR = os.path.join(PACKAGE_DIR, 'nextflow')
ETC_DIR = os.path.join(PACKAGE_DIR, 'etc')
LSRI_CLIENT_ID = "aa0fcc42-096a-4f9d-b871-aceb1a97d174"
MINIMUM_METADATA_XLSX_TEMPLATE_VERSION = '2.0.0'

SUB_CLI_CONFIG_FILE = ".eva_sub_cli_config.yml"

# Environment variable
SUBMISSION_WS_VAR = 'SUBMISSION_WS_URL'
ENA_WEBIN_ACCOUNT_VAR = 'ENA_WEBIN_ACCOUNT'
ENA_WEBIN_PASSWORD_VAR = 'ENA_WEBIN_PASSWORD'


try:
    # If setuptools_scm is installed we can get the version directly from it
    from setuptools_scm import get_version
    __version__ = get_version(root='..', relative_to=__file__)
    del get_version
except:
    # otherwise assume that we're working in a deployed instance which should have the _version file
    from ._version import version as __version__


