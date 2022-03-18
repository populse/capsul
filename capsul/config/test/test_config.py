# -*- coding: utf-8 -*-
import unittest
from capsul.config import (ApplicationConfiguration, ConfigurationLayer,
                           EngineConfiguration)
import sys
import os
import os.path as osp
import shutil
import tempfile
import json


class TestConfiguration(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        if hasattr(self, 'tmp_dir'):
            if os.path.exists(self.tmp_dir):
                shutil.rmtree(self.tmp_dir)
            del self.tmp_dir

    def test_single_configuration(self):

        user_file = osp.join(self.tmp_dir, 'user_conf.json')
        conf_dict = {'local': {'modules': {}}}
        with open(user_file, 'w') as f:
            json.dump(conf_dict, f)
        app_config = ApplicationConfiguration('single_conf',
                                              user_file=user_file)

        self.assertEqual(
            app_config.asdict(),
            {'site': {}, 'app_name': 'single_conf', 'user': conf_dict,
             'merged_config': {}})


def test():
    """ Function to execute unitest
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestConfiguration)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    print("RETURNCODE: ", test())