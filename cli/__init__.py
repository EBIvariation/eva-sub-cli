import os

import cli

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(cli.__file__)))  # This is your Project Root

NEXTFLOW_DIR = os.path.join(os.path.dirname(os.path.abspath(cli.__file__)), 'nextflow')
ETC_DIR = os.path.join(os.path.dirname(os.path.abspath(cli.__file__)), 'etc')
LSRI_CLIENT_ID = "aa0fcc42-096a-4f9d-b871-aceb1a97d174"

__version__ = open(os.path.join(os.path.dirname(os.path.abspath(cli.__file__)), 'VERSION')).read().strip()
