# Overview of Input Files 

The eva-sub-cli tool requires the following inputs:

- One or several valid VCF files
- Reference genome in FASTA format
- Completed metadata spreadsheet

VCF files can be either uncompressed or compressed using bgzip.
Other types of compression are not allowed and will result in errors during validation.
FASTA files must be uncompressed.

Only the metadata file is passed directly to the CLI tool. The VCF and FASTA files should be referenced from the 
metadata file.

The VCF file must adhere to official VCF specifications, and the metadata spreadsheet provides contextual information 
about the dataset. In the following sections, we will examine each of these inputs in detail.

## VCF File

A VCF (Variant Call Format) file is a type of file used in bioinformatics to store information about genetic variants.
It includes data about the differences (or variants) between a sample's DNA and a reference genome. Typically, 
generating a VCF file involves several steps: preparing your sample, sequencing the DNA, aligning it to a 
reference genome, identifying variants, and finally, formatting this information into a VCF file. The overall goal is
to systematically capture and record genetic differences in a standardised format. 

A VCF file consists of two main parts: the header and the body.

Header: The header contains metadata about the file, such as the format version, reference genome information, and 
descriptions of the data fields. Each line in the header starts with a double ##, except for the last header line which
starts with a single #.

```
##fileformat=VCFv4.2
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##FILTER=<ID=PASS,Description="All filters passed">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
```

Body: The body of the VCF file contains the actual variant data, with each row representing a single variant. The 
columns in the body are: CHROM, POS, ID, REF, ALT, QUAL, FILTER, INFO, FORMAT, Sample Columns

```
#CHROM  POS  ID  REF  ALT  QUAL  FILTER  INFO  FORMAT  [SampleIDs...]
```

## FASTA File

This is the reference genome that your variants were called against, in uncompressed FASTA format. The EVA uses this to
check that the reference alleles are set correctly in the VCF files.

The reference genome must be INSDC-registered, which means it is publicly available in one of the archives within the
INSDC consortium: [Genbank](https://www.ncbi.nlm.nih.gov/genbank/), [ENA](https://www.ebi.ac.uk/ena/browser/home), or
[DDBJ](https://www.ddbj.nig.ac.jp/index-e.html). This ensures the long-term availability of the genome and the 
reusability of your data.

## Metadata Spreadsheet

The metadata spreadsheet provides comprehensive contextual information about the dataset, ensuring that each submission
is accompanied by detailed descriptions that facilitate proper understanding and use of the data. Key elements included
in the metadata spreadsheet are analysis and project information, sample information, sequencing methodologies, and
experimental details. While not all fields are required, users are strongly encouraged to provide as much information
as possible to enhance the completeness and usefulness of the metadata.

The spreadsheet is organized into editable tabs, designed for metadata entry, and non-editable helper tabs, which offer
detailed explanations and guidance for each column. Users are required to complete all relevant sections within the
editable tabs. Mandatory fields in each section are indicated in bold to highlight essential information that must be 
provided for a valid submission. Fields highlighted in green indicate an either/or choice. This means you should fill
in the choice most relevant for your submission, but not both.

Below we go through some important details for each of the tabs.

### Submitter Details

This sheet captures basic information about the person or team submitting the data. This includes the lab name and
center, which is the name of the submitting institution or organization and is the name that will be visible once the
project is live on the EVA website.

### Project

The objective of this sheet is to gather general information about the Project. If you are submitting to an existing
project, you can skip the other details and just provide the project accession and analyses will be linked to that 
project. In case of a new project, please provide the relevant details including submitter, submitting center, 
collaborators, project title, description and publications.

One important column to note is the Hold Date, which is the date until which the data should be kept private. EVA will
release the data automatically after this date. If it is missing, the default value is three days after the date of
submission.

### Analysis

For EVA, an analysis is a grouping of samples and data files. This sheet allows EVA to link VCF files to a project and
to other EVA analyses. Additionally, this worksheet contains experimental metadata detailing the methodology of each
analysis. This includes a local path to your reference FASTA file.

One project can have multiple associated analyses. EVA links analyses to samples and VCF files through the analysis 
alias, which is a shortened identifier you must provide for each analysis.

### Sample

This is where you describe the biological samples used for your analyses. Each row describes one sample and must include
Analysis Alias to indicate which analysis it belongs to, and Sample Name in VCF which is the exact name of the sample
as it appears in the VCF file.

We accept preregistered samples, which should be provided using BioSamples sample or sampleset accessions. Please
ensure these are publicly accessible, as otherwise EVA will not be able to validate them.

If your samples are not yet accessioned, and are therefore novel, please use the "Novel sample(s)" sections of the
Sample worksheet to have them registered at BioSamples. Make sure to fill in the required fields in bold, including the
taxonomy  ID, geographic location (chosen from the controlled vocabulary in the drop-down menu), and collection date 
(in YYYY-MM-DD format).

### Files

This sheet lists the VCF files in your submission. These should be provided as local paths within your system, so that
the CLI tool can locate them, along with the Analysis Alias which should be associated with each file. Each file should 
be linked to exactly one analysis.
