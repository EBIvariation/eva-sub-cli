import glob
import gzip
import os
import shutil
import time
from itertools import groupby

import pysam
from ebi_eva_common_pyutils.logger import logging_config

logger = logging_config.get_logger(__name__)


def resolve_single_file_path(file_path):
    files = glob.glob(file_path)
    if len(files) == 0:
        return None
    elif len(files) > 0:
        return files[0]


def is_submission_dir_writable(submission_dir):
    if not os.path.exists(submission_dir):
        os.makedirs(submission_dir)
    if not os.path.isdir(submission_dir):
        return False
    if not os.access(submission_dir, os.W_OK):
        return False
    return True


def is_vcf_file(file_path):
    if file_path:
        file_path = file_path.strip().lower()
        return file_path.endswith('.vcf') or file_path.endswith('.vcf.gz')
    return False

def associate_vcf_path_with_analysis(metadata, vcf_files):
    """
    Match the files names associated with analysis provided in the metadata with the given file path

    :param vcf_files the list of full path to the vcf files
    :param files_per_analysis: dictionary of the analysis and their associated VCF file names
    :returns dictionary of analysis and their associated vcf file path
    """
    result_files_per_analysis = dict()
    for analysis in metadata.files_per_analysis:
        result_files_per_analysis[analysis] = []
    for vcf_file in vcf_files:
        analysis_aliases = metadata.get_analysis_for_vcf_file(vcf_file)
        if len(analysis_aliases) == 1:
            result_files_per_analysis[analysis_aliases[0]].append(vcf_file)
        elif len(analysis_aliases) == 0:
            logger.error(f'No analysis found for vcf {vcf_file}')
            if 'No analysis' not in result_files_per_analysis:
                result_files_per_analysis['No analysis'] = []
            result_files_per_analysis['No analysis'].append(vcf_file)
        else:
            logger.error(f'More than one analysis were match to vcf {vcf_file}')

    return result_files_per_analysis

def detect_vcf_evidence_type(vcf_file):
    """
    Detect the type of evidence (genotype aggregation) provided in the VCF file by checking the first 10 data lines
    The evidence type is determined to be "genotype" (meaning genotype are all present) if a GT field can be found in
    all the samples. It is determined to be "allele_frequency" if it is not "genotype" and an AF field or AN and AC fields are found
    in every line checked.
    Otherwise, it returns None meaning that the evidence type could not be determined.
    """

    try:
        samples, af_in_info, gt_in_format = _assess_vcf_evidence_type_with_pysam(vcf_file)
    except Exception:
        logger.error(f"Pysam Failed to open and read {vcf_file}")
        try:
            samples, af_in_info, gt_in_format = _assess_vcf_evidence_type_manual(vcf_file)
        except Exception:
            logger.error(f"Manual parsing Failed to open or read {vcf_file}")
            return None
    if len(samples) > 0 and gt_in_format:
        return 'genotype'
    elif len(samples) == 0 and af_in_info:
        return 'allele_frequency'
    else:
        logger.error(f'Aggregation type could not be detected for {vcf_file}')
        return None


def _assess_vcf_evidence_type_with_pysam(vcf_file):
    with pysam.VariantFile(vcf_file, 'r') as vcf_in:
        samples = list(vcf_in.header.samples)
        # check that the first 10 lines have genotypes for all the samples present and if they have allele frequency
        nb_line_checked = 0
        max_line_check = 10
        gt_in_format = True
        af_in_info = True
        for vcf_rec in vcf_in:
            gt_in_format = gt_in_format and all('GT' in vcf_rec.samples.get(sample, {}) for sample in samples)
            af_in_info = af_in_info and ('AF' in vcf_rec.info or ('AC' in vcf_rec.info and 'AN' in vcf_rec.info))
            nb_line_checked += 1
            if nb_line_checked >= max_line_check:
                break
        return samples, af_in_info, gt_in_format


def _assess_vcf_evidence_type_manual(vcf_file):
    try:
        if vcf_file.endswith('.gz'):
            open_file = gzip.open(vcf_file, 'rt')
        else:
            open_file = open(vcf_file, 'r')

        nb_line_checked = 0
        max_line_check = 10
        gt_in_format = True
        af_in_info = True
        samples = []
        for line in open_file:
            sp_line = line.strip().split('\t')
            if line.startswith('#CHROM'):
                if len(sp_line) > 9:
                    samples = sp_line[9:]
            if not line.startswith('#'):
                gt_in_format = gt_in_format and len(sp_line) > 8 and 'GT' in sp_line[8]
                af_in_info = af_in_info and (
                        sp_line[7].find('AF=') or (sp_line[7].find('AC=') and sp_line[7].find('AN=')))
            if nb_line_checked >= max_line_check:
                break
        return samples, af_in_info, gt_in_format
    finally:
        open_file.close()


def backup_file_or_directory(file_name, max_backups=None):
    """
    Rename a file or directory by adding a '.1' at the end. If the '.1' file exists it move it to a '.2' and so on.
    Keep at most the specified number of backups, if None will keep all.
    """
    suffix = 1
    backup_name = f'{file_name}.{suffix}'
    while os.path.exists(backup_name):
        suffix += 1
        backup_name = f'{file_name}.{suffix}'

    for i in range(suffix, 1, -1):
        if max_backups and i > max_backups:
            if os.path.isfile(file_name):
                os.remove(f'{file_name}.{i - 1}')
            else:
                shutil.rmtree(f'{file_name}.{i - 1}')
        else:
            os.rename(f'{file_name}.{i - 1}', f'{file_name}.{i}')
    os.rename(file_name, file_name + '.1')


def open_gzip_if_required(input_file, mode='r'):
    """Open a file in read mode using gzip if the file extension says .gz"""
    if input_file.endswith('.gz'):
        return gzip.open(input_file, mode + 't')
    else:
        return open(input_file, mode)


def fasta_iter(input_fasta):
    """
    Given a fasta file. yield tuples of header, sequence
    """
    # first open the file outside
    with open_gzip_if_required(input_fasta) as open_file:
        # ditch the boolean (x[0]) and just keep the header or sequence since
        # we know they alternate.
        faiter = (x[1] for x in groupby(open_file, lambda line: line[0] == ">"))

        for header in faiter:
            # drop the ">"
            headerStr = header.__next__()[1:].strip()

            # join all sequence lines to one.
            seq = "".join(s.strip() for s in faiter.__next__())
            yield (headerStr, seq)


class DirLockError(Exception):
    pass


class DirLock(object):
    _SPIN_PERIOD_SECONDS = 0.05

    def __init__(self, dirname, timeout=3):
        """Prepare a file lock to protect access to dirname. timeout is the
        period (in seconds) after an acquisition attempt is aborted.
        The directory must exist, otherwise aquire() will timeout.
        """
        self._lockfilename = os.path.join(dirname, ".lock")
        self._timeout = timeout

    def acquire(self):
        start_time = time.time()
        while True:
            try:
                # O_EXCL: fail if file exists or create it (atomically)
                os.close(os.open(self._lockfilename,
                                 os.O_CREAT | os.O_EXCL | os.O_RDWR))
                break
            except OSError:
                if (time.time() - start_time) > self._timeout:
                    raise DirLockError(f"could not create {self._lockfilename} after {self._timeout} seconds")
                else:
                    time.sleep(self._SPIN_PERIOD_SECONDS)

    def release(self):
        try:
            os.remove(self._lockfilename)
        except OSError:
            pass

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, type_, value, traceback):
        self.release()
