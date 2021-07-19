# -*- coding: utf-8 -*-
'''
Config module for :mod:`File Organization models (FOMs) <capsul.attributes.fom_completion_engine>`

Classes
=======
:class:`FomConfig`
------------------
'''

from __future__ import absolute_import
import os
import six
from traits.api import Bool, Str, Undefined, List, Directory
from soma.fom import AttributesToPaths, PathToAttributes
from soma.application import Application
from capsul.study_config.study_config import StudyConfigModule
from capsul.engine import CapsulEngine


class FomConfig(StudyConfigModule):
    '''FOM (File Organization Model) configuration module for StudyConfig

    .. note::
        :class:`~capsul.study_config.config_modules.fom_config.FomConfig`
        needs :class:`~capsul.study_config.config_modules.brainvisa_config.BrainVISAConfig`
        to be part of
        :class:`~capsul.study_config.study_config.StudyConfig` modules.

    This module adds the following options (traits) in the
    :class:`~capsul.study_config.study_config.StudyConfig` object:

    input_fom: str
        input FOM
    output_fom: str
        output FOM
    shared_fom: str
        shared data FOM
    volumes_format: str
        Format used for volumes
    meshes_format: str
        Format used for meshes
    auto_fom: bool (default: True)
        Look in all FOMs when a process is not found. Note that auto_fom
        looks for the first FOM matching the process to get
        completion for, and does not handle ambiguities. Moreover
        it brings an overhead (typically 6-7 seconds) the first
        time it is used since it has to parse all available FOMs.
    fom_path: list of directories
        list of additional directories where to look for FOMs (in addition to
        the standard share/foms)
    use_fom: bool
        Use File Organization Models for file parameters completion'

    *Methods:*
    '''

    dependencies = ['BrainVISAConfig', 'SPMConfig', 'AttributesConfig']

    def __init__(self, study_config, configuration):
        super(FomConfig, self).__init__(study_config, configuration)
        self.study_config.add_trait('input_fom', Str(Undefined, output=False,
            desc='input FOM', groups=['fom']))
        self.study_config.add_trait('output_fom', Str(Undefined, output=False,
            desc='output FOM', groups=['fom']))
        self.study_config.add_trait('shared_fom', Str(Undefined, output=False,
            desc='shared data FOM', groups=['fom']))
        self.study_config.add_trait('volumes_format',
                                    Str(Undefined, output=False,
            desc='Format used for volumes', groups=['fom']))
        self.study_config.add_trait('meshes_format',
                                    Str(Undefined, output=False,
            desc='Format used for meshes', groups=['fom']))
        self.study_config.add_trait(
            'auto_fom',
            Bool(True, output=False,
                 desc='Look in all FOMs when a process is not found (in '
                 'addition to the standard share/foms). Note that auto_fom '
                 'looks for the first FOM matching the process to get '
                 'completion for, and does not handle ambiguities. Moreover '
                 'it brings an overhead (typically 6-7 seconds) the first '
                 'time it is used since it has to parse all available FOMs.',
                 groups=['fom']))
        self.study_config.add_trait(
            'fom_path',
            List(Directory(output=False),
                 desc='list of additional directories where to look for FOMs',
                 groups=['fom']))
        self.study_config.add_trait('use_fom', Bool(
            Undefined,
            output=False,
            desc='Use File Organization Models for file parameters '
                'completion',
            groups=['fom']))

        # defaults
        self.study_config.input_fom = ""
        self.study_config.output_fom = ""
        self.study_config.shared_fom = ""
        self.study_config.modules_data.foms = {}
        self.study_config.modules_data.fom_atp = {}
        self.study_config.modules_data.fom_pta = {}


    def initialize_module(self):
        if 'capsul.engine.module.fom' \
                not in self.study_config.engine._loaded_modules:
            self.study_config.engine.load_module('capsul.engine.module.fom')

        if type(self.study_config.engine) is not CapsulEngine:
            # engine is a proxy, thus we are initialized from a real
            # CapsulEngine, which holds the reference values
            self.sync_from_engine()
        else:
            self.sync_to_engine()
            # 1st sync may have changed things
            self.sync_from_engine()

    def initialize_callbacks(self):
        self.study_config.on_trait_change(
            self.sync_to_engine,
            ['input_directory', 'input_fom', 'meshes_format',
             'output_directory', 'output_fom', 'shared_fom', 'volumes_format',
             'auto_fom', 'fom_path', 'shared_directory'])
        #  WARNING ref to self in callback
        self.study_config.engine.settings.module_notifiers[
            'capsul.engine.module.fom'].append(self.sync_from_engine)


    def sync_to_engine(self, param=None, value=None):
        params = ['input_fom', 'meshes_format', 'output_fom', 'shared_fom',
                  'volumes_format', 'input_directory', 'output_directory',
                  'auto_fom', 'fom_path']

        with self.study_config.engine.settings as session:
            config = session.config('fom', 'global')
            if config:
                if param in params:
                    params = [param]
                for p in params:
                    value = getattr(self.study_config, p)
                    if value is Undefined:
                        value = None
                    setattr(config, p, value)
            else:
                values = {}
                for p in params:
                    value = getattr(self.study_config, p)
                    if value is Undefined:
                        value = None
                    values[p] = value
                values[self.study_config.engine.settings.config_id_field] \
                    = 'fom'
                session.new_config('fom', 'global', values)


    def sync_from_engine(self, param=None, value=None):
        params = ['input_fom', 'meshes_format', 'output_fom', 'shared_fom',
                  'volumes_format', 'input_directory', 'output_directory',
                  'auto_fom', 'fom_path']
        if param is not None:
            params = [param]

        with self.study_config.engine.settings as session:
            config = session.config('fom', 'global')
            if not config:
                self.study_config.use_fom = False
                return
            for p in params:
                # print('sync_from_engine:', p, type(p))
                value = getattr(config, p)
                if value is None:
                    value = Undefined
                setattr(self.study_config, p, value)
            self.study_config.use_fom = True


    def load_fom(self, schema):
        with self.study_config.engine.settings as session:
            config = session.config('fom', 'global')
            if config:
                from capsul.engine.module.fom import load_fom
                return load_fom(self.study_config.engine, schema, config,
                                session, environment='global')
