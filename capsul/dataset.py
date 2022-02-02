# -*- coding: utf-8 -*-
import functools
import operator
import re

from soma.controller import Controller, Literal
from soma.undefined import undefined

class PathLayout(Controller):
    def build_path(self, **kwargs):
        return self._build_path(self.as_dict())


class BIDSLayout(PathLayout):
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
    center: str
    subject: str
    modality: str = None
    process: str = None
    analysis:str
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
        if 'prefix' in kwargs:
            filename.append(f'{kwargs["prefix"]}_')
        filename.append(kwargs['subject'])
        if 'longitudinal' in kwargs:
            filename.append(f'_to_avg_{kwargs["longitudinal"]}')
        if 'suffix' in kwargs:
            filename.append(f'_{kwargs["suffix"]}')
        if 'extension' in kwargs:
            filename.append(f'.{kwargs["extension"]}')
        path_list.append(''.join(filename))
        return path_list


class Dataset:
    layouts = {
        'bids': BIDSLayout,
        'brainvisa': BrainVISALayout,
    }
    def __init__(self, path, layout_str):
        self.path = path
        name, version = layout_str.split('-', 1)
        self.layout = self.layouts.get(name)
        if not self.layout:
            raise ValueError(f'Invalid paths layout: {layout_str}')
    
    def find(self, **kwargs):
        layout = self.layout(**kwargs)
        kwargs = {}
        for field in layout.fields():
            value = getattr(layout, field.name, undefined) 
            if value is undefined:
                if not layout.is_optional(field.name):
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
        layout = self.layout(**kwargs)
        # for field in executable.fields():
        #     if executable.is_output(field) and executable.is_path(field):
                # ...
