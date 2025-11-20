# Overview of Validation Checks 

The CLI tool performs the following validation checks and generates corresponding reports:

- Metadata check to ensure that the metadata fields have been correctly filled in
- VCF check to ensure that the VCF file follows the VCF format specification
- Assembly check to ensure that the genome and the VCF match
- Sample name check to ensure that the samples in the metadata can be associated with the samples in the VCF

In the following sections, we will examine each of these checks in detail.

## Metadata Check

Once the user passes the metadata spreadsheet for validation checks, the eva-sub-cli tool verifies that all mandatory columns, marked in bold in the spreadsheet, are filled in.
This data is crucial for further validation processes, such as retrieving the INDSC accession of the reference genome used to call the variants, and for sample and project metadata.

Each tab in the spreadsheet has an associated help tab, which provides detailed instructions on how to fill in your metadata correctly.
If any mandatory columns or sheets are missing, the CLI tool will raise errors.

Key points to note before validating your metadata spreadsheet with the eva-sub-cli tool:

- Please do not change the existing structure of the spreadsheet.
- Ensure all mandatory columns (marked in bold) are filled.
- Columns marked in green indicate an either/or requirement, so only one of the sections should be filled in.
- Any pre-registered projects and samples must be released and not kept in private status.
- Sample names in the spreadsheet must match those in the VCF file.
- Analysis aliases must match across the sheets (Analysis, Sample, and File sheets).
- Use the Hold Date field in the Project sheet for data that needs to be kept under embargo.

Common errors seen with metadata checks:

- Analysis alias is not filled in for the respective samples in the Sample tab.
- Reference field in the Analysis tab is not filled with an INSDC accession. Submitters should not use a non-GCA accession or generic assembly name as their reference genome.
- Taxonomy ID and the scientific name of the organism do not match for novel samples.
- Collection date and geographic location of the samples are not filled in for novel samples.
- Date fields do not follow the YYYY-MM-DD format.
- Custom values are used for controlled vocabulary fields (indicated with a drop-down menu). Submitters should select from the values provided or contact us if the required value is not present.

Most issues around metadata will be reported in the "Metadata validation results" section of the validation report.
However, note that other validation failures may also require you to modify your metadata file.

## VCF Checks

Ensuring data consistency upon submission is crucial for interoperability and supporting cross-study comparative genomics.
Before accepting a VCF submission, the CLI tool verifies that the submitted information adheres to the official VCF specifications.
Additionally, submitted variants must be supported by either experimentally determined sample genotypes or population allele frequencies.

Key points to note before validating your VCF file with the eva-sub-cli tool:

- File Format Version: Always start the header with the VCF version number (versions 4.1-4 are accepted).
- Header Metadata: Should include the reference genome, information fields (INFO), filters (FILTER), AF and  genotype metadata
- Variant Information: VCF files must provide either sample genotypes and/or aggregated sample summary-level allele frequencies.
- Unique Variants: Variant lines should be unique and not specify duplicate loci.
- Reference Genome: All variants must be submitted with positions on a reference genome accessioned by a member of the INSDC consortium: [Genbank](https://www.ncbi.nlm.nih.gov/genbank/), [ENA](https://www.ebi.ac.uk/ena/browser/home), or [DDBJ](https://www.ddbj.nig.ac.jp/index-e.html).

Common errors seen with VCF checks:

- The VCF version is not one of 4.1, 4.2, 4.3, or 4.4.
- The VCF file contains extra spaces, blanks, or extra quotations causing validation to fail. Tools like bcftools can help verify the header before validating the file.
- GT and AF fields are not defined in the header section.
- The fields used do not conform to the official VCF specifications.

Issues in VCF format validation will be reported in the "VCF validation results" section of the validation report.
Issues in determining evidence type (genotypes or allele frequencies) are reported per analysis at the top of the report.

## Assembly Checks

The EVA requires that all variants be submitted with an asserted position on an INSDC sequence.
This means that the reference allele for every variant must match a position in a sequence that has been accessioned in the GenBank, ENA, or DDBJ databases.
Aligning all submitted data with INSDC sequences enables integration with other EMBL-EBI resources, including Ensembl, and is crucial for maintaining standardisation at the EVA.
This also means that all sequence identifiers in your VCF must match those in the reference FASTA file.

Key points to note before validating your data with the eva-sub-cli tool:

- Ensure that the reference sequences in the FASTA file used to call the variants are accessioned in INSDC.
- Verify that the contig names in the VCF file match those in the FASTA file.

 Common errors seen with assembly checks:
 
- VCF file uses contig name not found in the FASTA file, causing the assembly check to fail.
- Major Allele Used as REF Allele: This typically occurs when a specific version of Plink or Tassel is used to create VCF files, causing the tool to use the major allele as the reference allele. In such cases, submitters should use the GCA FASTA sequence to create corrected files.

Issues around reference allele matching in VCF files will be reported in the "VCF validation results" section of the validation report,
while issues around INSDC accessioning of the assembly will be reported in the "Reference genome INSDC check" section.

## Sample Name Concordance Check

The sample name concordance check ensures that the sample names in the metadata spreadsheet match those in the VCF file.
This is achieved by cross-checking the "Sample name in VCF" column in the spreadsheet with the sample names registered in the VCF file.
Any discrepancies must be addressed by the submitter when the CLI tool generates a report of the mismatches found.

Key points to note before validating your data with the eva-sub-cli tool:

- Ensure that sample names between the VCF file and the metadata spreadsheet match. This comparison is case-sensitive.
- Ensure there are no extra spaces in the sample names.

Common errors seen with sample concordance checks:

- Link between "Sample" and "File" provided via the Analysis alias is not correctly defined in the metadata which causes the sample name concordance check to fail.
- Extra white spaces in the sample names can lead to mismatches.
- Case sensitivity issues between the sample names in the VCF file and the metadata spreadsheet.

Issues in sample name concordance will be reported in the "Sample name concordance check" section of the validation report.