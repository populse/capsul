# -*- coding: utf-8 -*-

from __future__ import print_function

from __future__ import absolute_import
import unittest
import sys
import os
import json
import six
import soma.config
from tempfile import mkdtemp
from shutil import rmtree
from capsul.study_config.study_config import StudyConfig
from traits.api import Undefined

# The following variables contains a series of (p,v) where p contains
# parameters to pass to StudyConfig constructor (*args and **kwargs) and v
# contains some expected values on the StudyConfig object. Each series
# of test is executed with a different context (i.e. configuration files and
# CAPSUL_CONFIG environment variable).

# StudyConfig instantiation tests and expected results when no configuration
# file exist.
tests_no_files = [

# Test StudyConfig()
[[(),{}],[
    {
        "somaworkflow_computing_resources_config": {},
        "somaworkflow_keep_succeeded_workflows": False,
        "somaworkflow_keep_failed_workflows": True,
        "generate_logging": False,
        'use_matlab': False,
        'use_smart_caching': False,
        'use_soma_workflow': False,
        'create_output_directories': True,
        'process_output_directory': False,
        'user_level': 0,
    },
    ['AFNIConfig', 'ANTSConfig', 'FSLConfig', 'MatlabConfig', 'SPMConfig', 'SmartCachingConfig',
        'SomaWorkflowConfig'],
    None,
    None]],
 
# Test StudyConfig('my_study')
[[('my_study',), {}],[
    {
        "somaworkflow_computing_resources_config": {},
        "somaworkflow_keep_succeeded_workflows": False,
        "somaworkflow_keep_failed_workflows": True,
        "generate_logging": False,
        'use_matlab': False,
        'use_smart_caching': False,
        'use_soma_workflow': False,
        'create_output_directories': True,
        'process_output_directory': False,
        'user_level': 0,
    },
    ['AFNIConfig', 'ANTSConfig', 'FSLConfig', 'MatlabConfig', 'SPMConfig', 'SmartCachingConfig',
        'SomaWorkflowConfig'],
    None,
    None]],
        
# Test StudyConfig('other_study')
[[('other_study',), {}],[
    {
        "somaworkflow_computing_resources_config": {},
        "somaworkflow_keep_succeeded_workflows": False,
        "somaworkflow_keep_failed_workflows": True,
        "generate_logging": False,
        'use_matlab': False,
        'use_smart_caching': False,
        'use_soma_workflow': False,
        'create_output_directories': True,
        'process_output_directory': False,
        'user_level': 0,
    },
    ['AFNIConfig', 'ANTSConfig', 'FSLConfig', 'MatlabConfig', 'SPMConfig', 'SmartCachingConfig',
        'SomaWorkflowConfig'],
    None,
    None]],

# Test StudyConfig(init_config={'config_modules':[]})
#[[(),dict(init_config={'config_modules':[]})], [
#    {
#        "generate_logging": False,
#    },
#    [], None, None]],
    
# Test StudyConfig(modules=['SomaWorkflowConfig'])
[[(),dict(modules=['SomaWorkflowConfig'])], [
    {
        "somaworkflow_computing_resources_config": {},
        "somaworkflow_keep_succeeded_workflows": False,
        "somaworkflow_keep_failed_workflows": True,
        "generate_logging": False,
        'use_soma_workflow': False,
        'create_output_directories': True,
        'process_output_directory': False,
        'user_level': 0,
    },
    ['SomaWorkflowConfig'], None, None]],

    
[[(),dict(init_config={}, modules=StudyConfig.default_modules + ['FSLConfig',
                                  'FreeSurferConfig', 'BrainVISAConfig'])],[
    {
        "somaworkflow_computing_resources_config": {},
        "somaworkflow_keep_succeeded_workflows": False,
        "somaworkflow_keep_failed_workflows": True,
        "generate_logging": False,
        'use_matlab': False,
        "use_freesurfer": False,
        "shared_directory": soma.config.BRAINVISA_SHARE,
        'use_smart_caching': False,
        'use_soma_workflow': False,
        'create_output_directories': True,
        'process_output_directory': False,
        'user_level': 0,
    },
    ['AFNIConfig', 'ANTSConfig', 'BrainVISAConfig', 'FSLConfig',
     'FreeSurferConfig', 'MatlabConfig', 'SPMConfig',
     'SmartCachingConfig', 'SomaWorkflowConfig'],
    None,
    None]],

]


# StudyConfig instantiation tests and expected results using configuration 
# files in user directory (a temporary directory is used instead of the user
# directory for this test).
tests_standard_files = [

# Test StudyConfig()
[[(),{}],[
    {
        "somaworkflow_computing_resources_config": {},
        "somaworkflow_keep_succeeded_workflows": False,
        "somaworkflow_keep_failed_workflows": True,
        "generate_logging": False,
        'use_matlab': False,
        'use_smart_caching': False,
        'use_soma_workflow': False,
        'create_output_directories': True,
        'process_output_directory': False,
        'user_level': 0,
    },
    ['AFNIConfig', 'ANTSConfig', 'FSLConfig', 'MatlabConfig', 'SPMConfig',
     'SmartCachingConfig', 'SomaWorkflowConfig'],
    'config.json',
     None]],
 
# Test StudyConfig('my_study')
[[('my_study',), {}],[
    {   'use_fom': True, 
        'auto_fom': True,
        'shared_fom': "",
        'input_fom': "",
        'fom_path': [],
        'somaworkflow_computing_resources_config': {},
        "somaworkflow_keep_succeeded_workflows": False,
        "somaworkflow_keep_failed_workflows": True,
        'generate_logging': False,
        "shared_directory": soma.config.BRAINVISA_SHARE,
        'output_fom': "",
        'use_matlab': False,
        'use_soma_workflow': False,
        'create_output_directories': True,
        'attributes_schema_paths': [
            'capsul.attributes.completion_engine_factory'],
        'attributes_schemas': {},
        'process_completion': 'builtin',
        'process_output_directory': False,
        'user_level': 0,
    },
    ['AttributesConfig', 'BrainVISAConfig', 'FomConfig', 'MatlabConfig', 'SPMConfig', 'SomaWorkflowConfig'],
    'config.json',
    os.path.join('my_study', 'config.json')]],

# Test StudyConfig('other_study')
[[('other_study',), {}],[
    {
        "somaworkflow_computing_resources_config": {},
        "somaworkflow_keep_succeeded_workflows": False,
        "somaworkflow_keep_failed_workflows": True,
        "generate_logging": False,
        'use_matlab': False,
        'use_smart_caching': False,
        'use_soma_workflow': False,
        'create_output_directories': True,
        'process_output_directory': False,
        'user_level': 0,
    },
    ['AFNIConfig', 'ANTSConfig', 'FSLConfig', 'MatlabConfig', 'SPMConfig',
     'SmartCachingConfig', 'SomaWorkflowConfig'],
    'config.json',
    None]],

# Test StudyConfig(init_config={'config_modules':[]})
[[(),dict(init_config={'config_modules':[]})], [
    {
        "generate_logging": False,
        'create_output_directories': True,
        'process_output_directory': False,
        'user_level': 0,
    },
    [],
    None,
    None]],
    
# Test StudyConfig(modules=['SomaWorkflowConfig'])
[[(),dict(modules=['SomaWorkflowConfig'])], [
    {
        "somaworkflow_computing_resources_config": {},
        "somaworkflow_keep_succeeded_workflows": False,
        "somaworkflow_keep_failed_workflows": True,
        "generate_logging": False,
        'use_soma_workflow': False,
        'create_output_directories': True,
        'process_output_directory': False,
        'user_level': 0,
    },
    ['SomaWorkflowConfig'],
    'config.json',
    None]],
]

# StudyConfig instantiation tests and expected results using configuration 
# files defined in CAPSUL_CONFIG.
tests_custom_files = [

# Test StudyConfig()
[[(),{}],[
    {
        "somaworkflow_computing_resources_config": {},
        "somaworkflow_keep_succeeded_workflows": False,
        "somaworkflow_keep_failed_workflows": True,
        "generate_logging": False,
        'use_matlab': False,
        'use_smart_caching': False,
        'use_soma_workflow': False,
        'create_output_directories': True,
        'process_output_directory': False,
        'user_level': 0,
    },
    ['AFNIConfig', 'ANTSConfig', 'FSLConfig', 'MatlabConfig', 'SPMConfig',
     'SmartCachingConfig', 'SomaWorkflowConfig'],
    os.path.join('somewhere', 'config.json'),
     None]],
 
# Test StudyConfig('my_study')
[[('my_study',), {}],[
    {   'use_fom': True, 
        'auto_fom': True,
        'shared_fom': "",
        'input_fom': "",
        'fom_path': [],
        'somaworkflow_computing_resources_config': {},
        "somaworkflow_keep_succeeded_workflows": False,
        "somaworkflow_keep_failed_workflows": True,
        'generate_logging': False,
        "shared_directory": soma.config.BRAINVISA_SHARE,
        'output_fom': "",
        'use_matlab': False,
        'use_soma_workflow': False,
        'create_output_directories': True,
        'attributes_schema_paths': [
            'capsul.attributes.completion_engine_factory'],
        'attributes_schemas': {},
        'process_completion': 'builtin',
        'process_output_directory': False,
        'user_level': 0,
    },
    ['AttributesConfig', 'BrainVISAConfig', 'FomConfig', 'MatlabConfig', 'SPMConfig', 'SomaWorkflowConfig'],
    os.path.join('somewhere', 'config.json'),
    os.path.join('my_study', 'config.json')]],

# Test StudyConfig('other_study')
[[('other_study',), {}],[
    {
        "somaworkflow_computing_resources_config": {},
        "somaworkflow_keep_succeeded_workflows": False,
        "somaworkflow_keep_failed_workflows": True,
        "generate_logging": False,
        'use_matlab': False,
        'use_smart_caching': False,
        'use_soma_workflow': False,
        'create_output_directories': True,
        'process_output_directory': False,
        'user_level': 0,
    },
    ['AFNIConfig', 'ANTSConfig', 'FSLConfig', 'MatlabConfig', 'SPMConfig',
     'SmartCachingConfig', 'SomaWorkflowConfig'],
    os.path.join('somewhere', 'config.json'),
    os.path.join('somewhere', 'other_study.json')]],

# Test StudyConfig(init_config={'config_modules':[]})
[[(),dict(init_config={'config_modules':[]})], [
    {
        "generate_logging": False,
        'create_output_directories': True,
        'process_output_directory': False,
        'user_level': 0,
    },
    [],
    None,
    None]],
    
# Test StudyConfig(modules=['SomaWorkflowConfig'])
[[(),dict(modules=['SomaWorkflowConfig'])], [
    {
        "somaworkflow_computing_resources_config": {},
        "somaworkflow_keep_succeeded_workflows": False,
        "somaworkflow_keep_failed_workflows": True,
        "generate_logging": False,
        'use_soma_workflow': False,
        'create_output_directories': True,
        'process_output_directory': False,
        'user_level': 0,
    },
    ['SomaWorkflowConfig'],
    os.path.join('somewhere', 'config.json'),
    None]],
]

user_config = {}

my_study_config = {
    'config_modules': ['AttributesConfig', 'BrainVISAConfig',
                       'SomaWorkflowConfig', 'FomConfig',
                       'MatlabConfig', 'SPMConfig']
}

other_config = {
    'studies_config': {
        'other_study': 'other_study.json'
    }
}
other_study_config = {}



class TestStudyConfigConfiguration(unittest.TestCase):

    def setUp(self):
        pass

    def run_study_config_instanciation(self, tests, test_description,
                                       user_config_directory):
        for arguments, results in tests:
            args, kwargs = arguments
            sargs = ', '.join(repr(i) for i in args)
            if kwargs:
                sargs += ', '.join('%s=%s' % (repr(i),repr(j)) for i,j
                                   in six.iteritems(kwargs))
            sc = StudyConfig(*args, **kwargs)
            (expected_config, expected_modules, global_config_file, 
            study_config_file) = results
            if global_config_file:
                global_config_file = os.path.join(user_config_directory, 
                                                global_config_file)
            if study_config_file:
                study_config_file = os.path.join(user_config_directory, 
                                                study_config_file)
            config = sc.get_configuration_dict()
            modules = sorted(sc.modules.keys())
            try:
                self.assertEqual(set(config), set(expected_config))
                for name, value in six.iteritems(expected_config):
                    self.assertEqual(config[name], value,
                        'StudyConfig(%s) %s attribute %s should be %s but is '
                        '%s' % (sargs, test_description, name, repr(value),
                                repr(getattr(sc, name))))
                self.assertEqual(modules, expected_modules,
                    'StudyConfig(%s) %s modules are %s but expected value is '
                    '%s' % (sargs, test_description, repr(modules), 
                            repr(expected_modules)))
                self.assertEqual(sc.global_config_file, global_config_file,
                    'StudyConfig(%s) %s global_config_file should be %s but '
                    'is %s' % (sargs,test_description, 
                                repr(global_config_file), 
                                repr(sc.global_config_file)))
                self.assertEqual(sc.study_config_file, study_config_file,
                    'StudyConfig(%s) %s study_config_file should be %s but is '
                    '%s' % (sargs, test_description, repr(study_config_file), 
                            repr(sc.study_config_file)))
            except Exception as e:
                raise EnvironmentError('When testing StudyConfig(*{0}, **{1}), got the following error: {2}'.format(args, kwargs, e))
    
    def test_study_config_configuration(self):
        user_config_directory = mkdtemp()
        try:
            # Run tests without any configuration file
            StudyConfig._user_config_directory = user_config_directory
            self.run_study_config_instanciation(tests_no_files, 
                'without configuration files', user_config_directory)
                
            # Check wrong value in CAPSUL_CONFIG environment variable
            os.environ['CAPSUL_CONFIG'] = \
                os.path.join(user_config_directory,'i_do_not_exists.json')
            #try:
            self.run_study_config_instanciation(tests_no_files, 
                'with wrong CAPSUL_CONFIG environment variable',
                user_config_directory)
            #except IOError, e:
            #    print e
            #    if e.errno != 2:
            #        raise
            #else:
            #    self.fail('Wrong value in CAPSUL_CONFIG is supposed to '
            #              'raise an IOError with errno==2')
            del os.environ['CAPSUL_CONFIG']
            
            # Check configuration files usage
            user_config_file = os.path.join(user_config_directory, 'config.json')
            with open(user_config_file,'w') as f:
                json.dump(user_config, f)
            
            my_study_config_file = os.path.join(user_config_directory, 'my_study', 'config.json')
            os.mkdir(os.path.join(user_config_directory, 'my_study'))
            with open(my_study_config_file,'w') as f:
                json.dump(my_study_config, f)

            other_config_dir = os.path.join(user_config_directory, 'somewhere')
            os.mkdir(other_config_dir)
            other_config_file = os.path.join(other_config_dir, 'config.json')
            with open(other_config_file,'w') as f:
                json.dump(other_config, f)
            
            other_study_config_file = os.path.join(other_config_dir, 'other_study.json')
            with open(other_study_config_file,'w') as f:
                json.dump(other_study_config, f)

            self.run_study_config_instanciation(tests_standard_files, 
                'with standard configuration files',
                user_config_directory)
                
            os.environ['CAPSUL_CONFIG'] = other_config_file
            self.run_study_config_instanciation(tests_custom_files, 
                'with CAPSUL_CONFIG configuration files',
                user_config_directory)
        finally:
            rmtree(user_config_directory)


def test():
    """ Function to execute unitest
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestStudyConfigConfiguration)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    print("RETURNCODE: ", test())
