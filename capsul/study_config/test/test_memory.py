#! /usr/bin/env python
##########################################################################
# Capsul - Copyright (C) CEA, 2014
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import unittest
import os
import tempfile
import shutil

# Capsul import
from capsul.process import Process
from capsul.process import FileCopyProcess
from capsul.process import get_process_instance
from capsul.study_config.memory import Memory

# Trait import
from traits.api import Float, File, List, String


class DummyProcess(Process):
    """ Dummy.
    """
    f = Float(output=False, optional=False, desc="float")

    def __init__(self):
        super(DummyProcess, self).__init__()
        self.add_trait("ff", Float(output=False, optional=True, desc="float"))
        self.add_trait("res", Float(output=True, desc="float"))

    def _run_process(self):
        self.res = self.f * self.ff


class DummyCopyProcess(FileCopyProcess):
    """ Dummy file copy.
    """
    f = Float(output=False, optional=False, desc="a float")
    i = File(output=False, optional=False, desc="a file")
    l = List(File(), output=False, optional=False, desc="a list of file")
    s = String(output=True, optional=False, desc="the output file copy map")

    def _run_process(self):
        self.s = repr(self.copied_inputs)


class TestMemory(unittest.TestCase):
    """ Execute a process using smart-caching functionalities.
    """
    def __init__(self, testname, dirpath):
        """ Initilaize the TestMemory class.
        """
        # Inheritance
        super(TestMemory, self).__init__(testname)

        # Create the memory object
        self.cachedir = dirpath
        self.mem = Memory(self.cachedir)

    def test_proxy_process(self):
        """ Test the proxy process behaviours.
        """
        # Create a process instance
        process = DummyProcess()

        # Create a proxy process
        proxy_process = self.mem.cache(process, verbose=1)

        # Test the cache mechanism
        for param in [(1., 2.3), (2., 2.), (1., 2.3)]:
            proxy_process(f=param[0], ff=param[1])
            self.assertEqual(proxy_process.res, param[0] * param[1])

    def test_proxy_process_copy(self):
        """ Test memory with copy.
        """
        # Create a process instance
        process = DummyCopyProcess()

        # Create a proxy process
        proxy_process = self.mem.cache(process, verbose=1)

        # Test the cache mechanism
        proxy_process(f=2.5, i=__file__, l=[__file__])
        self.assertEqual(
            proxy_process.s,
            ("{'i': '_workspace/test_memory.py', 'l': "
             "['_workspace/test_memory.py'], 'f': 2.5}"))

if 0:
    # Configure the environment
    study_config = StudyConfig(modules=["FSLConfig"],
                               fsl_config="/etc/fsl/4.1/fsl.sh")

    # Create a process instance
    ifname = "/home/ag239446/.local/share/nsap/t1_localizer.nii.gz"
    instance = get_process_instance("nipype.interfaces.fsl.Merge")

    # Create a decorated instance
    dec_instance = mem.cache(instance)
    print dec_instance
    print dec_instance.__doc__

    # Set parameters
    dec_instance.in_files = [ifname, ifname]
    dec_instance.dimension = "t"
    dec_instance.output_type = "NIFTI_GZ"
    dec_instance.set_output_directory("/home/ag239446/tmp/")

    # Test the cache mechanism
    result = dec_instance()
    print dec_instance._merged_file
    result = dec_instance(in_files=[ifname, ifname], dimension="t")
    print dec_instance._merged_file



    # Configure the environment
    study_config = StudyConfig(modules=["MatlabConfig", "SPMConfig", "NipypeConfig",
                                        "FSLConfig", "FreeSurferConfig"],
                               matlab_exec="/neurospin/local/bin/matlab",
                               spm_directory="/i2bm/local/spm8-5236",
                               use_matlab=True,
                               use_spm=True,
                               use_nipype=True)

    # Create a process instance
    ifname = "/home/ag239446/.local/share/nsap/t1_localizer.nii"
    instance = get_process_instance("nipype.interfaces.spm.Smooth")

    # Create a decorated instance
    dec_instance = mem.cache(instance)
    print dec_instance
    print dec_instance.__doc__

    # Set parameters
    dec_instance.in_files = [ifname]
    dec_instance.fwhm = [4, 4, 4]
    dec_instance.set_output_directory("/home/ag239446/tmp/")
    dec_instance._nipype_interface.mlab.inputs.prescript = [
        "ver,", "try,", "addpath('{0}');".format("/i2bm/local/spm8-5236"),
        "cd('{0}');".format("/home/ag239446/tmp/")
    ]

    # Test the cache mechanism
    result = dec_instance()
    print dec_instance._smoothed_files


def test():
    """ Function to execute unitest.
    """
    dirpath = tempfile.mkdtemp()
    suite = unittest.TestSuite()
    suite.addTest(TestMemory("test_proxy_process", dirpath))
    suite.addTest(TestMemory("test_proxy_process", None))
    suite.addTest(TestMemory("test_proxy_process_copy", None))
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    shutil.rmtree(dirpath)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    print("RETURNCODE: ", test())
