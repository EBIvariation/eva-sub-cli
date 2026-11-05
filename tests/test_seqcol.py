import json
import os
from tempfile import TemporaryDirectory
from unittest import TestCase

from eva_sub_cli.seqcol import sha512t24u_digest, canonical_json, sequence_collection_from_fasta, level1_digests, \
    refget_sequence_digest


class TestSeqcol(TestCase):
    resource_dir = os.path.join(os.path.dirname(__file__), 'resources', 'seqcol')

    def setUp(self):
        # Expected digests come from the GA4GH refget test suite (refgenie/refget test_fasta/test_fasta_digests.json)
        with open(os.path.join(self.resource_dir, 'expected_digests.json')) as open_json:
            self.expected = json.load(open_json)

    def test_sha512t24u_digest(self):
        assert sha512t24u_digest(b'') == 'z4PhNX7vuL3xVChQ1m2AB9Yg5AULVxXc'
        assert sha512t24u_digest('ACGT') == 'aKF498dAxcJAqme6QYQ7EZ07-fiw8Kw2'

    def test_canonical_json(self):
        assert canonical_json(['chr1', 'chr2']) == b'["chr1","chr2"]'
        assert canonical_json([8, 4]) == b'[8,4]'
        assert canonical_json({'sequences': 'b', 'names': 'a'}) == b'{"names":"a","sequences":"b"}'

    def test_refget_sequence_digest_case_insensitive(self):
        assert refget_sequence_digest('acgt') == refget_sequence_digest('ACGT') == 'SQ.aKF498dAxcJAqme6QYQ7EZ07-fiw8Kw2'

    def test_sequence_collection_from_fasta(self):
        for fasta_name, expected in self.expected.items():
            collection = sequence_collection_from_fasta(os.path.join(self.resource_dir, fasta_name))
            assert collection['digest'] == expected['digest'], fasta_name
            assert level1_digests(collection) == expected['level1'], fasta_name
            assert {k: collection[k] for k in expected['level2']} == expected['level2'], fasta_name

    def test_sequence_collection_lowercase_and_multiline_fasta(self):
        with TemporaryDirectory() as tmp_dir:
            fasta = os.path.join(tmp_dir, 'lower.fa')
            with open(fasta, 'w') as open_file:
                open_file.write('>chrX description\nttgg\nggaa\n>chr1\nggaa\n>chr2\ngcgc\n')
            collection = sequence_collection_from_fasta(fasta)
        assert collection['digest'] == self.expected['base.fa']['digest']
