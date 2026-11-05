"""
Computation of GA4GH sequence collections (https://ga4gh.github.io/refget/seqcols/) from a FASTA file.
"""
import base64
import hashlib
import json

from eva_sub_cli.file_utils import fasta_iter

# Attributes included in the level 2 representation of the sequence collection
SEQCOL_ATTRIBUTES = ('names', 'lengths', 'sequences')
# Attributes contributing to the top level (level 0) digest
INHERENT_ATTRIBUTES = ('names', 'sequences')


def sha512t24u_digest(data):
    """GA4GH digest: base64url encoding of the first 24 bytes of the SHA-512 hash of the data."""
    if isinstance(data, str):
        data = data.encode('utf-8')
    return base64.urlsafe_b64encode(hashlib.sha512(data).digest()[:24]).decode('ascii')


def canonical_json(obj):
    """
    Serialise to canonical JSON (RFC-8785). This implementation is sufficient for objects and arrays containing
    strings and integers, which is all that the sequence collection attributes use.
    """
    return json.dumps(obj, separators=(',', ':'), sort_keys=True, ensure_ascii=False, allow_nan=False).encode('utf-8')


def refget_sequence_digest(sequence):
    """Refget v2 identifier of a sequence."""
    return 'SQ.' + sha512t24u_digest(sequence.upper())


def level1_digests(collection):
    """Digest of each attribute of a level 2 sequence collection."""
    return {attribute: sha512t24u_digest(canonical_json(collection[attribute])) for attribute in SEQCOL_ATTRIBUTES}


def level0_digest(level1):
    """Top level digest of a sequence collection, computed from the level 1 digests of the inherent attributes."""
    return sha512t24u_digest(canonical_json({attribute: level1[attribute] for attribute in INHERENT_ATTRIBUTES}))


def sequence_collection_from_fasta(input_fasta):
    """
    Calculate the sequence collection of a FASTA file.
    :param input_fasta: path to the (optionally gzipped) FASTA file
    :returns: dict with the level 0 digest and the level 2 attributes (names, lengths, sequences)
    """
    collection = {attribute: [] for attribute in SEQCOL_ATTRIBUTES}
    for header, sequence in fasta_iter(input_fasta):
        collection['names'].append(header.split()[0])
        collection['lengths'].append(len(sequence))
        collection['sequences'].append(refget_sequence_digest(sequence))
    return {'digest': level0_digest(level1_digests(collection)), **collection}
