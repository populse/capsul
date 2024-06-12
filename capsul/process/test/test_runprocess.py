import os
import subprocess
import sys
import unittest

from soma.controller import field

from capsul.api import Process


class DummyProcess(Process):
    """Description of DummyProcess"""

    f: field(type_=float, doc="help for parameter f")

    def execute(self, context=None):
        print(f"DummyProcess exec, f={self.f}")


class TestRunProcess(unittest.TestCase):
    """Test case for CAPSUL command-line usage."""

    def test_python_m_capsul(self):
        with open(os.devnull, "wb") as f:
            ret = subprocess.call(
                [sys.executable, "-m", "capsul", "--help"], stdout=f, stderr=f
            )
        self.assertEqual(ret, 0)

    def test_run_process_help(self):
        with open(os.devnull, "wb") as f:
            ret = subprocess.call(
                [
                    sys.executable,
                    "-m",
                    "capsul",
                    "help",
                    "capsul.process.test.test_runprocess.DummyProcess",
                ],
                stdout=f,
                stderr=f,
            )
        self.assertEqual(ret, 0)

    def test_run_dummy_process(self):
        with open(os.devnull, "wb") as f:
            ret = subprocess.call(
                [
                    sys.executable,
                    "-m",
                    "capsul",
                    "run",
                    "--non-persistent",
                    "capsul.process.test.test_runprocess.DummyProcess",
                    "f=0.5",
                ],
                stdout=f,
                stderr=f,
            )
            self.assertEqual(ret, 0)
            ret = subprocess.call(
                [
                    sys.executable,
                    "-m",
                    "capsul",
                    "run",
                    "--non-persistent",
                    "capsul.process.test.test_runprocess.DummyProcess",
                    "0.5",
                ],
                stdout=f,
                stderr=f,
            )
            self.assertEqual(ret, 0)

    def test_run_dummy_process_wrong_args(self):
        with open(os.devnull, "wb") as f:
            ret = subprocess.call(
                [
                    sys.executable,
                    "-m",
                    "capsul",
                    "run",
                    "--non-persistent",
                    "capsul.process.test.test_runprocess.DummyProcess",
                    "f=toto",
                ],
                stdout=f,
                stderr=f,
            )
            self.assertNotEqual(ret, 0)
            ret = subprocess.call(
                [
                    sys.executable,
                    "-m",
                    "capsul",
                    "run",
                    "--non-persistent",
                    "capsul.process.test.test_runprocess.DummyProcess",
                ],
                stdout=f,
                stderr=f,
            )
            self.assertNotEqual(ret, 0)
            ret = subprocess.call(
                [
                    sys.executable,
                    "-m",
                    "capsul",
                    "run",
                    "--non-persistent",
                    "capsul.process.test.test_runprocess.DummyProcess",
                ],
                stdout=f,
                stderr=f,
            )
            self.assertNotEqual(ret, 0)


if __name__ == "__main__":
    unittest.main()
