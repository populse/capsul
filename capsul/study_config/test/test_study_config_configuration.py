#!/usr/bin/env python

import unittest
import sys
import os
import json
import soma.config
from tempfile import mkdtemp
from shutil import rmtree
from capsul.study_config.study_config import StudyConfig
try:
    from brainvisa_share import config as bv_share_config
except ImportError:
    bv_share_config = None

# The following variables contains a series of (p,v) where p contains
# parameters to pass to StudyConfig constructor (*args and **kwargs) and v
# contains some expected values on the StudyConfig object. Each series
# of test is executed with a different context (i.e. configuration files and
# CAPSUL_CONFIG environment variable).


if bv_share_config is not None:
    # take 2 fist digits in version
    bv_share_version = '.'.join(bv_share_config.version.split('.')[:2])
else:
    # brainvisa_share.config cannot be imported: sounds bad, but
    # fallback to soma.config version (which may be different)
    bv_share_version = soma.config.short_version

# StudyConfig instanciation tests and expected results when no configuration
# file exist.
tests_no_files = [

    # Test StudyConfig()
    [[(),{}],[
        {
            "somaworkflow_computing_resources_config": {},
            "generate_logging": False,
            "use_scheduler": False,
            "use_debug": False,
            "number_of_cpus": 1,
            "use_fsl": False,
            'use_matlab': False,
            'use_spm': False,
            'automatic_configuration': False,
            'spm_standalone': False,
            'use_smart_caching': False,
            'use_soma_workflow': False,
        },
        ['FSLConfig', 'MatlabConfig', 'SPMConfig', 'SmartCachingConfig',
            'SomaWorkflowConfig'],
        None,
        None]],
     
    # Test StudyConfig('my_study')
    [[('my_study',), {}],[
        {
            "somaworkflow_computing_resources_config": {},
            "generate_logging": False,
            "use_fsl": False,
            'use_matlab': False,
            'use_spm': False,
            'automatic_configuration': False,
            "use_scheduler": False,
            "use_debug": False,
            "number_of_cpus": 1,
            'spm_standalone': False,
            'use_smart_caching': False,
            'use_soma_workflow': False,
        },
        ['FSLConfig', 'MatlabConfig', 'SPMConfig', 'SmartCachingConfig',
            'SomaWorkflowConfig'],
        None,
        None]],
            
    # Test StudyConfig('other_study')
    [[('other_study',), {}],[
        {
            "somaworkflow_computing_resources_config": {},
            "generate_logging": False,
            "use_fsl": False,
            'use_matlab': False,
            "use_scheduler": False,
            "use_debug": False,
            "number_of_cpus": 1,
            'use_spm': False,
            'automatic_configuration': False,
            'spm_standalone': False,
            'use_smart_caching': False,
            'use_soma_workflow': False,
        },
        ['FSLConfig', 'MatlabConfig', 'SPMConfig', 'SmartCachingConfig',
            'SomaWorkflowConfig'],
        None,
        None]],

    # Test StudyConfig(init_config={'config_modules':[]})
    #[[(),dict(init_config={'config_modules':[]})], [
    #    {
    #        "generate_logging": False,
    #        'automatic_configuration': False,
    #    },
    #    [], None, None]],
        
    # Test StudyConfig(modules=['SomaWorkflowConfig'])
    [[(),dict(modules=['SomaWorkflowConfig'])], [
        {
            "use_scheduler": False,
            "use_debug": False,
            "number_of_cpus": 1,
            "somaworkflow_computing_resources_config": {},
            "generate_logging": False,
            'automatic_configuration': False,
            'use_soma_workflow': False,
        },
        ['SomaWorkflowConfig'], None, None]],

        
    [[(),dict(init_config={}, modules=StudyConfig.default_modules + ['FSLConfig',
                                      'FreeSurferConfig', 'BrainVISAConfig'])],[
        {
            "use_scheduler": False,
            "use_debug": False,
            "number_of_cpus": 1,
            "somaworkflow_computing_resources_config": {},
            "generate_logging": False,
            "use_fsl": False,
            'use_matlab': False,
            'use_spm': False,
            "use_freesurfer": False,
            "shared_directory": os.path.join(soma.config.BRAINVISA_SHARE, 
                                             'brainvisa-share-%s' % \
                                             bv_share_version),
            'automatic_configuration': False,
            'spm_standalone': False,
            'use_smart_caching': False,
            'use_soma_workflow': False,
        },
        ['BrainVISAConfig', 'FSLConfig', 'FreeSurferConfig', 'MatlabConfig', 
         'SPMConfig', 'SmartCachingConfig', 'SomaWorkflowConfig'],
        None,
        None]],

]


# StudyConfig instanciation tests and expected results using configuration 
# files in user directory (a temporary directory is used instead of the user
# directory for this test).
tests_standard_files = [

    # Test StudyConfig()
    [[(),{}],[
        {
            "somaworkflow_computing_resources_config": {},
            "generate_logging": False,
            "use_scheduler": False,
            "use_debug": False,
            "number_of_cpus": 1,
            "use_fsl": False,
            'use_matlab': False,
            'use_spm': False,
            'automatic_configuration': False,
            'spm_standalone': False,
            'use_smart_caching': False,
            'use_soma_workflow': False,
        },
        ['FSLConfig', 'MatlabConfig', 'SPMConfig', 'SmartCachingConfig',
            'SomaWorkflowConfig'],
        'config.json',
         None]],
     
    # Test StudyConfig('my_study')
    [[('my_study',), {}],[
        {   'use_fom': True, 
            'shared_fom': "",
            'input_fom': "",
            'somaworkflow_computing_resources_config': {},
            'generate_logging': False,
            "use_scheduler": False,
            "use_debug": False,
            "number_of_cpus": 1,
            "shared_directory": os.path.join(soma.config.BRAINVISA_SHARE, 
                                             'brainvisa-share-%s' % \
                                             bv_share_version),
            'output_fom': "",
            'automatic_configuration': False,
            'use_matlab': False,
            'use_spm': False,
            'spm_standalone': False,
            'use_soma_workflow': False,
        },
        ['BrainVISAConfig', 'FomConfig', 'MatlabConfig', 'SPMConfig', 'SomaWorkflowConfig'],
        'config.json',
        os.path.join('my_study', 'config.json')]],

    # Test StudyConfig('other_study')
    [[('other_study',), {}],[
        {
            "somaworkflow_computing_resources_config": {},
            "generate_logging": False,
            'use_fsl': False,
            'use_matlab': False,
            'use_spm': False,
            "use_scheduler": False,
            "use_debug": False,
            "number_of_cpus": 1,
            'automatic_configuration': False,
            'spm_standalone': False,
            'use_smart_caching': False,
            'use_soma_workflow': False,
        },
        ['FSLConfig', 'MatlabConfig', 'SPMConfig', 'SmartCachingConfig',
            'SomaWorkflowConfig'],
        'config.json',
        None]],

    # Test StudyConfig(init_config={'config_modules':[]})
    [[(),dict(init_config={'config_modules':[]})], [
        {
            "generate_logging": False,
            'automatic_configuration': False,
            "use_scheduler": False,
            "use_debug": False,
            "number_of_cpus": 1,
        },
        [],
        None,
        None]],
        
    # Test StudyConfig(modules=['SomaWorkflowConfig'])
    [[(),dict(modules=['SomaWorkflowConfig'])], [
        {
            "somaworkflow_computing_resources_config": {},
            "generate_logging": False,
            'automatic_configuration': False,
            'use_soma_workflow': False,
            "use_scheduler": False,
            "use_debug": False,
            "number_of_cpus": 1,
        },
        ['SomaWorkflowConfig'],
        'config.json',
        None]],
]

# StudyConfig instanciation tests and expected results using configuration 
# files defined in CAPSUL_CONFIG.
tests_custom_files = [

    # Test StudyConfig()
    [[(),{}],[
        {
            "use_scheduler": False,
            "use_debug": False,
            "number_of_cpus": 1,
            "somaworkflow_computing_resources_config": {},
            "generate_logging": False,
            'use_fsl': False,
            'use_matlab': False,
            'use_spm': False,
            'automatic_configuration': False,
            'spm_standalone': False,
            'use_smart_caching': False,
            'use_soma_workflow': False,
        },
        ['FSLConfig', 'MatlabConfig', 'SPMConfig', 'SmartCachingConfig', 'SomaWorkflowConfig'],
        os.path.join('somewhere', 'config.json'),
         None]],
     
    # Test StudyConfig('my_study')
    [[('my_study',), {}],[
        {   
            "use_scheduler": False,
            "use_debug": False,
            "number_of_cpus": 1,
            'use_fom': True, 
            'shared_fom': "",
            'input_fom': "",
            'somaworkflow_computing_resources_config': {},
            'generate_logging': False,
            "shared_directory": os.path.join(soma.config.BRAINVISA_SHARE, 
                                             'brainvisa-share-%s' % \
                                             bv_share_version),
            'output_fom': "",
            'automatic_configuration': False,
            'use_matlab': False,
            'use_spm': False,
            'spm_standalone': False,
            'use_soma_workflow': False,
        },
        ['BrainVISAConfig', 'FomConfig', 'MatlabConfig', 'SPMConfig', 'SomaWorkflowConfig'],
        os.path.join('somewhere', 'config.json'),
        os.path.join('my_study', 'config.json')]],

    # Test StudyConfig('other_study')
    [[('other_study',), {}],[
        {
            "use_scheduler": False,
            "use_debug": False,
            "number_of_cpus": 1,
            "somaworkflow_computing_resources_config": {},
            "generate_logging": False,
            'use_fsl': False,
            'use_matlab': False,
            'use_spm': False,
            'automatic_configuration': False,
            'spm_standalone': False,
            'use_smart_caching': False,
            'use_soma_workflow': False,
        },
        ['FSLConfig', 'MatlabConfig', 'SPMConfig', 'SmartCachingConfig', 'SomaWorkflowConfig'],
        os.path.join('somewhere', 'config.json'),
        os.path.join('somewhere', 'other_study.json')]],

    # Test StudyConfig(init_config={'config_modules':[]})
    [[(),dict(init_config={'config_modules':[]})], [
        {
            "use_scheduler": False,
            "use_debug": False,
            "number_of_cpus": 1,
            "generate_logging": False,
            'automatic_configuration': False,
        },
        [],
        None,
        None]],
        
    # Test StudyConfig(modules=['SomaWorkflowConfig'])
    [[(),dict(modules=['SomaWorkflowConfig'])], [
        {
            "use_scheduler": False,
            "use_debug": False,
            "number_of_cpus": 1,
            "somaworkflow_computing_resources_config": {},
            "generate_logging": False,
            'automatic_configuration': False,
            'use_soma_workflow': False,
        },
        ['SomaWorkflowConfig'],
        os.path.join('somewhere', 'config.json'),
        None]],
]

user_config = {}

my_study_config = {
    'config_modules': ['BrainVISAConfig', 'SomaWorkflowConfig', 'FomConfig',
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
                sargs += ', '.join('%s=%s' % (repr(i),repr(j)) for i,j in kwargs.iteritems())
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

            self.assertEqual(set(config), set(expected_config))
            for name, value in expected_config.iteritems():
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
            json.dump(user_config, open(user_config_file,'w'))
            
            my_study_config_file = os.path.join(user_config_directory, 'my_study', 'config.json')
            os.mkdir(os.path.join(user_config_directory, 'my_study'))
            json.dump(my_study_config, open(my_study_config_file,'w'))

            other_config_dir = os.path.join(user_config_directory, 'somewhere')
            os.mkdir(other_config_dir)
            other_config_file = os.path.join(other_config_dir, 'config.json')
            json.dump(other_config, open(other_config_file,'w'))
            
            other_study_config_file = os.path.join(other_config_dir, 'other_study.json')
            json.dump(other_study_config, open(other_study_config_file,'w'))

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

