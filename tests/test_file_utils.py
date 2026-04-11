import glob
import os
import shutil
from pathlib import Path
from unittest import TestCase

from eva_sub_cli.file_utils import DirLock, DirLockError


def set_up_test_dir():
    os.makedirs('backup_test/nested/dir', exist_ok=True)
    Path('backup_test/file.txt').touch()


def clean_up():
    for file_name in glob.glob('backup_test**'):
        shutil.rmtree(file_name)


class TestDirLock(TestCase):
    resources_folder = os.path.join(os.path.dirname(__file__), 'resources')

    def setUp(self) -> None:
        self.lock_folder = os.path.join(self.resources_folder, 'locked_folder')
        os.makedirs(self.lock_folder)

    def tearDown(self) -> None:
        shutil.rmtree(self.lock_folder)

    def test_create_lock(self):
        with DirLock(self.lock_folder) as lock:
            assert os.path.isfile(lock._lockfilename)
        assert not os.path.exists(lock._lockfilename)

    def test_prevent_create_2_lock(self):
        with DirLock(self.lock_folder) as lock:
            assert os.path.isfile(lock._lockfilename)
            with self.assertRaises(DirLockError):
                with DirLock(self.lock_folder) as lock2:
                    pass
            assert os.path.isfile(lock._lockfilename)
        assert not os.path.exists(lock._lockfilename)

    def test_lock_with_exception(self):
        try:
            with DirLock(self.lock_folder) as lock:
                assert os.path.isfile(lock._lockfilename)
                raise Exception()
        except Exception:
            pass
        assert not os.path.exists(lock._lockfilename)
