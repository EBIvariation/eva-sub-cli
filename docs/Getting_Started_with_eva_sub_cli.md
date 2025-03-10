# Comprehensive overview of the required inputs for eva-sub-cli tool 

The eva-sub-cli tool requires the following inputs:

- One or several valid VCF files
- Completed metadata spreadsheet
- Reference genome in fasta format

The VCF file must adhere to official VCF specifications, and the metadata spreadsheet provides contextual information about the dataset. In the following sections, we will examine each of these inputs in detail.

# VCF File

A VCF (Variant Call Format) file is a type of file used in bioinformatics to store information about genetic variants. It includes data about the differences (or variants) between a sample's DNA and a reference genome. Typically, generating a VCF file involves several steps: preparing your sample, sequencing the DNA, aligning it to a reference genome, identifying variants, and finally, formatting this information into a VCF file. The overall goal is to systematically capture and record genetic differences in a standardised format. A VCF file consists of two main parts: the header and the body.

Header: The header contains metadata about the file, such as the format version, reference genome information, and descriptions of the data fields. Each line in the header starts with a double ##, except for the last header line which starts with a single #.

File format version

```
##fileformat=VCFv4.2
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##FILTER=<ID=PASS,Description="All filters passed">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">

```

Body: The body of the VCF file contains the actual variant data, with each row representing a single variant. The columns in the body are : CHROM, POS, ID, REF, ALT, QUAL, FILTER, INFO, FORMAT, Sample Columns

```
#CHROM  POS  ID  REF  ALT  QUAL  FILTER  INFO  FORMAT  [SampleIDs...]
``` 
Here's a small example to illustrate the structure of a VCF file: Example VCF file archived at EVA to be inserted 

# Metadata Spreadsheet

The spreadsheet provides comprehensive contextual information about the dataset, ensuring that each submission is accompanied by detailed descriptions that facilitate proper understanding and use of the data. Key elements included in the metadata spreadsheet are analysis and project information, sample information, sequencing methodologies, experimental details. 


| WORKSHEET           | EXPLANATION          |
| -----------------   | -------------------- |
|  Submitter Details   | This sheet captures the details of the submitter|
| Project           | The objective of this sheet is to gather general information about the Project including submitter, submitting centre, collaborators, project title, description and publications. |
| Sample            | Projects consist of analyses that are run on samples. We accept sample information in the form of BioSample, ENA or EGA accession(s). We also accept BioSamples sampleset accessions. If your samples are not yet accessioned, and are therefore novel, please use the "Novel sample(s)" sections of the Sample(s) worksheet to have them registered at BioSample |
| Analysis          | For EVA, each analysis is one vcf file, plus an unlimited number of ancillary files. This sheet allows EVA to link vcf files to a project and to other EVA analyses. Additionally, this worksheet contains experimental meta-data detailing the methodology of each analysis. Important to note; one project can have multiple associated analyses          |
| Files             | Filenames and associated checking data associated with this EVA submission should be entered into this worksheet. Each file should be linked to exactly one analysis.            |


# Validation checks 

The CLI tool performs the following validation checks and generates corresponding reports:

- Metadata check to ensure that the metadata fields have been correctly filled in
- VCF check to ensure that the VCF file follows the VCF format specification
- Assembly check to ensure that the genome and the VCF match
- Sample name check to ensure that the samples in the metadata can be associated with the sample in the VCF

In the following sections, we will examine each of these checks in detail, starting with the Metadata check.

# Metadata check

Once the user passes the metadata spreadsheet for validation checks, the eva-sub-cli tool verifies that all mandatory columns, marked in bold in the spreadsheet, are filled in. This data is crucial for further validation processes, such as retrieving the INDSC accession of the reference genome used to call the variants, and for sample and project metadata. If any mandatory columns or sheets are missing, the CLI tool will raise errors.

Key points to note before validating your metadata spreadsheet with the eva-sub-cli tool:

- Please do not change the existing structure of the spreadsheet
- Ensure all mandatory columns (marked in bold) are filled.
- Pre-registered samples must be released and not kept in private status
- Sample names in the spreadsheet must match those in the VCF file.
- Analysis aliases must match across the sheets (Analysis, Sample, and File sheets).

Common Errors Seen with Metadata Checks:

- Analysis alias is not filled in for the respective samples in the Sample’s tab .
- Reference field is not filled with an INSDC accession. Submitters can sometimes use a non-GCA accession or generic assembly name as their reference genome.
- Tax ID and the scientific name of the organism do not match.
- Collection data and geographic location of the samples are not filled if the samples being submitted are novel.

# VCF Checks

Ensuring data consistency upon submission is crucial for interoperability and supporting cross-study comparative genomics. Before accepting a VCF submission, the cli tool verifies that the submitted information adheres to the official VCF specifications. Additionally, submitted variants must be supported by either experimentally determined sample genotypes or population allele frequencies.

Key points to note before validating your VCF file with the eva-sub-cli tool:

- File Format Version: Always start the header with the version number (versions 4.1, 4.2, and 4.3 are accepted).
- Header Metadata: Should include the reference genome, information fields (INFO), filters (FILTER), AF and  genotype metadata
- Variant Information: VCF files must provide either sample genotypes and/or aggregated sample summary-level allele frequencies.
- Unique Variants: Variant lines should be unique and not specify duplicate loci.
- Reference Genome: All variants must be submitted with positions on a reference genome accessionned by a member of the INSDC consortium  [Genbank](https://www.ncbi.nlm.nih.gov/genbank/), [ENA](https://www.ebi.ac.uk/ena/browser/home), or [DDBJ](https://www.ddbj.nig.ac.jp/index-e.html).

Common Errors Seen with VCF Checks:

- The VCF version is not one of 4.1, 4.2, or 4.3.
- The VCF file contains extra spaces, blanks, or extra quotations causing validation to fail. Tools like bcftools can help verify the header before validating the file.
- GT and AF fields are not defined in the header section.
- VCF uses non-GCA contig alias
- The fields used do not conform to the official VCF specifications 

# Assembly Check

The EVA requires that all variants be submitted with an asserted position on an INSDC sequence. This means that the reference allele for every variant must match a position in a sequence that has been accessioned in either the GenBank or ENA database. Aligning all submitted data with INSDC sequences enables integration with other EMBL-EBI resources, including Ensembl, and is crucial for maintaining standardisation at the EVA. Therefore, all sequence identifiers in your VCF must match those in the reference FASTA file.

Key points to note before validating your data with the eva-sub-cli Tool:

- Ensure that the reference sequences in the FASTA file used to call the variants are accessioned in INSDC.
- Verify that the VCF file does not use non-GCA contig aliases by cross-checking with the reference assembly report.

 Common errors seen with assembly checks:
 
- VCF file uses a non-GCA contig alias causing the assembly check to fail
- Contigs used do not exist in the assembly report of the reference genome
- Major Allele Used as REF Allele: This typically occurs when a specific version of Plink or Tassel is used to create VCF files, causing the tool to use the major allele as the reference allele. In such cases, submitters should use the GCA FASTA sequence to create corrected files.

# Sample Name Concordance Check

The sample name concordance check ensures that the sample names in the metadata spreadsheet match those in the VCF file. This is achieved by cross-checking the 'Sample name in VCF' column in the spreadsheet with the sample names registered in the VCF file. Any discrepancies must be addressed by the submitter when the CLI tool generates a report of the  mismatches found.

Key points to note before validating your data with the eva-sub-cli tool:

- Ensure that sample names between the VCF file and the metadata spreadsheet match. This comparison is case-sensitive.
- Ensure there are no extra spaces in the sample names.

Common errors seen with sample concordance checks:

- Link between “Sample” and “File” provided via the Analysis alias is not correctly defined in the metadata which causes the sample name concordance check to fail.
- Extra white spaces in the sample names can lead to mismatches.
- Case sensitivity issues between the sample names in the VCF file and the metadata spreadsheet.


