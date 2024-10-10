# eva-sub-cli
The eva-sub-cli tool is a command line interface tool for data validation and upload. The tool transforms the submission process at EVA by enabling users to take control of data validation process. Previously handled by our helpdesk team, validation can now be performed directly by users, streamlining and improving the overall submission workflow at the EVA. 


## Installation

There are currently three ways to install and run the tool : 
- Using conda
- From source using Docker
- From source natively (i.e. installing dependencies yourself)

### 1. Conda

The most straightforward way to install eva-sub-cli and its dependencies is through conda.
For instance, the following commands install eva-sub-cli in a new environment called `eva`, activate the environment, and print
the help message:
```bash
conda create -n eva -c conda-forge -c bioconda eva-sub-cli
conda activate eva
eva-sub-cli.py --help
````

### 2. From source using Docker

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

### 3. From source natively

This installation method requires the following :
* Python 3.8+
* [Nextflow](https://www.nextflow.io/docs/latest/getstarted.html) 21.10+
* [biovalidator](https://github.com/elixir-europe/biovalidator) 2.1.0+
* [vcf-validator](https://github.com/EBIvariation/vcf-validator) 0.9.7+

Install each of these and ensure they are included in your PATH. Then install the latest release as previously described.

## Getting started with the eva-sub-cli tool 

The ["Getting Started" guide](Getting_Started_with_eva_sub_cli.md) serves as an introduction for users of the eva-sub-cli tool. It includes instructions on how to prepare your data and metadata, ensuring that users are equipped with the necessary information to successfully submit variant data. This guide is essential for new users, offering practical advice and tips for a smooth onboarding experience with the eva-sub-cli tool.

## Options and parameters guide

The eva-sub-cli tool provides several options and parameters that you can use to tailor its functionality to your needs.
You can view all the available parameters with the command `eva-sub-cli.py -h` and view detailed explanations for the
input file requirements in the ["Getting Started" guide](Getting_Started_with_eva_sub_cli.md).
Below is an overview of the key parameters.

### Submission directory

This is the directory where all processing will take place, and where configuration and reports will be saved.
Crucially, the eva-sub-cli tool requires that there be **only one submission per directory** and that the submission directory not be reused.
Running multiple submissions from a single directory can result in data loss during validation and submission.

### Metadata file

Metadata can be provided in one of two files.

#### The metadata spreadsheet

The metadata template can be found within the [etc folder](eva_sub_cli/etc/EVA_Submission_template.xlsx). It should be populated following the instructions provided within the template.
This is passed using the option `--metadata_xlsx`.

#### The metadata JSON

The metadata can also be provided via a JSON file, which should conform to the schema located [here](eva_sub_cli/etc/eva_schema.json).
This is passed using the option `--metadata_json`.

### VCF files and Reference FASTA

These can be provided either in the metadata file directly, or on the command line using the `--vcf_files` and `--reference_fata` options.
Note that if you are using more than one reference FASTA, you **cannot** use the command line options; you must specify which VCF files use which FASTA files in the metadata.

VCF files can be either uncompressed or compressed using bgzip.
Other types of compression are not allowed and will result in errors during validation.
FASTA files must be uncompressed.

## Execution

### Validate only

To validate and not submit, run the following command:

```shell
eva-sub-cli.py --metadata_xlsx metadata_spreadsheet.xlsx --submission_dir submission_dir --tasks VALIDATE
```

**Note for Docker users:** 

Make sure that Docker is running in the background, e.g. by opening Docker Desktop.
For each of the below commands, add the command line option `--executor docker`, which will
fetch and manage the docker container for you. 

```shell
eva-sub-cli.py --metadata_xlsx metadata_spreadsheet.xlsx --submission_dir submission_dir --tasks VALIDATE --executor docker 
```

### Validate and submit your dataset

To validate and submit, run the following command:

```shell
eva-sub-cli.py --metadata_xlsx metadata_spreadsheet.xlsx \
               --vcf_files vcf_file1.vcf vcf_file2.vcf --reference_fasta assembly.fa --submission_dir submission_dir
```


### Submit only

All submissions must have been validated. You cannot run the submission without validation. Once validated, execute the following command:

```shell
eva-sub-cli.py --metadata_xlsx metadata_spreadsheet.xlsx --submission_dir submission_dir
```
or 
```shell
eva-sub-cli.py --metadata_xlsx metadata_spreadsheet.xlsx --submission_dir submission_dir --tasks SUBMIT
```
This will only submit the data and not validate.

### Shallow validation

If you are working with large VCF files and find that validation takes a very long time, you can add the
argument `--shallow` to the command, which will validate only the first 10,000 lines in each VCF. Note that running
shallow validation will **not** be sufficient for actual submission.
