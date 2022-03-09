# -*- coding: utf-8 -*-
'''
Matlab configuration module

Classes
=======
:class:`MatlabConfig`
---------------------
'''

from __future__ import print_function

from __future__ import absolute_import
import os
from traits.api import File, Undefined, Bool
from capsul.study_config.study_config import StudyConfigModule
from capsul.engine import CapsulEngine


class MatlabConfig(StudyConfigModule):
    '''
    Matlab path configuration
    '''

    def __init__(self, study_config, configuration):
        super(MatlabConfig, self).__init__(study_config, configuration)
        self.study_config.add_trait('matlab_exec', File(
            Undefined,
            output=False,
            desc='Matlab command path',
            exists=True,
            groups=['matlab']))
        self.study_config.add_trait("use_matlab", Bool(
            Undefined,
            desc="If True, Matlab configuration is set up on startup",
            groups=['matlab']))

    def initialize_module(self):
        """ Set up Matlab environment according to current configuration.
        """
        if not self.study_config.matlab_exec and self.study_config.use_matlab:
            # fix pathological config (appearing sometimes for an unknown reason)
            self.study_config.use_matlab = Undefined
        if 'capsul.engine.module.matlab' \
                not in self.study_config.engine._loaded_modules:
            self.study_config.engine.load_module('capsul.engine.module.matlab')

        if type(self.study_config.engine) is not CapsulEngine:
            # engine is a proxy, thus we are initialized from a real
            # CapsulEngine, which holds the reference values
            self.sync_from_engine()
        else:
            self.sync_to_engine()

        # the following should be moved to CapsulEngine module
        if self.study_config.use_matlab is False:
            # Configuration is explicitly asking not to use Matlab
            return

        if self.study_config.use_matlab is Undefined:
            # If use_matlab is not defined, Matlab configuration will
            # be done if possible but there will be no error if it cannot be
            # done.
            force_configuration = False
        else:
            # If use_matlab is True configuration must be valid otherwise
            # an EnvironmentError is raised
            force_configuration = True

        if self.study_config.matlab_exec is Undefined:
            # matlab_exec is not set, it will not be possible to activate
            #Matlab
            self.study_config.use_matlab = False
            if force_configuration:
                raise EnvironmentError('matlab_exec must be defined in order '
                                       'to use Matlab')
            return

        if not os.path.exists(self.study_config.matlab_exec):
            self.study_config.use_matlab = False
            if force_configuration:
                raise EnvironmentError('"%s" does not exists. Matlab '
                                      'configuration is not valid.' % \
                                      self.study_config.matlab_exec)
            return

    def initialize_callbacks(self):
        self.study_config.on_trait_change(self.sync_to_engine, 'matlab_exec')
        #  WARNING ref to self in callback
        self.study_config.engine.settings.module_notifiers[
            'capsul.engine.module.matlab'] = [self.sync_from_engine]

    def sync_to_engine(self, param=None, value=None):
        if param is not None:
            tparam = {'matlab_exec': 'executable'}
            ceparam = tparam.get(param)
        else:
            ceparam = 'executable'
            value = self.study_config.matlab_exec
            if value is Undefined:
                value = None
        if ceparam is not None:
            with self.study_config.engine.settings as session:
                config = session.config('matlab', 'global', any=True)
                if config is None:
                    if (ceparam !='executable'
                             or self.study_config.matlab_exec
                                not in (None, Undefined, '')):
                        cif = self.study_config.engine.settings.config_id_field
                        matlab_exec = self.study_config.matlab_exec
                        if matlab_exec is Undefined:
                            matlab_exec = None
                        session.new_config(
                            'matlab', 'global',
                            {'executable': matlab_exec,
                            cif: 'matlab'})
                else:
                    if value is Undefined:
                        value = None
                    setattr(config, ceparam, value)

    def sync_from_engine(self, param=None, value=None):
        self.use_matlab = None  # avoid transcient inconsistencies
        if param is not None:
            tparam = {'executable': 'matlab_exec'}
            scparam = tparam.get(param)
            if scparam is not None:
                if value is None:
                    value = Undefined
                setattr(self.study_config, scparam, value)
        else:
            if self.study_config.use_matlab:
                # in case we reset matlab_exec to Undefined
                self.study_config.use_matlab = Undefined
            with self.study_config.engine.settings as session:
                config = session.config('matlab', 'global', any=True)
                if config:
                    matlab_exec = config.executable
                    if matlab_exec is None:
                        matlab_exec = Undefined
                    self.study_config.matlab_exec = matlab_exec
        if self.study_config.matlab_exec not in (None, Undefined):
            self.study_config.use_matlab = True
