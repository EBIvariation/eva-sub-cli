#!/usr/bin/env nextflow

nextflow.enable.dsl=2

def helpMessage() {
    log.info"""
    Validate a set of VCF files and metadata to check if they are valid to be submitted to EVA.

    Inputs:
            --vcf_files_mapping     csv file with the mappings for vcf files, fasta and assembly report
            --output_dir            output_directory where the reports will be output
            --metadata_json         Json file describing the project, analysis, samples and files
            --metadata_xlsx         Excel file describing the project, analysis, samples and files
            --schema_dir            Directory containing the JSON schemas used for validation
    """
}

params.vcf_files_mapping = null
params.output_dir = null
params.metadata_json = null
params.metadata_xlsx = null

// executables
params.executable = [
    "vcf_validator": "vcf_validator",
    "vcf_assembly_checker": "vcf_assembly_checker",
    "samples_checker": "samples_checker.py",
    "xlsx2json": "xlsx2json.py",
    "biovalidator": "biovalidator"
]
// validation tasks
params.validation_tasks = [ "vcf_check", "assembly_check", "samples_check", "metadata_check"]
// container validation dir (prefix for vcf files)
params.container_validation_dir = "/opt/vcf_validation"
// help
params.help = null

// Show help message
if (params.help) exit 0, helpMessage()


// Test input files
if (!params.vcf_files_mapping || !params.output_dir || (!params.metadata_json && !params.metadata_xlsx)) {
    if (!params.vcf_files_mapping)      log.warn('Provide a csv file with the mappings (vcf, fasta, assembly report) --vcf_files_mapping')
    if (!params.metadata_xlsx)           log.warn('Provide a json file with the metadata description of the project and analysis --metadata_json')
    if (!params.output_dir)             log.warn('Provide an output directory where the reports will be copied using --output_dir')
    if (!params.metadata_json && !params.metadata_xlsx)   log.warn('Provide a json or Excel file with the metadata description of the project and analysis --metadata_json or --metadata_xlsx')
    exit 1, helpMessage()
}


workflow {
    vcf_channel = Channel.fromPath(params.vcf_files_mapping)
        .splitCsv(header:true)
        .map{row -> tuple(
            file(params.container_validation_dir+row.vcf),
            file(params.container_validation_dir+row.fasta),
            file(params.container_validation_dir+row.report)
        )}

    if ("vcf_check" in params.validation_tasks) {
        check_vcf_valid(vcf_channel)
    }
    if ("assembly_check" in params.validation_tasks) {
        check_vcf_reference(vcf_channel)
    }
    if (params.metadata_xlsx && !params.metadata_json){
        convert_xlsx_2_json(params.metadata_xlsx, params.conversion_configuration)
        metadata_json = convert_xlsx_2_json.out.metadata_json
    } else{
        metadata_json = params.metadata_json
    }
    if ("metadata_check" in params.validation_tasks){
        metadata_json_validation(metadata_json)
    }
    if ("samples_check" in params.validation_tasks) {
        sample_name_concordance(metadata_json, params.container_validation_dir)
    }
}

/*
* Validate the VCF file format
*/
process check_vcf_valid {
    publishDir "$params.output_dir",
            overwrite: false,
            mode: "copy"

    input:
    tuple path(vcf), path(fasta), path(report)

    output:
    path "vcf_format/*.errors.*.db", emit: vcf_validation_db
    path "vcf_format/*.errors.*.txt", emit: vcf_validation_txt
    path "vcf_format/*.vcf_format.log", emit: vcf_validation_log

    """
    trap 'if [[ \$? == 1 ]]; then exit 0; fi' EXIT

    mkdir -p vcf_format
    $params.executable.vcf_validator -i $vcf -r database,text -o vcf_format --require-evidence > vcf_format/${vcf}.vcf_format.log 2>&1
    """
}

/*
* Validate the VCF reference allele
*/
process check_vcf_reference {
    publishDir "$params.output_dir",
            overwrite: true,
            mode: "copy"

    input:
    tuple path(vcf), path(fasta), path(report)

    output:
    path "assembly_check/*valid_assembly_report*", emit: vcf_assembly_valid
    path "assembly_check/*text_assembly_report*", emit: assembly_check_report
    path "assembly_check/*.assembly_check.log", emit: assembly_check_log

    when:
    "assembly_check" in params.validation_tasks

    """
    trap 'if [[ \$? == 1 || \$? == 139 ]]; then exit 0; fi' EXIT

    mkdir -p assembly_check
    $params.executable.vcf_assembly_checker -i $vcf -f $fasta -a $report -r summary,text,valid  -o assembly_check --require-genbank > assembly_check/${vcf}.assembly_check.log 2>&1
    """
}


process convert_xlsx_2_json {
    publishDir "$params.output_dir",
            overwrite: true,
            mode: "copy"

    input:
    path(metadata_xlsx)
    path(conversion_configuration)

    output:
    path "metadata.json", emit: metadata_json

    script:
    metadata_json = metadata_xlsx.getBaseName() + '.json'

    """
    $params.executable.xlsx2json --metadata_xlsx $metadata_xlsx --metadata_json metadata.json --conversion_configuration $conversion_configuration
    """
}

process metadata_json_validation {
    publishDir "$params.output_dir",
            overwrite: true,
            mode: "copy"

    input:
    path(metadata_json)

    output:
    path "metadata_validation.txt", emit: metadata_validation

    script:
    """
    $params.executable.biovalidator --schema $params.schema_dir/eva_schema.json --ref $params.schema_dir/eva-biosamples.json --data $metadata_json > metadata_validation.txt
    """
}

process sample_name_concordance {
    publishDir "$params.output_dir",
            overwrite: true,
            mode: "copy"

    input:
    path(metadata_json)
    path(vcf_dir)

    output:
    path "sample_checker.yml", emit: sample_checker_yml

    script:
    """
    $params.executable.samples_checker --metadata_json $metadata_json --vcf_dir_prefix $vcf_dir --output_yaml sample_checker.yml
    """
}
