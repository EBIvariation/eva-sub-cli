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
    """
}

params.vcf_files_mapping = null
params.output_dir = null
params.metadata_json = null
params.metadata_xlsx = null

// executables - external tools
params.executable = [
    "vcf_validator": "vcf_validator",
    "vcf_assembly_checker": "vcf_assembly_checker",
    "biovalidator": "biovalidator"
]
// python scripts - installed as part of eva-sub-cli
params.python_scripts = [
    "samples_checker": "samples_checker.py",
    "fasta_checker": "check_fasta_insdc.py",
    "xlsx2json": "xlsx2json.py",
    "semantic_checker": "check_metadata_semantics.py"
]
// prefix to prepend to all provided path
params.base_dir = ""
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

schema_dir = file(projectDir).parent + '/etc'
conversion_configuration = schema_dir + '/spreadsheet2json_conf.yaml'

def joinBasePath(path) {
    if (path){
        return params.base_dir + '/' + path
    }
    return 'NO_FILE'
}

output_dir = joinBasePath(params.output_dir)

workflow {
    // Prepare the file path
    vcf_channel = Channel.fromPath(joinBasePath(params.vcf_files_mapping))
        .splitCsv(header:true)
        .map{row -> tuple(
            file(joinBasePath(row.vcf)),
            file(joinBasePath(row.fasta)),
            file(joinBasePath(row.report))
        )}
    vcf_files = Channel.fromPath(joinBasePath(params.vcf_files_mapping))
        .splitCsv(header:true)
        .map{row -> file(joinBasePath(row.vcf))}

    // VCF checks
    check_vcf_valid(vcf_channel)
    check_vcf_reference(vcf_channel)

    generate_file_size_and_md5_digests(vcf_files)
    collect_file_size_and_md5(generate_file_size_and_md5_digests.out.file_size_and_digest_info.collect())


    // Metadata conversion
    if (params.metadata_xlsx && !params.metadata_json){
        convert_xlsx_2_json(joinBasePath(params.metadata_xlsx))
        metadata_json = convert_xlsx_2_json.out.metadata_json
    } else {
        metadata_json = joinBasePath(params.metadata_json)
    }
    if (metadata_json) {
        // Metadata checks and concordance checks
        metadata_json_validation(metadata_json)
        sample_name_concordance(metadata_json, vcf_files.collect())
        fasta_to_vcfs = Channel.fromPath(joinBasePath(params.vcf_files_mapping))
            .splitCsv(header:true)
            .map{row -> tuple(file(joinBasePath(row.fasta)), file(joinBasePath(row.vcf)))}
            .groupTuple(by:0)
        insdc_checker(metadata_json, fasta_to_vcfs)
    }
}

/*
* Validate the VCF file format
*/
process check_vcf_valid {
    publishDir output_dir,
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
    publishDir output_dir,
            overwrite: true,
            mode: "copy"

    input:
    tuple path(vcf), path(fasta), path(report)

    output:
    path "assembly_check/*text_assembly_report*", emit: assembly_check_report
    path "assembly_check/*.assembly_check.log", emit: assembly_check_log

    script:
    def report_opt = report.name != 'NO_FILE' ? "-a $report" : ''

    """
    trap 'if [[ \$? == 1 || \$? == 139 ]]; then exit 0; fi' EXIT

    mkdir -p assembly_check
    $params.executable.vcf_assembly_checker -i $vcf -f $fasta $report_opt -r summary,text  -o assembly_check --require-genbank > assembly_check/${vcf}.assembly_check.log 2>&1
    """
}

process generate_file_size_and_md5_digests {
    input:
    path(vcf_file)

    output:
    path "${vcf_file}_file_size_and_digest_info.txt", emit: file_size_and_digest_info

    script:
    // Capture the realpath of the vcf to be able to resolve the file based on path instead of name
    """
     echo "\$(md5sum $vcf_file | awk '{print \$1}') \$(stat -c%s $vcf_file) \$(readlink -f $vcf_file)" > ${vcf_file}_file_size_and_digest_info.txt
    """
}

process collect_file_size_and_md5 {
    publishDir output_dir,
            overwrite: true,
            mode: "copy"

    input:
    path(file_size_and_digests)

    output:
    path "file_info.txt", emit: file_info_log

    script:
    """
    cat $file_size_and_digests > file_info.txt
    """
}


process convert_xlsx_2_json {
    publishDir output_dir,
            overwrite: true,
            mode: "copy"

    input:
    path(metadata_xlsx)

    output:
    path "metadata.json", emit: metadata_json, optional: true
    path "metadata_conversion_errors.yml", emit: errors_yaml

    script:
    metadata_json = metadata_xlsx.getBaseName() + '.json'

    """
    $params.python_scripts.xlsx2json --metadata_xlsx $metadata_xlsx --metadata_json metadata.json --errors_yaml metadata_conversion_errors.yml --conversion_configuration $conversion_configuration
    """
}

process metadata_json_validation {
    publishDir output_dir,
            overwrite: true,
            mode: "copy"

    input:
    path(metadata_json)

    output:
    path "metadata_validation.txt", emit: metadata_validation

    script:
    """
    $params.executable.biovalidator --schema $schema_dir/eva_schema.json --ref $schema_dir/eva-biosamples.json --data $metadata_json > metadata_validation.txt
    """
}

process sample_name_concordance {
    publishDir output_dir,
            overwrite: true,
            mode: "copy"

    input:
    path(metadata_json)
    path(vcf_files)

    output:
    path "sample_checker.yml", emit: sample_checker_yml

    script:
    """
    $params.python_scripts.samples_checker --metadata_json $metadata_json --vcf_files $vcf_files --output_yaml sample_checker.yml
    """
}


process insdc_checker {
    publishDir output_dir,
            overwrite: true,
            mode: "copy"

    input:
    path(metadata_json)
    tuple(path(fasta_file), path(vcf_files))

    output:
    path "${fasta_file}_check.yml", emit: fasta_checker_yml

    script:
    """
    $params.python_scripts.fasta_checker --metadata_json $metadata_json --vcf_files $vcf_files --input_fasta $fasta_file --output_yaml ${fasta_file}_check.yml
    """
}


process metadata_semantic_check {
    publishDir output_dir,
            overwrite: true,
            mode: "copy"

    input:
    path(metadata_json)

    output:
    path "metadata_semantic_check.yml", emit: metadata_semantic_check_yml

    script:
    """
    $params.python_scripts.semantic_checker --metadata_json $metadata_json --output_yaml metadata_semantic_check.yml
    """
}
