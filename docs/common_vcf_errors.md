# **Frequently encountered VCF validation issues** 

This section provides a curated overview of some of the common VCF validation errors. Each error is illustrated with a real validation output example, followed by a brief description about the error and the expected resolution for EVA submissions.

## 1. Duplicated Variants

**Example Validation Error**

```text
Line 31165: Duplicated variant 10:51781012:A>a found.
Line 31166: Duplicated variant 10:51781012:A>a found. It occurs in lines 31165 and 31166.
```

**Description**

This error indicates that the same variant appears more than once in the VCF file. A duplicated variant is defined as multiple records with identical:

* Chromosome  
* Position  
* Reference allele   
* Alternate allele 

**Additional context**

When you receive a validation error like Duplicated variant found, it means two lines in your VCF file are describing the exact same genetic change. Let's explore this further with a real-world VCF example. 

```text
#CHROM  POS       ID    REF        ALT    QUAL    FILTER   ...
4      15112781    .    TGGCCAG    T      7.71    PASS     ...
4      15112782    .    GGCCAGG    G      13.18   PASS     ...
```

At first glance, these look like two distinct variants because their positions and allele sequences are different. However, both vcf lines are trying to describe a 6-base pair deletion as shown below: 

```text
15112781
       |
       TGGCCAGG
       T------G

 15112782
        |
       TGGCCAGG
       TG------
```

**Resolution**

Duplicate variants are not permitted in EVA submissions. Please ensure all duplicate records are identified and removed prior to submission. One tools that can help in removing duplicate is [bcftools norm](https://samtools.github.io/bcftools/bcftools.html#norm)

```bash
bcftools norm -multiallelics -both --rm-dup all input.vcf > output.vcf
```


## 2. Variants not sorted by Genomic Position

**Example Validation Error**

```text
Line 54: Contig is not sorted by position. Contig chr1 position 666974 found after 1083338.  
Line 98: Contig is not sorted by position. Contig chr1 position 16620664 found after 16624328.
```

**Description**

VCF files must be sorted by chromosome/contig and genomic position in ascending order, otherwise validation error will be raised. 

**Resolution**

Ensure the VCF file is sorted by chromosome/contig and genomic position in ascending order prior to submission. Possible ways to achieve this are shown below:

Option 1: Using bcftools  

```bash
bcftools sort input.vcf > output.vcf
```
Option 2: Using awk and sort 

```bash
awk '/^#/ {print; next} {print | "sort -k1,1 -k2,2n"}' input.vcf > output.vcf
```



## 3. Values Outside Allowed Range

**Example Validation Error**

```text
Line 4709805: INFO AF value does not lie in the interval [0,1]. AF=1.0005.

Line 39098: Sample #1, GP=164.33,0 value does not lie in the interval [0,1].

```

**Description**

This error indicates that one or more numeric values fall outside their permitted range. Certain VCF fields are expected to contain values within a defined interval (commonly \[0,1\]). 

**Resolution**

Ensure that all values in the affected fields fall within their expected range. Any values outside the permitted interval should be corrected or recalculated prior to submission.

```bash
Example 1: Invalid AF value

AF represents allele frequency and must not exceed 1.

Problematic record:
1 10583 . G A . PASS AF=1.0005

Corrected record:
1 10583 . G A . PASS AF=1.0
```

```bash
Example 2: Invalid GP value

GP values represent genotype probabilities and must fall within the range [0,1]

Problematic record:

1    250321  .  C  T  .  PASS  .  GT:GP  0/1:1.24,0.15,0.03

Corrected record:

1  250321  .  C  T  .  PASS  .  GT:GP  0/1:0.82,0.15,0.03
```



## 4. Invalid Reference Allele

**Example Validation Error**

```text
Line 91987: Reference is not a string of bases.
```

**Description**

This error indicates that the reference allele contains invalid characters. The REF field in a VCF file must consist only of valid nucleotide bases (A, C, G, T). Any other characters or formats are not permitted and violate VCF specification requirements.

**Resolution**

Please check the following before submission:

- Check that the REF allele contains valid bases
- Ensure that the VCF was generated against the same reference genome assembly declared in the submission metadata.
- If the VCF was generated using PLINK, check that the correct reference allele settings were used. When exporting VCF files using PLINK 2.0, use the appropriate reference FASTA option so that REF alleles are taken from the correct reference genome:

```bash
plink2 --vcf input.vcf --ref-from-fa reference.fa --export vcf --out output
```

## 5. Invalid Fileformat Declaration

**Example Validation Error**

```text
The fileformat declaration is not valid (the line must start with ##fileformat= and the value must be one of 'VCFv4.1', 'VCFv4.2', 'VCFv4.3' or 'VCFv4.4').
```

**Description**

This error indicates that the VCF header does not contain a valid file format declaration. The fileformat line is a mandatory header field and must follow the required structure and accepted version values. 

**Resolution**

Ensure that the fileformat declaration is correctly defined in the VCF header using a supported version and the required format before submission.


Problematic header:

```text
##fileformat=VCFv4.5
```

Example of a supported header:

```text
##fileformat=VCFv4.2
```


## 6. Missing Contig Definition (warning) 

**Example Validation Error**

```text
Chromosome/contig '13' is not described in a 'contig' meta description. (warning)
```

**Description**

This warning indicates that a chromosome or contig referenced in the VCF records is not defined in the header. Each contig used in the VCF file should have a corresponding entry in the header describing it as without this there would be errors further down in our submission pipeline. 

**Resolution**

Ensure that all contigs referenced in the VCF file are properly defined in the header using contig meta-information lines before submission.

Problematic header:

```text
##fileformat=VCFv4.2
#CHROM  POS  ID  REF  ALT  QUAL  FILTER  INFO
13     32936732  .  G  A    .    PASS    .
```
Header with contig definition added:

```text
##fileformat=VCFv4.2
##contig=<ID=13,length=114364328>
#CHROM  POS  ID  REF  ALT  QUAL  FILTER  INFO
13      32936732 . G   A    .    PASS    .
```

## 7. Invalid Genotype Format

**Example Validation Error**

```text
Critical error: Line 23: Sample #77 does not start with a valid genotype.
```

**Description**

This error indicates that the genotype (GT) field for a sample is not in a valid format. The GT field must follow the standard VCF genotype representation, typically consisting of allele values separated by either / or | 

**Resolution**

Ensure that all genotype values are correctly formatted according to VCF specifications before submission. Example command to inspect genotype fields

```bash
bcftools query -f '%CHROM\t%POS[\t%GT]\n' input.vcf
```

## 8. Invalid INFO Field Format and Cardinality

**Example Validation Errors**

```text
Critical error: Line 119: Info field value is not a comma-separated list of valid strings (maybe it contains whitespaces?).

Critical error: Line 186: Info key is not a sequence of alphanumeric and/or punctuation characters

​​Critical error: Line 115: INFO ConfidenceInterval does not match the meta specification Number=A (expected 1 value(s)). ConfidenceInterval=0.1554,0.3237.

Line 2805: INFO TYPE does not match the meta specification Number=A (expected 2 value(s)). TYPE=snp.
```

**Description**

These errors indicate that the INFO field is not correctly defined or does not match its expected format. INFO field keys must use valid characters, values must be provided as scalar values or simple comma-separated lists, and the number of values must match the corresponding header definition. 

**Resolution**

Ensure that INFO field keys use valid characters, values are formatted as scalar values or simple comma-separated lists, and the number of values matches the corresponding header definition before submission. 

Example command to inspect INFO header definitions

```bash
bcftools view -h input.vcf | grep "^##INFO"
```

Example command to inspect INFO fields in variant records

```bash
bcftools query -f '%CHROM\t%POS\t%INFO\n' input.vcf
```


## 9. Identical Reference and Alternate Alleles

**Example Validation Error**

```text
Line 25551: Reference and alternate alleles must not be the same.
```

**Description**

This error indicates that the reference (REF) and alternate (ALT) alleles are identical. In a valid VCF record, the REF and ALT fields must represent different alleles. 

**Resolution**

Ensure that the REF and ALT fields contain different allele values before submission.

Example command to identify records where REF and ALT are identical

```bash
awk '!/^#/ && $4 == $5' input.vcf
```


## 10. Invalid Quality Value

**Example Validation Error**

```text
Line 29: Quality is not a single dot or a positive number.
```

**Description**

This error indicates that the QUAL field is not correctly formatted.The QUAL field must contain either a positive numeric value or a single dot (.) to indicate a missing value. 

**Resolution**

Ensure that the QUAL field contains either a valid positive number or a dot (.) where the value is missing before submission.

Example command to inspect QUAL values

```bash
bcftools query -f '%CHROM\t%POS\t%QUAL\n' input.vcf
```


## 11. Incorrect SVLEN Value

**Example Validation Error**

```text
Line 54: INFO SVLEN must be equal to "length of ALT - length of REF" for non-symbolic alternate alleles. SVLEN=6, expected value=-6.
```
**Description**

This error indicates that the SVLEN value in the INFO field does not match the expected value based on the REF and ALT alleles. For non-symbolic alternate alleles, SVLEN must correspond to the difference in length between the ALT and REF sequences. 

**Resolution**

Ensure that the SVLEN value correctly reflects the difference in length between the ALT and REF alleles before submission.

Example command to inspect structural variant annotations

```bash
bcftools query -f '%CHROM\t%POS\t%INFO/SVTYPE\t%INFO/SVLEN\n' input.vcf
```


## 12 Major allele used as REF allele (Data consistency issue)


**Example** 

```text
##INFO=<ID=PR,Number=0,Type=Flag,Description="Provisional reference allele, may not be based on real reference genome">

Line 51: Chromosome NC_040252.1, position 303453, reference allele 'G' does not match the reference sequence, expected 'T'
```

**Description**

This is a known behaviour of PLINK, which by default may assign the major allele as the reference allele if not explicitly instructed otherwise. As a result, the REF field in the VCF may not correspond to the actual reference genome used for submission. 

**Resolution**

When generating VCF files using PLINK 2.0, use the `--ref-from-fa` option to ensure that reference alleles are derived from the correct FASTA reference genome file.

Example command when exporting VCFs with PLINK 2.0

```bash
plink2 --vcf input.vcf --ref-from-fa reference.fa --export vcf --out output
```

## 13. Sample Count Mismatch  

**Example Validation Error** 

```text
Line 124: The number of samples must match those listed in the header line.
```

**Description**

This error indicates that the number of sample columns in the VCF data does not match the number of samples defined in the header. The header line specifies the sample identifiers, and each record must contain the same number of sample entries. 

**Resolution**

Ensure that the number of sample columns in all records matches the number of samples defined in the header before submission.

Example command to detect records with inconsistent sample column counts


```bash
awk '!/^#/ {print NF}' input.vcf | sort -u
```

This command reports the total number of columns present across variant records in the VCF file. In a correctly formatted VCF, all variant records should contain the same number of columns.


## 14. Missing Newline at End of File

**Example Validation Error** 

```text
Critical error: Line 15: There is no newline at the end of the file.
```

**Description**

This error indicates that the VCF file does not end with a newline character. VCF files must end with a newline to ensure proper parsing and compliance with file formatting requirements. 

**Resolution**

Ensure that the VCF file ends with a newline character before submission. One way to achieve this is shown below:

Example command to add a newline character to the end of the file

```bash
sed -i -e '$a\' input.vcf
```

## 15. INFO and FORMAT Fields not defined in header (warnings)

**Example Validation Errors**

```text
INFO 'SVTYPE' is not defined in the header, assuming Type=String

INFO 'END' is not defined in the header, assuming Type=String

INFO 'SVLEN' is not defined in the header, assuming Type=String

INFO 'AF' is not defined in the header, assuming Type=String

INFO 'DP' is not defined in the header, assuming Type=String

FORMAT 'CN' is not defined in the header, assuming Type=String

FORMAT 'GT' is not defined in the header, assuming Type=String

FORMAT 'DP' is not defined in the header, assuming Type=String
```

**Description**

These warnings indicate that one or more INFO or FORMAT fields are present in the VCF records but are not defined in the header.

**Resolution**

All INFO and FORMAT fields used in the VCF must be explicitly defined in the header using \#\#INFO and \#\#FORMAT lines.

Example command to inspect INFO field definitions

```bash
bcftools view -h input.vcf | grep "^##INFO"
```

Example command to inspect FORMAT field definitions

```bash
bcftools view -h input.vcf | grep "^##FORMAT"
```
