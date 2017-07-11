##########################################################################
# Capsul - Copyright (C) CEA, 2014
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from __future__ import print_function

# System import
import unittest
import os
import tempfile
import shutil

# Capsul import
from capsul.api import Process
from capsul.api import FileCopyProcess
from capsul.api import get_process_instance
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
    def setUp(self):
        self.workspace_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.workspace_dir)
        if hasattr(self, 'cachedir'):
            try:
                shutil.rmtree(self.cachedir)
            except:
                pass

    def test_proxy_process_with_cache(self):
        """ Test the proxy process behaviours with cache.
        """
        # Create the memory object
        self.cachedir = tempfile.mkdtemp()
        self.mem = Memory(self.cachedir)
    
        # Call the test
        self.proxy_process()

        # Rm temporary folder
        shutil.rmtree(self.cachedir)

    def test_proxy_process_without_cache(self):
        """ Test the proxy process behaviours without cache.
        """
        # Create the memory object
        self.cachedir = None
        self.mem = Memory(self.cachedir)
    
        # Call the test
        self.proxy_process()

    def test_proxy_process_copy(self):
        """ Test memory with copy.
        """
        # Create the memory object
        self.cachedir = None
        self.mem = Memory(self.cachedir)
    
        # Call the test
        self.proxy_process_copy()

    def proxy_process(self):
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

    def proxy_process_copy(self):
        """ Test memory with copy.
        """
        # Create a process instance
        process = DummyCopyProcess()
        process.destination = self.workspace_dir

        # Create a proxy process
        proxy_process = self.mem.cache(process, verbose=1)

        # Test the cache mechanism
        proxy_process(f=2.5, i=__file__, l=[__file__])
        copied_file = os.path.join(self.workspace_dir,
                                   os.path.basename(__file__))
        print('proxy_process:', type(proxy_process))
        print('machin:', "{{'i': {0}, 'l': [{0}], 'f': 2.5}}".format(repr(copied_file)))
        self.assertEqual(
            eval(proxy_process.s),
            {'i': copied_file, 'l': [copied_file], 'f': 2.5})

if 0:
    # Configure the environment
    study_config = StudyConfig(modules=["FSLConfig"],
                               fsl_config="/etc/fsl/4.1/fsl.sh")

    # Create a process instance
    ifname = "/home/ag239446/.local/share/nsap/t1_localizer.nii.gz"
    instance = get_process_instance("nipype.interfaces.fsl.Merge")

    # Create a decorated instance
    dec_instance = mem.cache(instance)
    print(dec_instance)
    print(dec_instance.__doc__)

    # Set parameters
    dec_instance.in_files = [ifname, ifname]
    dec_instance.dimension = "t"
    dec_instance.output_type = "NIFTI_GZ"
    dec_instance.set_output_directory("/home/ag239446/tmp/")

    # Test the cache mechanism
    result = dec_instance()
    print(dec_instance._merged_file)
    result = dec_instance(in_files=[ifname, ifname], dimension="t")
    print(dec_instance._merged_file)



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
    print(dec_instance)
    print(dec_instance.__doc__)

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
    print(dec_instance._smoothed_files)


def test():
    """ Function to execute unitest.
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMemory)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    print("RETURNCODE: ", test())
