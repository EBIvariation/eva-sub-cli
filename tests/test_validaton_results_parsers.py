import os.path
from unittest import TestCase

from eva_sub_cli.validators.validation_results_parsers import vcf_check_errors_is_critical, parse_assembly_check_log, \
    parse_assembly_check_report, parse_bcftools_norm_report


class TestValidationParsers(TestCase):
    resource_dir = os.path.join(os.path.dirname(__file__), 'resources')

    def test_vcf_check_errors_is_critical(self):
        errors = [
            ('INFO AC does not match the specification Number=A (expected 1 value(s)). AC=100,37.', False),
            ('Line 124385: Sample #10, field PL does not match the meta specification Number=G (expected 2 value(s)). '
             'PL=.. It must derive its number of values from the ploidy of GT (if present), or assume diploidy. '
             'Contains 1 value(s), expected 2 (derived from ploidy 1).', False),
            ('Line 124384: Sample #102, field AD does not match the meta specification Number=R (expected 3 value(s)). AD=..', False),
            ('Line 8: SAMPLE metadata Genomes is not a valid string (maybe it contains quotes?).', True),
            ('Line 6: FORMAT GQ metadata Type is not Integer.', False),
            ('Line 7: FORMAT PL metadata Number is not G.', False),
            ('Line 10: INFO AF metadata Number is not A.', True),
            ('Line 4039: FORMAT GQ metadata Type is not Integer.', False),
            ('Line 1525: Duplicated variant NA:5:C>T found.', True),
            ('Line 8: Metadata ID contains a character different from alphanumeric, dot, underscore and dash.', True),
            ('Line 14: FORMAT metadata Number is not a number, A, G or dot.', True),
            ('Line 13: Contig is not sorted by position. Contig 1 position 5600263 found after 12313283.', True),
            ('Line 1067: INFO SVLEN must be equal to "length of ALT - length of REF" for non-symbolic alternate '
             'alleles. SVLEN=31, expected value=33.', False),
        ]
        for error, is_critical in errors:
            assert vcf_check_errors_is_critical(error) == is_critical, error

    def test_parse_assembly_check_log(self):
        assembly_check_log = os.path.join(self.resource_dir, 'assembly_check', 'invalid.vcf.assembly_check.log')
        error_list, nb_error, match, total = parse_assembly_check_log(assembly_check_log)
        assert error_list == ["The assembly checking could not be completed: Contig 'chr23' not found in assembly report"]

    def test_parse_assembly_check_report(self):
        assembly_check_report = os.path.join(self.resource_dir, 'assembly_check', 'invalid.vcf.text_assembly_report.txt')
        mismatch_list, nb_mismatch, error_list, nb_error = parse_assembly_check_report(assembly_check_report)
        assert mismatch_list[0] == "Line 43: Chromosome chr1, position 955679, reference allele 'T' does not match the reference sequence, expected 'C'"
        assert nb_mismatch == 12
        assert error_list == ['Chromosome scaffold_chr1 is not present in FASTA file']
        assert nb_error == 1

    def test_parse_bcftools_norm_report(self):
        normalisation_report = os.path.join(self.resource_dir, 'norm_check', 'invalid.vcf_bcftools_norm.log')
        error_list, nb_total, nb_split, nb_realigned, nb_skipped = parse_bcftools_norm_report(normalisation_report)
        assert error_list == [
            "NON_ACGTN_ALT	chr1	49338976	]chr1:49277505]T",
            "NON_ACGTN_ALT	chr1	49997014	TAT[chr1:50014208[",
            "NON_ACGTN_ALT	chr1	50014208	]chr1:49997014]ATT",
            "NON_ACGTN_ALT	chr1	191611692	[chr8:41723769[A"
        ]
        assert nb_total == 152
        assert nb_split == nb_realigned == nb_skipped == 0
