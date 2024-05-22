# eva-sub-cli
EVA Submission Command Line Interface for Validation


## Installation

There are currently three ways to install and run the tool: using conda, from source using Docker,
and from source natively (i.e. managing dependencies on your own).

### Conda

The most straightforward way to install eva-sub-cli and its dependencies is through conda.
For example the following installs eva-sub-cli in a new environment called `eva`, activates the environment, and prints
the help message:
```bash
conda create -n eva -c conda-forge -c bioconda eva-sub-cli
conda activate eva
eva-sub-cli.py --help
````

### From source using Docker

Docker provides an easy way to run eva-sub-cli without installing dependencies separately.
This method requires just Python 3.8+ and [Docker](https://docs.docker.com/engine/install/) to be installed.
Then either clone the git repository, or download the newest tagged release from [here](https://github.com/EBIvariation/eva-sub-cli/tags):
```bash
git clone git@github.com:EBIvariation/eva-sub-cli.git
# OR (replace "v0.2" with the newest version)
wget -O eva-sub-cli.zip https://github.com/EBIvariation/eva-sub-cli/archive/refs/tags/v0.2.zip
unzip eva-sub-cli.zip && mv eva-sub-cli-* eva-sub-cli
```

Then install the library and its dependencies as follows (e.g. in a virtual environment):
```bash
cd eva-sub-cli
pip install -r requirements.txt
python setup.py install
```

To check it is installed correctly, you can run:
```bash
eva-sub-cli.py -h
```

### From source natively

This method requires the following:
* Python 3.8+
* [Nextflow](https://www.nextflow.io/docs/latest/getstarted.html) 21.10+
* [biovalidator](https://github.com/elixir-europe/biovalidator) 2.1.0+
* [vcf-validator](https://github.com/EBIvariation/vcf-validator) 0.9.6+

Install each of these and ensure they are available on the path.
Then git clone the repo or install the newest release as described above.

## Input files for the validation and submission tool

There are two ways of specifying the VCF files and associated reference genome

### Using  `--vcf_files` and `--reference_fasta`

This allows you to provide multiple VCF files to validate and a single associated reference genome file.
The VCF files and the associated reference genome file must use the same chromosome naming convention 

### Using metadata file by providing `--metadata_json` or `--metadata_xlsx`

The path to the VCF files are provided in the Files section of the metadata and their corresponding fasta sequence is provided in the analysis section. 
This allows us to support different assemblies for each VCF file. 
Please check the below sections `The metadata spreadsheet` and `The metadata JSON` for the format and options available in metadata files.

### The metadata spreadsheet 

The metadata template can be found within the etc folder at `eva_sub_cli/etc/EVA_Submission_template.xlsx`
It should be populated following the instruction provided within the template

### The metadata JSON

The metadata can also be provided via a JSON file which should conform to the schema located  at 
`eva_sub_cli/etc/eva_schema.json` 

More detail documentation to follow 

## Execution

**Note for Docker users:** for each of the below commands, add the command line option `--executor docker`, which will
fetch and manage the docker container for you. Make sure that Docker is running in the background, e.g.
by opening Docker Desktop.

### Validate and submit your dataset

To validate and submit run the following command

```shell
eva-sub-cli.py --metadata_xlsx metadata_spreadsheet.xlsx \
               --vcf_files vcf_file1.vcf vcf_file2.vcf --reference_fasta assembly.fa --submission_dir submission_dir
```

### Validate only

To validate and not submit run the following command

```shell
eva-sub-cli.py --metadata_xlsx metadata_spreadsheet.xlsx --submission_dir submission_dir --tasks VALIDATE
```
### Submit only

All submission must have been validated. You cannot run the submission without validation. Once validated running 

```shell
eva-sub-cli.py --metadata_xlsx metadata_spreadsheet.xlsx --submission_dir submission_dir
```
or 
```shell
eva-sub-cli.py --metadata_xlsx metadata_spreadsheet.xlsx --submission_dir submission_dir --tasks SUBMIT
```
Will only submit the data and not validate.
