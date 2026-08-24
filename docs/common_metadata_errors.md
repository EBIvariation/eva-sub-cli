# **Frequently encountered metadata errors** 

This section provides a curated overview of some of the common metadata errors. Each error is illustrated with a real validation output example, followed by a brief description of the error and the expected resolution for EVA submissions.

## 1. Missing mandatory metadata

**Example Validation Error** 

| **Sheet** | **Row** | **Column** | **Description** |
|---|---:|---|---|
| **Submitter Details** | **2** | **Center** | Column "Center" is not populated |

**Description**

The Center field is required but has been left empty in the Submitter Details sheet.

**Resolution** 

Populate all mandatory fields indicated in bold. EVA expects these fields to contain a valid value and not be left blank. 

For the Center field, provide the name of the submitting center/institution.

## 2. Invalid metadata values

**Example Validation Error** 

| Sheet | Row | Column | Description |
|---|---:|---|---|
| **Sample** | **3** | **Scientific Name** | Species *Homo sapens* does not match taxonomy 9606 (*Homo sapiens*). |

**Description**

The Scientific Name does not match the species associated with the submitted Taxonomy ID. In the above example, taxonomy ID 9606 corresponds to Homo sapiens and not Homo sapens.

**Resolution** 

Check that the metadata value is valid and follows the expected format or controlled vocabulary. 

## 3. Invalid metadata format 

**Example Validation Error** 

| Sheet | Row | Column | Description |
| --- | --- | --- | --- |
| **Submitter Details** | **2** | **Email Address** | Must match the `email` format. |

**Description**

The email address provided in the Submitter Details sheet does not match the expected email address format.

**Resolution**

Enter a valid email address in the Email Address field, for example, name@example.com.

For similar metadata validation errors, check the value against the format or allowed values expected by EVA and correct the metadata accordingly.

## 4. Project or Sample Not Publicly Accessible

**Example Validation Error** 

```text
Exception: PRJEBXXXXXX does not exist in ENA or is private

SAMNXXXXXXXX does not exist or is private

```

**Description**

The submitted project or sample accession cannot be found in ENA or is not publicly accessible. This may occur when the accession is incorrect, does not exist, or the corresponding object is still private.

**Resolution**

EVA cannot access or validate private objects. Make sure the project or sample has been released publicly before submitting it to EVA for validation.

## 5. NCBI BioSamples geographic location/collection date issue 

**Example Validation Error** 

| Sheet | Row | Column | Description |
|---|---:|---|---|
| **Sample** | **4** | **Sample Accession** | Error validating existing sample SAMN47377199: must have required property **'collection date'**. |
| **Sample** | **4** | **Sample Accession** | Error validating existing sample SAMN47377199: must have required property **'geographic location (country and/or sea)'**. |

**Description**

This error is due to a difference in reporting geographical location and collection date between NCBI BioSamples and ENA BioSamples. NCBI BioSamples uses property names "geo_loc_name" and "collection_date", whereas ENA uses "geographic location (country and/or sea)" and "collection date". EVA validates BioSamples against ENA's definition, which makes reusing NCBI BioSamples in a submission to EVA difficult to automate at the moment.

**Resolution** 

Once you have validated the rest of the data, contact eva-helpdesk@ebi.ac.uk to submit the data, as this will require manual intervention. Both NCBI and ENA are aware of this issue and we are working towards fixing this.

## 6. Either/Or Fields Completed Incorrectly

**Description**

Some metadata fields are highlighted in green to indicate an either/or requirement. Only one of the specified options should be completed. 

For example, in the Project tab, the submitter should complete either the Pre-registered Project section or the New Project section. Both sections should not be completed.

**Resolution** 

When fields are highlighted in green, check the available options and complete only the section that applies to the submission. Leave the other option blank.


## 7. Publication Field Not Completed Correctly 

**Description**

The Publication(s) field is optional, but when provided, the publication must be and given in the expected DB format. An example valid entry would be: PubMed:23128226

**Resolution** 

If publications related to the project are available, enter them using the required DB format, for example, PubMed:23128226. Multiple publications should be separated as specified in the metadata template. 
If there are no relevant publications, the field can be left blank and can be added later by contacting the EVA helpdesk team.