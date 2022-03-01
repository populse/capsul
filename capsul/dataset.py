# -*- coding: utf-8 -*-
import functools
import operator
import re

from soma.controller import Controller, Literal
from soma.undefined import undefined

from .api import Pipeline

class PathLayout(Controller):
    ''' Path layout for :class:`Dataset`

    Abstract class: derived classes should overload the :meth:`_build_path`
    static method to actually implement path building.

    This class is a :class:`~soma.controller.controller.Controller`: attributes
    are stored as fields.
    '''
    def build_path(self, **kwargs):
        ''' Returns a list of path elements built from the current PathLayout
        fields values.

        This method calls :meth:`_build_path` which should be implemented in
        subclasses.
        '''
        return self._build_path(self.asdict())

    @staticmethod
    def _build_path(attributes):
        raise NotImplementedError(
            '_build_path should be specialized in PathLayout subclasses.')


class BIDSLayout(PathLayout):
    ''' BIDS path layout for dataset
    '''
    folder: Literal['sourcedata', 'rawdata', 'derivative']
    pipeline: str = None
    sub: str
    ses: str
    data_type: str
    task: str = None
    acq: str = None
    ce: str = None
    rec: str = None
    run: str = None
    echo: str = None
    part: str = None
    suffix: str
    extension: str


    find_attrs = re.compile(
        r'(?P<folder>[^-_/]*)/'
        r'sub-(?P<sub>[^-_/]*)/'
        r'ses-(?P<ses>[^-_/]*)/'
        r'(?P<data_type>[^/]*)/'
        r'sub-(?P=sub)_ses-(?P=ses)'
        r'(?:_task-(?P<task>[^-_/]*))?'
        r'(?:_acq-(?P<acq>[^-_/]*))?'
        r'(?:_ce-(?P<ce>[^-_/]*))?'
        r'(?:_rec-(?P<rec>[^-_/]*))?'
        r'(?:_run-(?P<run>[^-_/]*))?'
        r'(?:_echo-(?P<echo>[^-_/]*))?'
        r'(?:_part-(?P<part>[^-_/]*))?'
        r'_(?P<suffix>[^-_/]*)\.(?P<extension>.*)$'
    )


    @staticmethod
    def _build_path(kwargs):
        '''
        The path has the following pattern:
          sub-{sub}/ses-{ses}/{data_type}/sub-{sub}_ses-{ses}[_task-{task}][_acq-{acq}][_ce-{ce}][_rec-{rec}][_run-{run}][_echo-{echo}][_part-{part}]{modality}.{extension}
        '''
        path_list = [kwargs["folder"]]
        if kwargs['pipeline']:
            path_list += [kwargs['pipeline']]
        path_list += [f'sub-{kwargs["sub"]}',
                      f'ses-{kwargs["ses"]}',
                      kwargs["data_type"]]

        filename = [f'sub-{kwargs["sub"]}',
                    f'ses-{kwargs["ses"]}']
        for key in ('task', 'acq', 'ce', 'rec', 'run', 'echo', 'part'):
            value = kwargs.get(key)
            if value:
                filename.append(f'{key}-{value}')
        filename.append(f'{kwargs["suffix"]}.{kwargs["extension"]}')
        path_list.append('_'.join(filename))
        return path_list


class BrainVISALayout(PathLayout):
    ''' BrainVISA path layout for dataset
    '''
    center: str
    subject: str
    modality: str = None
    process: str = None
    analysis:str = 'default'
    acquisition: str = None
    preprocessings: str = None
    longitudinal: list[str] = None
    prefix: str = None
    suffix: str = None
    extension: str = None

    find_attrs = re.compile(
        r'(?P<folder>[^-_/]*)/'
        r'sub-(?P<sub>[^-_/]*)/'
        r'ses-(?P<ses>[^-_/]*)/'
        r'(?P<data_type>[^/]*)/'
        r'sub-(?P=sub)_ses-(?P=ses)'
        r'(?:_task-(?P<task>[^-_/]*))?'
        r'_(?P<suffix>[^-_/]*)\.(?P<extension>.*)$'
    )

    @staticmethod
    def _build_path(kwargs):
        '''
        The path has the following pattern:
        {center}/{subject}/[{modality}/][{process/][{acquisition}/][{preprocessings}/][{longitudinal}/]{analysis}/[{prefix}_]{subject}[_to_avg_{longitudinal}}[_{suffix}][.{extension}]
        '''

        path_list = [kwargs['center'], kwargs['subject']]
        for key in ('modality', 'process', 'acquisition', 'preprocessings', 'longitudinal'):
            value = kwargs.get(key)
            if value:
                path_list.append(value)
        path_list.append(kwargs['analysis'])

        filename = []
        prefix = kwargs.get('prefix')
        if prefix:
            filename.append(f'{prefix}_')
        filename.append(kwargs['subject'])
        longitudinal = kwargs.get('longitudinal')
        if longitudinal:
            filename.append(f'_to_avg_{longitudinal}')
        suffix = kwargs.get('suffix')
        if suffix:
            filename.append(f'_{suffix}')
        extension = kwargs.get('extension')
        if extension:
            filename.append(f'.{extension}')
        path_list.append(''.join(filename))
        return path_list


class Dataset:
    ''' Dataset class
    '''
    layouts = {
        'bids': BIDSLayout,
        'brainvisa': BrainVISALayout,
    }
    def __init__(self, path, layout_str):
        self.path = path
        self.layout_name, self.layout_version = layout_str.split('-', 1)
        self.layout = self.layouts.get(self.layout_name)
        if not self.layout:
            raise ValueError(f'Invalid paths layout: {layout_str}')
    
    def find(self, **kwargs):
        ''' Find attributes values from existing files (using :func:`glob.glob`
        and filenames parsing)

        Returns
        -------
        Yields an attributes dict for every matching file path.
        '''
        layout = self.layout(**kwargs)
        kwargs = {}
        for field in layout.fields():
            value = getattr(layout, field.name, undefined) 
            if value is undefined:
                if not field.optional:
                    kwargs[field.name] = '*'
            else:
                kwargs[field.name] = value
        globs = layout._build_path(kwargs)
        directories = [self.path]
        while len(globs) > 1:
            new_directories = []
            for d in directories:
                for sd in d.glob(globs[0]):
                    if sd.is_dir():
                        new_directories.append(sd)
            globs = globs[1:]
            directories = new_directories
        for d in directories:
            for sd in d.glob(globs[0]):
                path = str(sd)[len(str(self.path))+1:]
                m = layout.find_attrs.match(path)
                if m:
                    result = m.groupdict()
                    result['path'] = str(sd)
                    yield result

    def set_output_paths(self, executable, **kwargs):
        ''' Operates completion for output values of an executable.
        '''
        global_attrs = getattr(executable, 'path_layout', {}).get('*', {})
        for field in executable.fields():
            if not field.is_output():
                continue
            if isinstance(executable, Pipeline):
                inner_item = next(executable.get_linked_items(executable, field.name), None)
                if inner_item is not None:
                    inner_process, inner_field_name = inner_item
                    inner_field = inner_process.field(inner_field_name)
                else:
                    inner_process = inner_field = None
            if field.is_path() or (inner_field and inner_field.is_path()):
                layout = self.layout(**kwargs)
                attrs = global_attrs.copy()
                process_attrs = getattr(executable, 'path_layout', {}).get(self.layout_name, {}).get(field.name)
                if process_attrs is None and inner_field:
                    process_attrs = getattr(inner_process, 'path_layout', {}).get(self.layout_name, {}).get(inner_field.name)
                if process_attrs:
                    attrs.update(process_attrs)
                for n, v in attrs.items():
                    setattr(layout, n, v)
                path = functools.reduce(operator.truediv, layout.build_path(), self.path)
                setattr(executable, field.name, str(path))
        if isinstance(executable, Pipeline):
            executable.set_temporary_file_names()
