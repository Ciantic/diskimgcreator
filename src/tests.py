from diskimgcreator import try_create_image, _parse_size, _set_verbose
from diskimgmounter import try_mount_image
import unittest
import os
import datetime

_set_verbose(True)


class TestParseSize(unittest.TestCase):
    def test_parse_size(self):
        self.assertEqual(_parse_size("5.5"), 5.5 * 1000 ** 2)
        self.assertEqual(_parse_size("100KB"), 1000 * 100)
        self.assertEqual(_parse_size("1KiB"), 1024)
        self.assertEqual(_parse_size("1MB"), 1000 * 1000)
        self.assertEqual(_parse_size("1MiB"), 1024 * 1024)
        self.assertEqual(_parse_size("1.5MiB"), 1024 * 1024 * 1.5)
        self.assertEqual(_parse_size("1.75GiB"), 1024 * 1024 * 1024 * 1.75)


class TestCreateImage(unittest.TestCase):
    def test_create_image(self):
        try_create_image(
            "../example01", "../temp/example01.img", overwrite=True, use_partfs=True
        )

    def test_create_image2(self):
        try_create_image(
            "../example02", "../temp/example02.img", overwrite=True, use_partfs=True
        )

    def test_create_image3(self):
        try_create_image(
            "../example03", "../temp/example03.img", overwrite=True, use_partfs=True
        )

    def test_mount_image1(self):
        with try_mount_image(
            "../temp/example03.img", partitions=[1, 2], use_partfs=True
        ):
            print("Do with the mounts!")


if __name__ == "__main__":
    # Change working directory to the tests.py path
    abspath = os.path.abspath(__file__)
    dname = os.path.dirname(abspath)
    os.chdir(dname)

    unittest.main()
