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
import traits.api as traits
from soma.fom import AttributesToPaths, PathToAttributes
from soma.application import Application
from soma.sorted_dictionary import SortedDictionary
import weakref
import capsul.engine
from functools import partial


def init_settings(capsul_engine):
    with capsul_engine.settings as session:
        session.ensure_module_fields('fom',
            [dict(name='input_fom', type='string', description='input FOM'),
             dict(name='output_fom', type='string', description='output FOM'),
             dict(name='shared_fom', type='string',
                  description='shared data FOM'),
             dict(name='volumes_format', type='string',
                  description='Format used for volumes'),
             dict(name='meshes_format', type='string',
                  description='Format used for meshes'),
             dict(name='auto_fom', type='boolean',
                  description='Look in all FOMs when a process is not found '
                  '(in addition to the standard share/foms). Note that '
                  'auto_fom looks for the first FOM matching the process to '
                  'get completion for, and does not handle ambiguities. '
                  'Moreover it brings an overhead (typically 6-7 seconds) the '
                  'first time it is used since it has to parse all available '
                  'FOMs.'),
             dict(name='fom_path', type='list_string',
                  description='list of additional directories where to look '
                  'for FOMs'),
             # FIXME: until directories are included in another config module
             dict(name='input_directory', type='string',
                  description='input study data directory'),
             dict(name='output_directory', type='string',
                  description='output study data directory'),
            ])

    capsul_engine.load_module('capsul.engine.module.axon')
    capsul_engine.load_module('capsul.engine.module.spm')
    capsul_engine.load_module('capsul.engine.module.attributes')

    with capsul_engine.settings as session:
        config = session.config('fom', 'global')
        if not config:
            values = {capsul_engine.settings.config_id_field: 'fom',
                      'auto_fom': True, 'fom_path': []}
            session.new_config('fom', 'global', values)

    if not hasattr(capsul_engine, '_modules_data'):
        capsul_engine._modules_data = {}
    store = capsul_engine._modules_data.setdefault('fom', {})
    store['foms'] = {}
    store['all_foms'] = SortedDictionary()
    store['fom_atp'] = {'all': {}}
    store['fom_pta'] = {'all': {}}

    capsul_engine.settings.module_notifiers['capsul.engine.module.fom'] \
        = [partial(fom_config_updated, weakref.proxy(capsul_engine), 'global')]
    capsul_engine.settings.module_notifiers.setdefault(
        'capsul.engine.module.axon', []).append(
            partial(config_updated, weakref.proxy(capsul_engine), 'global'))
    capsul_engine.settings.module_notifiers.setdefault(
        'capsul.engine.module.spm', []).append(
            partial(config_updated, weakref.proxy(capsul_engine), 'global'))

    # link with StudyConfig
    if hasattr(capsul_engine, 'study_config') \
            and 'FomConfig' not in capsul_engine.study_config.modules:
        scmod = capsul_engine.study_config.load_module('FomConfig', {})
        scmod.initialize_module()
        scmod.initialize_callbacks()

    update_fom(capsul_engine, 'global')


def config_dependencies(config):
    return {'axon': 'any', 'spm': 'any', 'attributes': 'any'}


def config_updated(capsul_engine, environment, param=None, value=None):
    if param in (None, 'directory', 'shared_directory'):
        update_fom(capsul_engine, environment)


def spm_config_updated(capsul_engine, environment, param=None, value=None):
    if param in (None, 'directory'):
        update_fom(capsul_engine, environment)


def fom_config_updated(capsul_engine, environment='global',
                       param=None, value=None):
    if param in ('volumes_format', 'meshes_format'):
        update_formats(capsul_engine, environment)
        return

    if param in ('fom_path', ):
        reset_foms(capsul_engine, environment)
        return

    # otherwise use update_fom()
    update_fom(capsul_engine, environment, param, value)


def update_fom(capsul_engine, environment='global', param=None, value=None):
    '''Load configured FOMs and create FOM completion data
    '''
    #print('***update_fom ***')
    with capsul_engine.settings as session:
        config = session.config('fom', environment)
        if config is None:
            return

        soma_app = Application('capsul', plugin_modules=['soma.fom'])
        if 'soma.fom' not in soma_app.loaded_plugin_modules:
            # WARNING: this is unsafe, may erase configured things, and
            # probably not thread-safe.
            soma_app.initialize()

        if config.fom_path:
            fom_path = [p for p in config.fom_path
                        if p not in soma_app.fom_path] \
                + soma_app.fom_path
        else:
            fom_path = list(soma_app.fom_path)

        soma_app.fom_manager.paths = fom_path
        soma_app.fom_manager.fom_files()

        store = capsul_engine._modules_data['fom']
        if config.auto_fom \
                and len(store['all_foms']) <= 3:
            for schema in soma_app.fom_manager.fom_files():
                if schema not in store['all_foms']:
                    store['all_foms'][schema] = None # not loaded yet.

        foms = (('input', config.input_fom),
                ('output', config.output_fom),
                ('shared', config.shared_fom))
        for fom_type, fom_filename in foms:
            if fom_filename not in ("", None, traits.Undefined):
                fom = store['all_foms'].get(fom_filename)
                if fom is None:
                    fom, atp, pta = load_fom(capsul_engine, fom_filename,
                                             config, session, environment)
                else:
                    atp = store['fom_atp']['all'][fom_filename]
                    pta = store['fom_pta']['all'][fom_filename]
                store['foms'][fom_type] = fom
                store['fom_atp'][fom_type] = atp
                store['fom_pta'][fom_type] = pta

        # update directories
        directories = {}
        spm = session.config('spm', environment)
        if spm:
            directories['spm'] = spm.directory
        axon = session.config('axon', environment)
        if axon:
            directories['shared'] = axon.shared_directory
        directories['input'] = config.input_directory
        directories['output'] = config.output_directory

        for atp in store['fom_atp']['all'].values():
            atp.directories = directories

        # backward compatibility for StudyConfig
        capsul_engine.study_config.modules_data.foms = store['foms']
        capsul_engine.study_config.modules_data.all_foms = store['all_foms']
        capsul_engine.study_config.modules_data.fom_atp = store['fom_atp']
        capsul_engine.study_config.modules_data.fom_pta = store['fom_pta']


def update_formats(capsul_engine, environment):
    with capsul_engine.settings as session:
        config = session.config('fom', environment)
        if config is None:
            return

        directories = {}
        spm = session.config('spm', environment)
        if spm:
            directories['spm'] = spm.directory
        axon = session.config('axon', environment)
        if axon:
            directories['shared'] = axon.shared_directory
        directories['input'] = config.input_directory
        directories['output'] = config.output_directory

        fields = config._dbs.get_fields_names(config._collection)
        formats = tuple(getattr(config, key) \
            for key in fields \
            if key.endswith('_format') \
                and getattr(config, key) is not None)

        store = capsul_engine._modules_data['fom']

        for schema, fom in store['all_foms'].items():
            if fom is None:
                continue

            atp = AttributesToPaths(
                fom,
                selection={},
                directories=directories,
                preferred_formats=set((formats)))
            old_atp = store['fom_atp']['all'].get(schema)
            store['fom_atp']['all'][schema] = atp
            if old_atp is not None:
                for t in ('input', 'output', 'shared'):
                    if store['fom_atp'].get(t) is old_atp:
                        store['fom_atp'][t] = atp


def load_fom(capsul_engine, schema, config, session, environment='global'):
    #print('=== load fom', schema, '===')
    #import time
    #t0 = time.time()
    soma_app = Application('capsul', plugin_modules=['soma.fom'])
    if 'soma.fom' not in soma_app.loaded_plugin_modules:
        # WARNING: this is unsafe, may erase configured things, and
        # probably not thread-safe.
        soma_app.initialize()
    old_fom_path = soma_app.fom_path
    if config.fom_path:
        soma_app.fom_path = [six.ensure_str(p) for p in config.fom_path
                             if p not in soma_app.fom_path] \
            + soma_app.fom_path
    else:
        soma_app.fom_path = list(soma_app.fom_path)
    fom = soma_app.fom_manager.load_foms(schema)
    soma_app.fom_path = old_fom_path
    store = capsul_engine._modules_data['fom']
    store['all_foms'][schema] = fom

    # Create FOM completion data
    fields = config._dbs.get_fields_names(config._collection)
    formats = tuple(getattr(config, key) \
        for key in fields \
        if key.endswith('_format') \
            and getattr(config, key) is not None)

    directories = {}
    spm = session.config('spm', environment)
    if spm:
        directories['spm'] = spm.directory
    axon = session.config('axon', environment)
    if axon:
        directories['shared'] = axon.shared_directory
    directories['input'] = config.input_directory
    directories['output'] = config.output_directory

    atp = AttributesToPaths(
        fom,
        selection={},
        directories=directories,
        preferred_formats=set((formats)))
    store['fom_atp']['all'][schema] = atp
    pta = PathToAttributes(fom, selection={})
    store['fom_pta']['all'][schema] = pta
    #print('   load fom done:', time.time() - t0, 's')
    return fom, atp, pta


def reset_foms(capsul_engine, environment):
    soma_app = Application('capsul', plugin_modules=['soma.fom'])
    if 'soma.fom' not in soma_app.loaded_plugin_modules:
        # WARNING: this is unsafe, may erase configured things, and
        # probably not thread-safe.
        soma_app.initialize()
    soma_app.fom_manager.clear_cache()
    update_fom(capsul_engine, environment)


def edition_widget(engine, environment, config_id='fom'):
    ''' Edition GUI for FOM config - see
    :class:`~capsul.qt_gui.widgets.settings_editor.SettingsEditor`
    '''
    from soma.qt_gui.controller_widget import ScrollControllerWidget
    from soma.controller import Controller
    import types

    def validate_config(widget):
        widget.update_controller()
        controller = widget.controller_widget.controller
        with widget.engine.settings as session:
            conf = session.config(config_id, widget.environment)
            values = {'config_id': config_id}
            for k in ('input_fom', 'output_fom', 'shared_fom',
                      'volumes_format', 'meshes_format', 'auto_fom',
                      'fom_path', 'input_directory', 'output_directory'):
                value = getattr(controller, k)
                if value is traits.Undefined:
                    if k in ('fom_path', ):
                        value = []
                    else:
                        value = None
                values[k] = value
            if conf is None:
                session.new_config(config_id, widget.environment, values)
            else:
                for k, value in values.items():
                    if k == 'config_id':
                        continue
                    setattr(conf, k, values[k])

    controller = Controller()

    controller.add_trait(
        'input_fom',
        traits.Str(traits.Undefined, output=False, desc='input FOM'))
    controller.add_trait(
        'output_fom',
        traits.Str(traits.Undefined, output=False, desc='output FOM'))
    controller.add_trait(
        'shared_fom',
        traits.Str(traits.Undefined, output=False, desc='shared data FOM'))
    controller.add_trait(
        'volumes_format',
        traits.Str(traits.Undefined, output=False, desc='Format used for volumes'))
    controller.add_trait(
        'meshes_format',
        traits.Str(traits.Undefined, output=False,
                   desc='Format used for meshes'))
    controller.add_trait(
        'auto_fom',
        traits.Bool(True, output=False,
              desc='Look in all FOMs when a process is not found (in '
              'addition to the standard share/foms). Note that auto_fom '
              'looks for the first FOM matching the process to get '
              'completion for, and does not handle ambiguities. Moreover '
              'it brings an overhead (typically 6-7 seconds) the first '
              'time it is used since it has to parse all available FOMs.'))
    controller.add_trait(
        'fom_path',
        traits.List(traits.Directory(output=False),
          desc='list of additional directories where to look for FOMs'))
    # FIXME: until directories are included in another config module
    controller.add_trait(
        'input_directory',
        traits.Directory(traits.Undefined, output=False,
                         desc='input study data directory'))
    controller.add_trait(
        'output_directory',
        traits.Directory(traits.Undefined, output=False,
                         desc='output study data directory'))

    conf = engine.settings.select_configurations(
        environment, {'fom': 'any'})
    if conf:
        fconf = conf.get(
            'capsul.engine.module.fom', {})
        controller.input_fom = fconf.get(
            'input_fom', traits.Undefined)
        controller.output_fom = fconf.get(
            'output_fom', traits.Undefined)
        controller.shared_fom = fconf.get(
            'shared_fom', traits.Undefined)
        controller.volumes_format= fconf.get(
            'volumes_format', traits.Undefined)
        controller.meshes_format = fconf.get(
            'meshes_format', traits.Undefined)
        controller.auto_fom = fconf.get(
            'auto_fom', traits.Undefined)
        controller.fom_path = fconf.get(
            'fom_path', traits.Undefined)
        controller.input_directory= fconf.get(
            'input_directory', traits.Undefined)
        controller.output_directory = fconf.get(
            'output_directory', traits.Undefined)

    widget = ScrollControllerWidget(controller, live=True)
    widget.engine = engine
    widget.environment = environment
    widget.accept = types.MethodType(validate_config, widget)

    return widget
