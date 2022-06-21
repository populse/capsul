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
import json
import glob

from capsul.api import capsul_engine
from capsul.api import Process, Pipeline
from capsul.engine import activate_configuration
from capsul import engine
from soma_workflow import configuration as swconfig
from traits.api import File


which = getattr(shutil, 'which', None)
if which is None:
    # python2 doesn't have shutil.which
    import distutils.spawn
    which = distutils.spawn.find_executable


def setUpModule():
    global old_home
    global temp_home_dir
    # Run tests with a temporary HOME directory so that they are isolated from
    # the user's environment
    temp_home_dir = None
    old_home = os.environ.get('HOME')
    try:
        temp_home_dir = tempfile.mkdtemp('', prefix='soma_workflow')
        os.environ['HOME'] = temp_home_dir
        swconfig.change_soma_workflow_directory(temp_home_dir)
    except BaseException:  # clean up in case of interruption
        if old_home is None:
            del os.environ['HOME']
        else:
            os.environ['HOME'] = old_home
        if temp_home_dir:
            shutil.rmtree(temp_home_dir)
        raise


class MatlabProcess(Process):
    output_config = File(output=True, desc='output file to write config',
                         allowed_extensions=['.json'])

    def requirements(self):
        return {'matlab': 'any'}

    def _run_process(self):
        import capsul.engine
        mconf = capsul.engine.configurations.get('capsul.engine.module.matlab')
        with open(self.output_config, 'w') as f:
            json.dump(mconf, f)
        if not mconf:
            raise RuntimeError('Matlab config is not present')

class PythonProcess(Process):
    output_config = File(output=True, desc='output file to write config',
                         allowed_extensions=['.json'])

    # python requirements are handled automatically
    #def requirements(self):
        #return {'python': 'any'}

    def _run_process(self):
        import capsul.engine
        import sys
        import os
        pconf = capsul.engine.configurations.get('capsul.engine.module.python')
        exe = os.environ.get('EXECUTABLE', sys.executable)
        conf = {'python_config': pconf,
                'runtime': {'executable': exe,
                            'path': sys.path}}
        with open(self.output_config, 'w') as f:
            json.dump(conf, f)
        if not pconf:
            raise RuntimeError('Python config is not present')


def tearDownModule():
    if old_home is None:
        del os.environ['HOME']
    else:
        os.environ['HOME'] = old_home
    #print('temp_home_dir:', temp_home_dir)
    shutil.rmtree(temp_home_dir)


def check_nipype_spm():
    # look for hardcoded paths, I have no other way at hand...
    spm_standalone_paths = ['/usr/local/spm12-standalone',
                            '/i2bm/local/spm12-standalone']
    spm_standalone_path = [p for p in spm_standalone_paths if os.path.isdir(p)]
    if not spm_standalone_path:
        return None
    spm_standalone_path = spm_standalone_path[0]
    mcr_path = None
    mcr = glob.glob(osp.join(spm_standalone_path, 'mcr', 'v*'))
    if not mcr or len(mcr) != 1:
        spm_exe = which('spm12')
        if spm_exe:
            # installed as in neurospin
            with open(spm_exe) as f:
                for l in f.readlines():
                    if l.startswith('MCR_HOME='):
                        mcr_path = l.split('=', 1)[1]
        if not mcr_path:
            mcr_paths = ['/usr/local/matlab/MATLAB_Runtime',
                         '/i2bm/local/matlab/MATLAB_Runtime', ]
            for p in mcr_paths:
                mcr = glob.glob(osp.join(p, 'v*'))
                if mcr and len(mcr) == 1:
                    break
    if not mcr_path:
        if not mcr or len(mcr) != 1:
            # not found or ambiguous
            return None
        mcr_path = mcr[0]
    try:
        import nipype
    except ImportError:
        return None
    return spm_standalone_path, mcr_path


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
            config = settings.config('fsl', 'global')
            if config:
                settings.remove_config('fsl', 'global',
                                        getattr(config, cif))
            fsl = settings.new_config('fsl', 'global', {cif:'5'})
            fsl.directory = '/there'

            # Create a global AFNI configuration
            config = settings.config('afni', 'global')
            if config:
                settings.remove_config('afni', 'global',
                                        getattr(config, cif))
            settings.new_config('afni', 'global', {'directory': '/there',
                                                   cif: '22'})

            # Create a global ANTS configuration
            config = settings.config('ants', 'global')
            if config:
                settings.remove_config('ants', 'global',
                                       getattr(config, cif))
            settings.new_config('ants', 'global', {'directory': '/there',
                                                   cif: '235'})

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
                                        'capsul.engine.module.spm': 'ALL',
                                        'capsul.engine.module.afni': 'ALL',
                                        'capsul.engine.module.ants': 'ALL'}},
             'capsul.engine.module.fsl': {'config_environment': 'global',
                                          'directory': '/there',
                                          cif: '5'},
             'capsul.engine.module.afni': {
                'config_environment': 'global','directory': '/there',
                cif: '22'},
             'capsul.engine.module.ants': {
                 'config_environment': 'global', 'directory': '/there',
                 cif: '235'},
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
                                                   uses={'afni': 'any'}),
            {'capsul.engine.module.afni':
                 {'config_environment': 'global', 'directory': '/there',
                  cif: '22'},
             'capsul_engine':
                 {'uses': {'capsul.engine.module.afni': 'any'}}})

        self.assertEqual(
            self.ce.settings.select_configurations('global',
                                                   uses={'ants': 'any'}),
            {'capsul.engine.module.ants':
                 {'config_environment': 'global', 'directory': '/there',
                  cif: '235'},
             'capsul_engine':
                 {'uses': {'capsul.engine.module.ants': 'any'}}})

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
            os.environ['PATH'] = os.pathsep.join((path,
                                                  osp.join(tdir, 'bin')))
            cif = self.ce.settings.config_id_field
            with self.ce.settings as settings:
                config = settings.config('fsl', 'global')
                if config:
                    settings.remove_config('fsl', 'global',
                                           getattr(config, cif))
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

    @unittest.skipIf(check_nipype_spm() is None,
                     'SPM12 standalone or nipype are not found')
    def test_nipype_spm_config(self):
        tdir = tempfile.mkdtemp(prefix='capsul_spm')
        try:
            cif = self.ce.settings.config_id_field
            spm_path, mcr_path = check_nipype_spm()
            # FIXME: do something with mcr_path
            t1_src = osp.join(spm_path,
                              'spm12_mcr/spm12/toolbox/OldNorm/T1.nii')
            if not osp.exists(t1_src):
                # spm12 has suddenly changed directories structure...
                t1_src = osp.join(
                    spm_path, 'spm12_mcr/spm12/spm12/toolbox/OldNorm/T1.nii')
            t1 = osp.join(tdir, 'T1.nii')
            shutil.copyfile(t1_src, t1)

            self.ce.load_module('nipype')

            with self.ce.settings as session:
                session.new_config('spm', 'global',
                                   {'directory': spm_path, 'standalone': True,
                                    'version': '12'})
                session.new_config('nipype', 'global', {})

            self.ce.study_config.use_soma_workflow = True
            self.ce.study_config.somaworkflow_keep_failed_workflows = True
            #self.ce.study_config.somaworkflow_keep_succeeded_workflows = True

            conf = self.ce.settings.select_configurations(
                'global', uses={'nipype': 'any', 'spm': 'any'})
            activate_configuration(conf)

            process = self.ce.get_process_instance(
                'nipype.interfaces.spm.Smooth')
            process.in_files = t1
            process.output_directory = tdir
            self.ce.study_config.run(process, configuration_dict=conf)
            self.assertTrue(osp.exists(osp.join(tdir, 'sT1.nii')))

        finally:
            #print('tdir:', tdir)
            shutil.rmtree(tdir)

    @unittest.skipIf(sys.platform.startswith('win'),
                     'Shell script needed, windows cannot execute this test.')
    def test_matlab_config(self):
        tdir = tempfile.mkdtemp(prefix='capsul_matlab')
        ce = self.ce
        try:
            matlab_exe = os.path.join(tdir, 'matlab')
            with open(matlab_exe, 'w') as f:
                f.write('#!/bin/sh\necho "$@"')
            os.chmod(matlab_exe, 0o755)

            ce.load_module('matlab')
            with ce.settings as session:
                session.new_config(
                    'matlab', 'global',
                    {'config_id': 'matlab',
                     'executable': matlab_exe})
            proc = ce.get_process_instance(
                'capsul.engine.test.test_capsul_engine.MatlabProcess')
            config_file = os.path.join(tdir, 'config.json')
            proc.output_config = config_file
            mlist = []
            req = proc.check_requirements(message_list=mlist)
            self.assertTrue(
                req is not None,
                'requirements are not met:\n%s' % '\n'.join(mlist))
            ce.check_call(proc)
            with open(config_file) as f:
                config = json.load(f)
            self.assertEqual(
                config,
                {'config_id': 'matlab', 'executable': matlab_exe,
                 'config_environment': 'global'})
        finally:
            #print('tdir:', tdir)
            shutil.rmtree(tdir)

    @unittest.skipIf(sys.platform.startswith('win'),
                     'Shell script needed, windows cannot execute this test.')
    def test_python_config(self):
        tdir = tempfile.mkdtemp(prefix='capsul_python')
        ce = self.ce
        try:
            py_exe = os.path.join(tdir, 'python')
            with open(py_exe, 'w') as f:
                f.write('#!/bin/sh\nexport EXECUTABLE="$0"\nexec python "$@"')
            os.chmod(py_exe, 0o755)

            ce.load_module('python')
            py_path = ['/tmp', '/tmp/path2']
            with ce.settings as session:
                session.new_config(
                    'python', 'global',
                    {'config_id': 'python',
                     'executable': py_exe,
                     'path': py_path})
            proc = ce.get_process_instance(
                'capsul.engine.test.test_capsul_engine.PythonProcess')
            config_file = os.path.join(tdir, 'config.json')
            proc.output_config = config_file
            mlist = []
            req = proc.check_requirements(message_list=mlist)
            self.assertTrue(
                req is not None,
                'requirements are not met:\n%s' % '\n'.join(mlist))
            ce.check_call(proc)
            with open(config_file) as f:
                config = json.load(f)
            self.assertEqual(
                config.get('python_config'), {
                    'config_id': 'python', 'executable': py_exe,
                    'path': py_path,
                    'config_environment': 'global'})
            self.assertEqual(
                config.get('runtime', {}).get('executable'), py_exe)
            paths = config.get('runtime', {}).get('path', [])
            for path in py_path:
                self.assertTrue(path in paths)
        finally:
            #print('tdir:', tdir)
            shutil.rmtree(tdir)


def test():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCapsulEngine)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    print("RETURNCODE: ", unittest.main())
