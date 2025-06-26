# Installation

There are currently three ways to install and run the tool : 
- Using conda
- From source using Docker
- From source natively (i.e. installing dependencies yourself)

We encourage users to install the most recent version, as we are constantly improving the tool.

## 1. Conda

The most straightforward way to install eva-sub-cli and its dependencies is through conda.
For instance, the following commands install eva-sub-cli in a new environment called `eva`, activate the environment, and print
the help message:
```bash
conda create -n eva -c conda-forge -c bioconda eva-sub-cli
conda activate eva
eva-sub-cli.py --help
````

## 2. From source using Docker

Docker provides an easy way to run eva-sub-cli without installing dependencies separately.
This method requires just Python 3.8+ and [Docker](https://docs.docker.com/engine/install/) to be installed.
Then you can install the most recent version from [PyPI](https://pypi.org/project/eva-sub-cli/) in a virtual environment:
```bash
pip install eva-sub-cli
```

To verify that the cli tool is installed correctly, run the following command, and you should see the help message displayed : 
```bash
eva-sub-cli.py -h
```

## 3. From source natively

This installation method requires the following :
* Python 3.8+
* [Nextflow](https://www.nextflow.io/docs/latest/getstarted.html) 21.10+
* [biovalidator](https://github.com/elixir-europe/biovalidator) 2.1.0+
* [vcf-validator](https://github.com/EBIvariation/vcf-validator) 0.9.7+

Install each of these and ensure they are included in your PATH. Then install the latest release as previously described.
