# Installation

There are two main ways to install eva-sub-cli, either through [conda](#1-conda) or [pip](#2-pip).
Conda is the most straightforward and recommended method, as it will install all dependencies for you.

Otherwise you can install using pip, in which case you will need to handle non-Python dependencies separately.
You can do this either using Docker or natively (i.e. installing by yourself).
Note that pip using Docker is currently the only installation method available for Windows users.

We encourage users to install the most recent version, as we are constantly improving the tool. You can check that you
have the latest version installed by running `eva-sub-cli.py --version` and comparing against the
[release page](https://github.com/EBIvariation/eva-sub-cli/releases).

All installation methods require Python 3.8 or above.

## 1. Conda

View our [video tutorial on conda installation](https://embl-ebi.cloud.panopto.eu/Panopto/Pages/Viewer.aspx?id=aa82710e-4401-4074-b6b0-b346016bb14e).

The most straightforward way to install eva-sub-cli and its dependencies is through conda.
For instance, the following commands install eva-sub-cli in a new environment called `eva`, activate the environment, and print
the help message:
```bash
conda create -n eva -c conda-forge -c bioconda eva-sub-cli
conda activate eva
eva-sub-cli.py --help
````

To upgrade to the newest version, run `conda update eva-sub-cli`.

## 2. Pip

View our [video tutorial on pip installation](https://embl-ebi.cloud.panopto.eu/Panopto/Pages/Viewer.aspx?id=2e6828ed-31c2-4621-8eb5-b34701484aae).

You can also install eva-sub-cli using pip. 
The following commands will create a new virtual environment called `eva`, activate the environment, and install eva-sub-cli:
```bash
python3 -m venv eva
source ./eva/bin/activate
pip install eva-sub-cli
```

You can verify the installation by printing the help message:
```bash
eva-sub-cli.py --help
```

For external (non-Python) dependencies, you will need to install them either [via Docker](#docker) or [natively](#native).
These methods are described below.

To upgrade to the newest version of the tool, run `pip install --upgrade eva-sub-cli`.

### Docker

Docker provides an easy way to run eva-sub-cli without installing dependencies separately.
For this method, all you need is for [Docker](https://docs.docker.com/engine/install/) to be installed and running in the background.

When you run eva-sub-cli, you will need to [specify execution using Docker](how_to_submit.md#running-using-docker).
The tool will then automatically run using a Docker container with all dependencies pre-installed.

### Native

For those requiring more flexibility or working on systems where Docker is not available, you can also install the 
external dependencies on your own. These are:
* [Nextflow](https://www.nextflow.io/docs/latest/getstarted.html) 21.10+
* [biovalidator](https://github.com/elixir-europe/biovalidator) 2.1.0+
* [vcf-validator](https://github.com/EBIvariation/vcf-validator) 0.9.7+

Install each of these and ensure they are included in your PATH.
This will allow eva-sub-cli to be executed natively, i.e. directly on your machine.
