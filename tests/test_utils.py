import csv


def create_mapping_file(mapping_file, vcf_files, fasta_files, assembly_reports=None):
    with open(mapping_file, 'w', encoding='UTF8') as f:
        writer = csv.writer(f)
        writer.writerow(['vcf', 'fasta', 'report'])
        if not assembly_reports:
            assembly_reports = ['' for _ in range(len(vcf_files))]
        for vcf_file, fasta_file, assembly_reports in zip(vcf_files, fasta_files, assembly_reports):
            writer.writerow([vcf_file, fasta_file, assembly_reports])


def touch(file_path, content=''):
    with open(file_path, 'w') as open_file:
        open_file.write(content)