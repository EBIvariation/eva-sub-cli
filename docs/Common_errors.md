# **Frequently encountered VCF validation issues** 

# This section provides a curated overview of some of the common VCF validation errors. Each error is illustrated with a real validation output example, followed by a brief description about the error and the expected resolution for EVA submissions.

1. ## **Duplicated Variants**

**Example Validation Error**

Line 31165: Duplicated variant 10:51781012:A\>a found.

Line 31166: Duplicated variant 10:51781012:A\>a found. It occurs in lines 31165 and 31166\.

**Description**

This error indicates that the same variant appears more than once in the VCF file. A duplicated variant is defined as multiple records with identical:

* Chromosome  
* Position  
* Reference allele   
* Alternate allele 

**Additional context**