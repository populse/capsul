# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import absolute_import

import gc
import unittest
import tempfile
import os
import sys
import os.path as osp
import shutil

from capsul.api import capsul_engine
from capsul.engine import activate_configuration
from capsul import engine


class TestCapsulEngine(unittest.TestCase):
    def setUp(self):
        self.sqlite_file = str(tempfile.mktemp(suffix='.sqlite'))
        self.ce = capsul_engine(self.sqlite_file)
    
    def tearDown(self):
        self.ce = None
        # garbage collect to ensure the database is closed
        # (otherwise it can cause problems on Windows when removing the
        # sqlite file)
        gc.collect()
        if os.path.exists(self.sqlite_file):
            os.remove(self.sqlite_file)


    def test_engine_settings(self):
        # In the following, we use explicit values for config_id_field
        # (which is a single string value that must be unique for each
        # config). This is not mandatory but it avoids to have randomly
        # generated values making testing results more difficult to tackle.
        self.maxDiff = 2000
        
        cif = self.ce.settings.config_id_field
        with self.ce.settings as settings:
            # Create a new section object for 'fsl' in 'global' environment
            fsl = settings.new_config('fsl', 'global', {cif:'5'})
            fsl.directory = '/there'
            
            # Create two global SPM configurations
            settings.new_config('spm', 'global', {'version': '8',
                                                  'standalone': True,
                                                  cif:'8'})
            settings.new_config('spm', 'global', {'version': '12',
                                                  'standalone': False,
                                                  cif:'12'})
            # Create one SPM configuration for 'my_machine'
            settings.new_config('spm', 'my_machine', {'version': '20',
                                                      'standalone': True,
                                                      cif:'20'})
    
        self.assertEqual(
            self.ce.settings.select_configurations('my_machine'),
            {'capsul_engine': {'uses': {'capsul.engine.module.fsl': 'ALL',
                               'capsul.engine.module.matlab': 'ALL',
                               'capsul.engine.module.spm': 'ALL'}},
             'capsul.engine.module.fsl': {'config_environment': 'global',
                                          'directory': '/there',
                                          cif: '5'},
             'capsul.engine.module.spm': {'config_environment': 'my_machine',
                                           'version': '20',
                                           'standalone': True,
                                           cif: '20'}})
        self.assertRaises(EnvironmentError,
                          lambda:
                              self.ce.settings.select_configurations('global'))
        self.assertEqual(
            self.ce.settings.select_configurations('global',
                                                   uses={'fsl': 'any'}),
            {'capsul.engine.module.fsl':
                {'config_environment': 'global', 'directory': '/there',
                 cif:'5'},
             'capsul_engine':
                {'uses': {'capsul.engine.module.fsl': 'any'}}})

        self.assertEqual(
            self.ce.settings.select_configurations('global',
                                                   uses={'spm': 'any'}),
            {'capsul.engine.module.spm':
                {'config_environment': 'global',
                 'version': '8',
                 'standalone': True,
                 cif: '8'},
             'capsul_engine':
                {'uses': {'capsul.engine.module.spm': 'any'}}})
        self.assertEqual(
            self.ce.settings.select_configurations(
                'global',  uses={'spm': 'version=="12"'}),
            {'capsul.engine.module.spm':
                {'config_environment': 'global',
                 'version': '12',
                 'standalone': False,
                 cif: '12'},
             'capsul_engine':
                {'uses':
                    {'capsul.engine.module.spm': 'version=="12"',
                     'capsul.engine.module.matlab': 'any'}}})

    def test_fsl_config(self):
        # fake the FSL "bet" command to have test working without FSL installed
        path = os.environ.get('PATH')
        tdir = tempfile.mkdtemp(prefix='capsul_fsl')

        try:
            os.mkdir(osp.join(tdir, 'bin'))
            script = osp.join(tdir, 'bin', 'fsl5.0-bet')
            with open(script, 'w') as f:
                print('''#!/usr/bin/env python

from __future__ import print_function
import sys

print(sys.argv)
''', file=f)
            os.chmod(script, 0o775)

            # change config
            os.environ['PATH'] = '%s:%s' % (path, osp.join(tdir, 'bin'))
            cif = self.ce.settings.config_id_field
            with self.ce.settings as settings:
                fsl = settings.new_config('fsl', 'global', {cif:'5'})
                fsl.directory = tdir
                fsl.prefix = 'fsl5.0-'

            conf = self.ce.settings.select_configurations('global',
                                                          uses={'fsl': 'any'})
            self.assertTrue(conf is not None)
            self.assertEqual(len(conf), 2)

            activate_configuration(conf)
            self.assertEqual(os.environ.get('FSLDIR'), tdir)
            self.assertEqual(os.environ.get('FSL_PREFIX'), 'fsl5.0-')

            if not sys.platform.startswith('win'):
                # skip this test under windows because we're using a sh script
                # shebang, and FSL doent't work there anyway

                # run it using in_context.fsl
                from capsul.in_context.fsl import fsl_check_call, \
                    fsl_check_output
                fsl_check_call(['bet', 'nothing', 'nothing_else'])
                output = fsl_check_output(['bet', 'nothing', 'nothing_else'])
                output = output.decode('utf-8').strip()
                self.assertEqual(output,
                                 "['%s', 'nothing', 'nothing_else']" % script)
        finally:
            shutil.rmtree(tdir)
            # cleanup env for later tests
            if 'FSLDIR' in os.environ:
                del os.environ['FSLDIR']


def test():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCapsulEngine)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    print("RETURNCODE: ", test())

