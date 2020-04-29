# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import absolute_import

import gc
import unittest
import tempfile
import os
import sys


from capsul.api import capsul_engine

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


    def test_engine(self):
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
        self.assertRaises(EnvironmentError, lambda: self.ce.settings.select_configurations('global'))
        self.assertEqual(
            self.ce.settings.select_configurations('global', uses={'fsl': 'any'}),
            {'capsul.engine.module.fsl': {'config_environment': 'global', 'directory': '/there', cif:'5'},
             'capsul_engine': {'uses': {'capsul.engine.module.fsl': 'any'}}})
            
        self.assertEqual(
            self.ce.settings.select_configurations('global', uses={'spm': 'any'}),
            {'capsul.engine.module.spm': {'config_environment': 'global', 
                                          'version': '8',
                                          'standalone': True,
                                          cif: '8'},
             'capsul_engine': {'uses': {'capsul.engine.module.spm': 'any'}}})
        self.assertEqual(
            self.ce.settings.select_configurations('global', uses={'spm': 'version=="12"'}),
            {'capsul.engine.module.spm': {'config_environment': 'global',
                                          'version': '12',
                                          'standalone': False,
                                          cif: '12'},
             'capsul_engine': {'uses': {'capsul.engine.module.spm': 'version=="12"',
                                        'capsul.engine.module.matlab': 'any'}}})

def test():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCapsulEngine)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    print("RETURNCODE: ", test())

