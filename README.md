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

The ["Getting Started" guide](docs/Getting_Started_with_eva_sub_cli.md) serves as an introduction for users of the eva-sub-cli tool. It includes instructions on how to prepare your data and metadata, ensuring that users are equipped with the necessary information to successfully submit variant data. This guide is essential for new users, offering practical advice and tips for a smooth onboarding experience with the eva-sub-cli tool.

## Options and parameters guide

The eva-sub-cli tool provides several options and parameters that you can use to tailor its functionality to your needs.
You can view all the available parameters with the command `eva-sub-cli.py -h` and view detailed explanations for the
input file requirements in the ["Getting Started" guide](docs/Getting_Started_with_eva_sub_cli.md).
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
fetch and manage the Docker container for you. 

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


## Leveraging Nextflow to parallelize the validation process  

Nextflow is a common workflow management system that helps orchestrate tasks and interface with the execution engine (like HPC or cloud). When running natively (i.e. not using Docker), eva-sub-cli will use Nextflow to run all the validation steps. In this section we'll see how it can be parameterised to work with your compute infrastructure.

When no options are provided, Nextflow will run as many tasks as there are available CPUs on the machine executing it. To modify how many tasks can start and how Nextflow will process each one, you can provide a Nextflow configuration file in several ways.

From the command line you can use `--nextflow_config <path>` to specify the Nextflow config file you want to apply. The configuration can also be picked up from other places directly by Nextflow. Please refer to [the nextflow documentation](https://www.nextflow.io/docs/latest/config.html) for more details.

### Basic Nextflow configuration.

There are many options to configure Nextflow so we will not provide them all. Please refer to [the documentation](https://www.nextflow.io/docs/latest/reference/config.html) for advanced features.
Below is a very basic Nextflow configuration file that will request 2 cpus for each process, essentially limiting the number of process to half the number of available CPUs 
```
process {
    executor="local"
    cpus=2
}
```
In this configuration, all the process will be running on the same machine where eva-sub-cli was started as described in the schema below.
```
(Local machine)
eva-sub-cli
  |_ nextflow
      |_ task1
      |_ task2
```

### Basic Nextflow configuration for HPC use.

If you have access to High Performance Compute (HPC) environment, Nextflow supports the main resource managers such as [SLURM](https://www.nextflow.io/docs/latest/executor.html#slurm), [SGE](https://www.nextflow.io/docs/latest/executor.html#sge), [LSF](https://www.nextflow.io/docs/latest/executor.html#lsf) and others.
In the configuration below, we're assuming that you are using SLURM. It would work similarly with other resource managers.
```
process {
    executor="slurm"
    queue="my_production_queue"
}
```

In this configuration, the subtasks will be performed in other machines as specified by your SLURM resource manager as described in the schema below.
```
(Local machine)
eva-sub-cli
  |_ nextflow
(Other compute node)
task1
(Other compute node)
task2
```
