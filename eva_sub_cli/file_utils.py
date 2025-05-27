import glob
import gzip
import os
import shutil
import time
from itertools import groupby


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