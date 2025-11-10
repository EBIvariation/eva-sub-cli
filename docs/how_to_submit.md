# How to Submit

## 1. File preparation
You should have **one or more VCF files** to submit, as well as a **completed metadata spreadsheet** following [our 
template](https://raw.githubusercontent.com/EBIvariation/eva-sub-cli/main/eva_sub_cli/etc/EVA_Submission_template.xlsx).
More guidance on these files can be found in the [inputs overview](input_file_overview.md) as well as in the metadata 
template itself.

You will also need the **reference sequences in FASTA format** that you used to generate the VCF files. This is required for
validation, though it will not be submitted.

## 2. Setting up
First [**install eva-sub-cli**](installation.md), or check that you have the latest version installed.

You will need an [**ENA Webin account**](https://www.ebi.ac.uk/ena/submit/webin/login) in order to submit, though you
can run validation without one.

Finally, you need to specify a **submission directory**, which is a specific directory associated with each submission.
This is where all processing will take place, and where configuration and reports will be saved.

Crucially, the eva-sub-cli tool requires that there be **only one submission per directory** and
that the submission directory not be reused. Running multiple submissions from a single directory can result in data 
loss during validation and submission.

## 3. Running eva-sub-cli
The basic command to run validation and submission is as follows:
```shell
eva-sub-cli.py --metadata_xlsx <metadata file> --submission_dir <submission directory> --username <webin username> --password <webin password>
```
This will run validation and generate a report with the results. The report can be viewed as HTML or plain text. More 
description of the validation checks being performed can be found in the [validation overview](validation_overview.md).

**NOTE:** If the validation is successful, this command will automatically submit your data and metadata to EVA. If you 
don't want this, see [below](#running-only-validation-or-only-submission).

If your files are large, we also encourage you to use [shallow validation](#shallow-validation) before running full
validation and submission.

## 4. Post submission
Once you've successfully validated and submitted your data, you will receive an automatic email stating that your data
has been uploaded. If you don't get this email within a short time, we have very likely **not received your data**, so
you should get in touch with our [helpdesk](mailto:eva-helpdesk@ebi.ac.uk).

If your submission contains **human genotype data**, then you will also need to provide a signed copy of our
[consent statement](https://docs.google.com/document/d/1UaRmimAe919IZYIH55mDXMe-4sHsRVqaP4moqx2IYE4) via email.
For more information please see our [submission FAQs](https://www.ebi.ac.uk/eva/?Help#submissionPanel&link=consent-statement-for-human-genotype-data).

## Other options
The above steps are the most common, but there are some other options that you can use to tailor its functionality to
your needs. A full listing is available by running `eva-sub-cli.py -h`.

### Running only validation or only submission
If you want to run validation without submitting automatically once the validation passes, you can use the `--tasks` 
option. To run only validation:
```shell
eva-sub-cli.py --metadata_xlsx <metadata file> --submission_dir <submission directory> --tasks VALIDATE
```
To run only submission - note this will **not submit** if you've not yet validated successfully:
```shell
eva-sub-cli.py --metadata_xlsx <metadata file> --submission_dir <submission directory> --tasks SUBMIT --username <webin username> --password <webin password>
```

### Shallow validation
If you are working with large VCF files and find that validation takes a very long time, you can add the
argument `--shallow` to the command, which will validate only the first 10,000 lines in each VCF. Note that running
shallow validation will **not** be sufficient for actual submission but will allow you to identify most validation concerns without long run time.

### Validation tasks
To run only a subset of the validation steps, you can use the `--validation_tasks` argument.
This can be useful if you want to avoid re-running long-running validations that have already passed.
Note that all validation tasks must pass in order to submit. The report will aggregate the results of previous runs and new ones.
The possible tasks are:
* `vcf_check` - includes syntax validation and other checks on VCF files
* `assembly_check` - includes all checks involving the FASTA file
* `metadata_check` - includes syntactic and semantic checks on metadata
* `sample_check` - includes sample coherence checks between VCF files and metadata

For example, to run only `vcf_check` and `sample_check`:
```shell
eva-sub-cli.py --metadata_xlsx <metadata file> --submission_dir <submission directory> --validation_tasks vcf_check sample_check
```

### VCF files and reference FASTA
These can be provided either in the metadata file directly, or on the command line using the `--vcf_files` and
`--reference_fasta` options. Note that if you are using more than one reference FASTA, you **cannot** use the command 
line options; you must specify which VCF files use which FASTA files in the metadata.

VCF files can be either uncompressed or compressed using bgzip.
Other types of compression are not allowed and will result in errors during validation.
FASTA files must be uncompressed.

### Metadata JSON
Frequent submitters may be interested in using our [metadata JSON schema](https://github.com/EBIvariation/eva-sub-cli/blob/main/eva_sub_cli/etc/eva_schema.json)
instead of our spreadsheet template. The metadata requirements are the same regardless of which format you use, you will
just need to use the `--metadata_json` option instead of the `--metadata_xlsx` option.

### Running using Docker
If you've installed eva-sub-cli using Docker, make sure that Docker is running in the background before running 
eva-sub-cli, e.g. by opening Docker Desktop. Additionally, for each eva-sub-cli command, add the command line option 
`--executor docker`, which will fetch and manage the Docker container for you.

### Using Nextflow
Under the hood, eva-sub-cli uses Nextflow to run validation, which you can configure on the command line using the 
`--nextflow_config` option. For more information, please see [here](using_nextflow.md).
