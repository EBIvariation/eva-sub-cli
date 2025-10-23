# Overview of Validation Checks 

The CLI tool performs the following validation checks and generates corresponding reports:

- Metadata check to ensure that the metadata fields have been correctly filled in
- VCF check to ensure that the VCF file follows the VCF format specification
- Assembly check to ensure that the genome and the VCF match
- Sample name check to ensure that the samples in the metadata can be associated with the sample in the VCF

In the following sections, we will examine each of these checks in detail, starting with the Metadata check.

## Metadata check

Once the user passes the metadata spreadsheet for validation checks, the eva-sub-cli tool verifies that all mandatory columns, marked in bold in the spreadsheet, are filled in. This data is crucial for further validation processes, such as retrieving the INDSC accession of the reference genome used to call the variants, and for sample and project metadata. If any mandatory columns or sheets are missing, the CLI tool will raise errors.

Key points to note before validating your metadata spreadsheet with the eva-sub-cli tool:

- Please do not change the existing structure of the spreadsheet
- Ensure all mandatory columns (marked in bold) are filled.
- Pre-registered project and samples must be released and not kept in private status
- Sample names in the spreadsheet must match those in the VCF file.
- Analysis aliases must match across the sheets (Analysis, Sample, and File sheets).

Common Errors Seen with Metadata Checks:

- Analysis alias is not filled in for the respective samples in the Sample’s tab .
- Reference field is not filled with an INSDC accession. Submitters can sometimes use a non-GCA accession or generic assembly name as their reference genome.
- Tax ID and the scientific name of the organism do not match.
- Collection data and geographic location of the samples are not filled if the samples being submitted are novel.

## VCF Checks

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

## Assembly Check

The EVA requires that all variants be submitted with an asserted position on an INSDC sequence. This means that the reference allele for every variant must match a position in a sequence that has been accessioned in either the GenBank or ENA database. Aligning all submitted data with INSDC sequences enables integration with other EMBL-EBI resources, including Ensembl, and is crucial for maintaining standardisation at the EVA. Therefore, all sequence identifiers in your VCF must match those in the reference FASTA file.

Key points to note before validating your data with the eva-sub-cli Tool:

- Ensure that the reference sequences in the FASTA file used to call the variants are accessioned in INSDC.
- Verify that the VCF file does not use non-GCA contig aliases by cross-checking with the reference assembly report.

 Common errors seen with assembly checks:
 
- VCF file uses a non-GCA contig alias causing the assembly check to fail
- Contigs used do not exist in the assembly report of the reference genome
- Major Allele Used as REF Allele: This typically occurs when a specific version of Plink or Tassel is used to create VCF files, causing the tool to use the major allele as the reference allele. In such cases, submitters should use the GCA FASTA sequence to create corrected files.

## Sample Name Concordance Check

The sample name concordance check ensures that the sample names in the metadata spreadsheet match those in the VCF file. This is achieved by cross-checking the 'Sample name in VCF' column in the spreadsheet with the sample names registered in the VCF file. Any discrepancies must be addressed by the submitter when the CLI tool generates a report of the  mismatches found.

Key points to note before validating your data with the eva-sub-cli tool:

- Ensure that sample names between the VCF file and the metadata spreadsheet match. This comparison is case-sensitive.
- Ensure there are no extra spaces in the sample names.

Common errors seen with sample concordance checks:

- Link between “Sample” and “File” provided via the Analysis alias is not correctly defined in the metadata which causes the sample name concordance check to fail.
- Extra white spaces in the sample names can lead to mismatches.
- Case sensitivity issues between the sample names in the VCF file and the metadata spreadsheet.
