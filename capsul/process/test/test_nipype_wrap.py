# -*- coding: utf-8 -*-
# System import
from __future__ import absolute_import

import os
import os.path as osp
import unittest
import glob
import shutil
import tempfile

# Capsul import
from capsul.api import executable
from capsul.api import NipypeProcess
from capsul.api import Capsul
from capsul.config.configuration import ApplicationConfiguration

try:
    import nipype
except ImportError:
    # if nipype is not installed, skip this test (without failure)
    nipype = None


def init_spm_config():
    if nipype is None:
        return False

    spm_search_dirs = ['/host/usr/local/spm12-standalone',
                        '/usr/local/spm12-standalone',
                        '/i2bm/local/spm12-standalone']
    mcr_search_dirs = ['/host/usr/local/Matlab/mcr/v97',
                        '/usr/local/Matlab/mcr/v97',
                        '/i2bm/local/Matlab/mcr/v97']

    spm_dir = None
    for spm_dir in spm_search_dirs:
        if osp.isdir(spm_dir):
            break
    if not osp.isdir(spm_dir):
        return False

    mcr_dir = None
    mcr_dirs = glob.glob(osp.join(spm_dir, 'mcr', 'v*'))
    if len(mcr_dirs) == 1:
        mcr_dir = mcr_dirs[0]
    else:
        for mcr_dir in mcr_search_dirs:
            if osp.isdir(mcr_dir):
                break
    if not osp.isdir(mcr_dir):
        return False

    Capsul.delete_singleton()
    c = Capsul()

    config = ApplicationConfiguration('capsul_test_nipype_spm')
    user_conf_dict = {
        'builtin': {
            'spm': {
                'spm12_standalone': {
                    'directory': spm_dir,
                    'standalone': True,
                    'version': '12'},
                },
            'nipype': {
                'nipype': {},
            },
            'matlab': {
                'matlab_mcr': {
                    'mcr_directory': mcr_dir,
                },
            },
        }
    }
    config.user = user_conf_dict
    config.merge_configs()

    c.config = config.merged_config
    # print('local config:', c.config.asdict())

    return True


class TestNipypeWrap(unittest.TestCase):
    """ Class to test the nipype interfaces wrapping.
    """

    def setUp(self):
        # output format and extensions depends on FSL config variables
        # so may change if FSL has been setup.
        fsl_output_format = os.environ.get('FSLOUTPUTTYPE', '')
        if fsl_output_format == 'NIFTI_GZ':
            self.output_extension = '.nii.gz'
        else:
            # default is nifti
            self.output_extension = '.nii'

    @unittest.skipIf(nipype is None, 'nipype is not installed')
    def test_nipype_automatic_wrap(self):
        """ Method to test if the automatic nipype interfaces wrap work
        properly.
        """
        from nipype.interfaces.fsl import BET
        nipype_process = executable("nipype.interfaces.fsl.BET")
        self.assertTrue(isinstance(nipype_process, NipypeProcess))
        self.assertTrue(isinstance(nipype_process._nipype_interface, BET))

    @unittest.skipIf(nipype is None, 'nipype is not installed')
    def test_nipype_monkey_patching(self):
        """ Method to test the monkey patching used to work in user
        specified directories.
        """
        nipype_process = executable("nipype.interfaces.fsl.BET")
        nipype_process.in_file = os.path.abspath(__file__)
        self.assertEqual(
            nipype_process._nipype_interface._list_outputs()["out_file"],
            os.path.join(os.getcwd(),
                         "test_nipype_wrap_brain%s" % self.output_extension))

    @unittest.skipIf(not init_spm_config(),
                     'SPM is not configured to run this test')
    def test_nipype_spm_exec(self):
        # we must do this again because when multiple tests are run, the init
        # function may be called at the wrong time (too early, at import), then
        # other tests will run and define a different Capsul object
        init_spm_config()

        c = Capsul()

        template_dirs = ['spm12_mcr/spm12/spm12',
                         'spm12_mcr/spm12',
                         'spm12']
        for template_dir_s in template_dirs:
            template_dir = osp.join(
                c.config.builtin.spm.spm12_standalone.directory, template_dir_s)
            if osp.isdir(template_dir):
                break
        self.assertTrue(
            osp.isdir(template_dir),
            'SPM template dir is not found. Please check SPM installation')

        t1_template = osp.join(template_dir, 'toolbox/OldNorm/T1.nii')

        tmp_dir = tempfile.mkdtemp(prefix='capsul_nipype_wrap_test')

        try:

            p = c.executable('nipype.interfaces.spm.preprocess.Smooth')

            p.in_files = [t1_template]
            p.fwhm = 10.
            p.output_directory = tmp_dir

            with c.engine() as e:
                e.run(p)

            print('output values:')
            print(p.asdict())

            smoothed = p.smoothed_files
            self.assertEqual(len(smoothed), 1)
            smoothed = smoothed[0]
            self.assertEqual(osp.dirname(smoothed), tmp_dir)
            self.assertEqual(osp.basename(smoothed),
                             f's{osp.basename(t1_template)}')
            self.assertTrue(osp.exists(smoothed))

        finally:
            shutil.rmtree(tmp_dir)


def tearDownModule():
    Capsul.delete_singleton()
