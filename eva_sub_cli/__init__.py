import os


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # This is your Project Root
PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
NEXTFLOW_DIR = os.path.join(PACKAGE_DIR, 'nextflow')
ETC_DIR = os.path.join(PACKAGE_DIR, 'etc')
LSRI_CLIENT_ID = "aa0fcc42-096a-4f9d-b871-aceb1a97d174"

__version__ = open(os.path.join(PACKAGE_DIR, 'VERSION')).read().strip()

SUB_CLI_CONFIG_FILE = ".eva_sub_cli_config.yml"