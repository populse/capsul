from __future__ import print_function

import gc
import unittest
import tempfile
import os
import sys


from capsul.api import capsul_engine

class TestCapsulEngine(unittest.TestCase):        
    def setUp(self):
        self.sqlite_file = tempfile.mktemp(suffix='.sqlite')
        self.ce = capsul_engine(self.sqlite_file)
    
    def tearDown(self):
        del self.ce
        # garbage collect to ensure the database is closed
        # (otherwise it can cause problems on Windows when removing the
        # sqlite file)
        gc.collect()
        if os.path.exists(self.sqlite_file):
            os.remove(self.sqlite_file)


    def test_engine(self):
        with self.ce.settings as settings:
            # Create a new section object for 'fsl' in 'global' environment
            fsl = settings.new_section('global', 'fsl')
            fsl.version = 5 # Set global FSL version
            
            # Create two global SPM configurations
            settings.new_section('global', 'spm', version=8)
            settings.new_section('global', 'spm', version=12)
            # Create one SPM configuration for 'my_machine'
            settings.new_section('my_machine', 'spm', version=20)
    
        self.assertEqual(
            self.ce.settings.config('my_machine'),
            {u'capsul.engine.module.fsl': {u'config_environment': u'global',
                                        u'version': 5},
            u'capsul.engine.module.spm': {u'config_environment': u'my_machine',
                                        u'version': 20}})
        self.assertRaises(EnvironmentError, lambda: self.ce.settings.config('global'))
        self.assertEqual(
            self.ce.settings.config('global', uses={'fsl': 'any'}),
            {'capsul.engine.module.fsl': {u'config_environment': u'global', u'version': 5},
             'capsul_engine': {'uses': {'capsul.engine.module.fsl': 'any'}}})
            
        self.assertEqual(
            self.ce.settings.config('global', uses={'spm': 'any'}),
            {'capsul.engine.module.spm': {u'config_environment': u'global', u'version': 8},
             'capsul_engine': {'uses': {'capsul.engine.module.spm': 'any'}}})
        self.assertEqual(
            self.ce.settings.config('global', uses={'spm': 'version==12'}),
            {'capsul.engine.module.spm': {u'config_environment': u'global',
                                          u'version': 12},
             'capsul_engine': {'uses': {'capsul.engine.module.spm': 'version==12'}}})
