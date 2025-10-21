# Overview of Input Files 

The eva-sub-cli tool requires the following inputs:

- One or several valid VCF files
- Completed metadata spreadsheet
- Reference genome in fasta format

VCF files can be either uncompressed or compressed using bgzip.
Other types of compression are not allowed and will result in errors during validation.
FASTA files must be uncompressed.

The VCF file must adhere to official VCF specifications, and the metadata spreadsheet provides contextual information about the dataset. In the following sections, we will examine each of these inputs in detail.

# VCF File

A VCF (Variant Call Format) file is a type of file used in bioinformatics to store information about genetic variants. It includes data about the differences (or variants) between a sample's DNA and a reference genome. Typically, generating a VCF file involves several steps: preparing your sample, sequencing the DNA, aligning it to a reference genome, identifying variants, and finally, formatting this information into a VCF file. The overall goal is to systematically capture and record genetic differences in a standardised format. A VCF file consists of two main parts: the header and the body.

Header: The header contains metadata about the file, such as the format version, reference genome information, and descriptions of the data fields. Each line in the header starts with a double ##, except for the last header line which starts with a single #.

```
##fileformat=VCFv4.2
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##FILTER=<ID=PASS,Description="All filters passed">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
```

Body: The body of the VCF file contains the actual variant data, with each row representing a single variant. The columns in the body are: CHROM, POS, ID, REF, ALT, QUAL, FILTER, INFO, FORMAT, Sample Columns

```
#CHROM  POS  ID  REF  ALT  QUAL  FILTER  INFO  FORMAT  [SampleIDs...]
``` 

# Metadata Spreadsheet

The spreadsheet provides comprehensive contextual information about the dataset, ensuring that each submission is accompanied by detailed descriptions that facilitate proper understanding and use of the data. Key elements included in the metadata spreadsheet are analysis and project information, sample information, sequencing methodologies, experimental details.
The spreadsheet is organized into editable tabs, designed for metadata entry, and non-editable helper tabs, which offer detailed explanations and guidance for each column. Users are required to complete all relevant sections within the editable tabs. Mandatory fields in each section are indicated in bold to highlight essential information that must be provided for a valid submission. However, users are strongly encouraged to provide as much additional information as possible to enhance the completeness and usefulness of the metadata.

| WORKSHEET         | EXPLANATION                                                                                                                                                                                                                                                                                                                                                                                                        |
|-------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Submitter Details | This sheet captures the details of the submitter                                                                                                                                                                                                                                                                                                                                                                   |
| Project           | The objective of this sheet is to gather general information about the Project. If you are submitting to an existing project, you can skip the other details and just provide the project accession and analyses will be linked to that project. In case of a new project, please provide the relevant details including submitter, submitting centre, collaborators, project title, description and publications. |
| Sample            | Projects consist of analyses that are run on samples. We accept sample information in the form of BioSample, ENA or EGA accession(s). We also accept BioSamples sampleset accessions. If your samples are not yet accessioned, and are therefore novel, please use the "Novel sample(s)" sections of the Sample(s) worksheet to have them registered at BioSample                                                  |
| Analysis          | For EVA, each analysis is one vcf file, plus an unlimited number of ancillary files. This sheet allows EVA to link vcf files to a project and to other EVA analyses. Additionally, this worksheet contains experimental meta-data detailing the methodology of each analysis. Important to note; one project can have multiple associated analyses                                                                 |
| Files             | Filenames and associated checking data associated with this EVA submission should be entered into this worksheet. Each file should be linked to exactly one analysis.                                                                                                                                                                                                                                              |
