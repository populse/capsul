# -*- coding: utf-8 -*-
import csv
import functools
import json
import operator
from pathlib import Path
import re

from soma.controller import Controller, Literal
from soma.undefined import undefined

# from .api import Pipeline
# from .pipeline.process_iteration import ProcessIteration


class MetadataSchema(Controller):
    '''Schema of metadata associated to a file in a :class:`Dataset`

    Abstract class: derived classes should overload the :meth:`_path_list`
    static method to actually implement path building.

    This class is a :class:`~soma.controller.controller.Controller`: attributes
    are stored as fields.
    '''
    def __init__(self, base_path):
        if not isinstance(base_path, Path):
            self.base_path = Path(base_path)
        else:
            self.base_path = base_path

    def get(self, name, default=None):
        '''
        Shortcut to get an attribute with a None default value.
        Used in :meth:`_path_listh` specialization to have a 
        shorter code.
        '''
        return getattr(self, name, value)

    def build_path(self, base):
        ''' Returns a list of path elements built from the current PathLayout
        fields values.

        This method calls :meth:`_path_listh` which should be implemented in
        subclasses.
        '''            
        return functools.reduce(operator.truediv,
                                self._path_list(),
                                self.base_path)

    def _path_list():
        raise NotImplementedError(
            '_path_list() must be specialized in MetadataSchema subclasses.')

    def metadata(self, path):
        raise NotImplementedError(
            'metadata() must be specialized in MetadataSchema subclasses.')


class BIDSSchema(MetadataSchema):
    ''' Metadata schema for BIDS datasets
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

    path_pattern = re.compile(
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

    def __init__(self, base_path):
        super().__init__(base_path)

        # Cache of TSV files that are already read and converted
        # to a dictionary
        self._tsv_to_dict = {}

    def _path_list(self):
        '''
        The path has the following pattern:
          sub-{sub}/ses-{ses}/{data_type}/sub-{sub}_ses-{ses}[_task-{task}][_acq-{acq}][_ce-{ce}][_rec-{rec}][_run-{run}][_echo-{echo}][_part-{part}]{modality}.{extension}
        '''
        path_list = [self.folder]
        if self.pipeline:
            path_list += [self.pipeline]
        path_list += [f'sub-{self.sub}',
                      f'ses-{self.ses}',
                      self.data_type]

        filename = [f'sub-{self.sub}',
                    f'ses-{self.ses}']
        for key in ('task', 'acq', 'ce', 'rec', 'run', 'echo', 'part'):
            value = getattr(self, key, undefined)
            if value:
                filename.append(f'{key}-{value}')
        filename.append(f'{self.suffix}.{self.extension}')
        path_list.append('_'.join(filename))
        return path_list
    
    def tsv_to_dict(self, tsv):
        '''
        Reads a TSV file and convert it to a dictionary of dictionaries
        using the first row value as key and other row values are converted
        to dict. The first row must contains column names.
        '''
        result = self._tsv_to_dict.get(tsv)
        if result is None:
            result = {}
            with open(tsv) as f:
                reader = csv.reader(f, dialect='excel-tab')
                header = next(reader)[1:]
                for row in reader:
                    key = row[0]
                    value = dict(zip(header, row[1:]))
                    result[key] = value
            self._tsv_to_dict[tsv] = result
        return result

    def metadata(self, path):
        '''
        Get metadata from BIDS files given its path.
        During the process, TSV files that are read and converted
        to dictionaries values are cached in self. That way if the same
        BIDSMetadata is used to get metadata of many files, there
        will be only one reading and conversion per file.
        '''
        result = {}
        if path.is_absolute():
            relative_path = path.relative_to(self.base_path)
        else:
            relative_path = path
            path = self.base_path / path
        if path.exists():
            m = self.path_pattern.match(str(relative_path))
            if m:
                result.update((k,v) for k, v in m.groupdict().items() if v is not None)
            folder = result.get('folder')
            sub = result.get('sub')
            if folder and sub:
                ses = result.get('ses')
                if ses:
                    sessions_file = self.base_path / folder / f'sub-{sub}' /  f'sub-{sub}_sessions.tsv'
                    if sessions_file.exists():
                        sessions_data = self.tsv_to_dict(sessions_file)
                        session_metadata = sessions_data.get(f'ses-{ses}', {})
                        result.update(session_metadata)
                    scans_file = self.base_path / folder / f'sub-{sub}' / f'ses-{ses}' / f'sub-{sub}_ses-{ses}_scans.tsv'
                else:
                    scans_file = self.base_path / folder / f'sub-{sub}' / f'sub-{sub}_scans.tsv'
                if scans_file.exists():
                    scans_data = self.tsv_to_dict(scans_file)
                    scan_metadata = scans_data.get(str(path.relative_to(scans_file.parent)), {})
                    result.update(scan_metadata)
                extension = result.get('extension')
                if extension:
                    json_path = path.parent / (path.name[:-len(extension)-1] + '.json')
                else:
                    json_path = path.parent / (path.name + '.json')                    
                if json_path.exists():
                    with open(json_path) as f:
                        result.update(json.load(f))
        return result

    def find(self, **kwargs):
        ''' Find path from existing files given fixed values for some parameters
        (using :func:`glob.glob` and filenames parsing)

        Returns
        -------
        Yields a path for every match.
        '''
        layout = self.__class__(**kwargs)
        for field in layout.fields():
            value = getattr(layout, field.name, undefined) 
            if value is undefined:
                if not field.optional:
                    # Force the value of the attribute without
                    # using Pydantic validation because '*' may
                    # not be a valid value.
                    object.__setattr__(layout, field.name, '*')
        globs = layout._path_list()
        directories = [self.base_path]
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
                yield sd
                

class BrainVISASchema(MetadataSchema):
    '''Metadata schema for BrainVISA datasets
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
    def _path_list(self):
        '''
        The path has the following pattern:
        {center}/{subject}/[{modality}/][{process/][{acquisition}/][{preprocessings}/][{longitudinal}/]{analysis}/[{prefix}_]{subject}[_to_avg_{longitudinal}}[_{suffix}][.{extension}]
        '''

        path_list = [self.center, self.subject]
        for key in ('modality', 'process', 'acquisition', 'preprocessings', 'longitudinal'):
            value = getattr(self, key, None)
            if value:
                path_list.append(value)
        path_list.append(self.analysis)

        filename = []
        prefix = self.get('prefix')
        if prefix:
            filename.append(f'{prefix}_')
        filename.append(self.subject)
        longitudinal = self.get('longitudinal')
        if longitudinal:
            filename.append(f'_to_avg_{longitudinal}')
        suffix = self.get('suffix')
        if suffix:
            filename.append(f'_{suffix}')
        extension = self.get('extension')
        if extension:
            filename.append(f'.{extension}')
        path_list.append(''.join(filename))
        return path_list

def bids_to_brainvisa(bids):
    return dict(
        center='whaterver',
        subject=bids['sub'],
        acquisition=bids['ses'],
        extension = 'nii')

class Dataset:
    ''' Dataset class
    '''
    schemas = {
        'bids': BIDSSchema,
        'brainvisa': BrainVISASchema,
    }

    schema_mappings = {
        ('brainvisa', 'bids'): bids_to_brainvisa,
    }

    def __init__(self, path, schema=None):
        if isinstance(path, Path):
            self.path = path
        else:
            self.path = Path(path)          
        if schema is None:
            capsul_json = self.path / 'capsul.json'
            if capsul_json.exists():
                with capsul_json.open() as f:
                    schema = json.load(f).get('metadata_schema')
            if schema is None:
                schema = 'bids'
        self.schema_name = schema
        self.schema = self.find_schema(self.schema_name)
        if not self.schema:
            raise ValueError(f'Invalid metadata schema "{schema}" for path "{path}"')
    
    @classmethod
    def find_schema(cls, schema_name):
        return cls.schemas.get(schema_name)

    @classmethod
    def find_schema_mapping(cls, source_schema, target_schema):
        return cls.schema_mappings.get((source_schema, target_schema))

    def find(self, **kwargs):
        yield from self.schema.find(self.path, **kwargs)


def generate_paths(self, executable, context):
    source_field_per_schema = {}
    target_field_per_schema = {}
    dataset_name_per_field = {}
    for field in executable.fields():
        if field.path_type:
            # Associates a Dataset name with the field
            dataset_name = getattr(field, 'dataset', None)
            if dataset_name is None:
                dataset_name = ('output' if field.is_output() else 'input')
            dataset = None
            datasets = getattr(context, 'datasets', None)
            if datasets:
                dataset = getattr(context, dataset_name, None)
            value = getattr(executable, field.name, undefined)
            if value is undefined:
                if dataset is None:
                    if not field.optional:
                        raise ValueError(f'No dataset "{dataset_name}" found '
                            'in execution context. It is required to generate '
                            f'path for parameter "{field.name}"')
                else:
                    dataset_name_per_field[field] = dataset_name
                    target_field_per_schema.setdefault(dataset.schema_name, []).append(field) 
            else:
                if dataset is not None:
                    source_field_per_schema.setdefault(dataset.schema_name, []).append(field) 

    if len(target_field_per_schema) > 1:
        raise ValueError(f'Found several metadata schemas in path parameters with missing value: {", ".join(target_field_per_schema)}')
    target_schema_name, target_fields = target_field_per_schema.pop()
    if not target_fields:
        return
    target_schema = Dataset.find_schema(target_schema_name)
    if target_schema is None:
        raise ValueError(f'Cannot find metadata schema {target_schema_name}')

    global_metadata = getattr(executable, 'metadata_schema', {}).get(target_schema_name, {}).get('*', {})

    target_list_fields = [i for i in target_fields if i.is_list()]
    if target_list_fields and len(target_list_fields) != len(target_fields):
        l = ', '.join(i.name for i in target_list_fields)
        s = ', '.join(i.name for i in target_fields if not i.is_list())
        raise ValueError(f'Cannot generate paths for parameters {l} that are expecting lists ans {s} that are single paths')

    target_list_size = None
    if target_list_fields:
        for source_schema_name, source_fields in source_field_per_schema.items():
            for field in source_fields:
                value = getattr(executable, field.name, undefined)
                if isinstance(value, list):
                    l = len(value)
                    if target_list_size is not None and target_list_size != l:
                        raise ValueError('Lists of different sizes given to generate paths')
                    target_list_size = l
    source_metadatas = ([{}] * target_list_size if target_list_size is None else [{}])

    for source_schema_name, source_fields in source_field_per_schema.items():
        source_schema = Dataset.find_schema(source_schema_name)
        if not source_schema:
            continue
        if source_schema_name != target_schema_name:
            mapping = Dataset.find_schema_mapping(source_schema_name, target_schema_name)
            if mapping is None:
                continue
        else:
            mapping = None
        for list_index in ((None,) if target_list_size is None else range(target_list_size)):
            merged_metadata = source_metadata[(0 if list_index is None else list_index)]
            for field in source_fields:
                path = getattr(executable, field.name)
                if isinstance(path, list):
                    path = path[list_index]
                path_metadata = source_schema.metadata(path)
                if mapping is not None:
                    path_metadata = mapping(path_metadata)
                for k, v in path_metadata.items():
                    if k in merged_metadata:
                        if merged_metadata[k] != v:
                            merged_metadata[k] = undefined
                    else:
                        merged_metadata[k] = v

    for field in target_fields:
        inner_item = next(executable.get_linked_items(
                            executable, field.name), None)
        if inner_item is not None:
            inner_process, inner_field_name = inner_item
            inner_field = inner_process.field(inner_field_name)
        else:
            inner_process = inner_field = None
        values = []
        for source_metadata in source_metadatas:
            target_metadata = dict((k, v) for k, v in source_metadata if v is not undefined)
            target_metadata.update(global_metadata)
            field_metadata = getattr(
                executable, 'metadata_schema', {}).get(target_schema_name,
                    {}).get(field.name)
            if field_metadata is None and inner_field:
                field_metadata = getattr(
                    inner_process, 'metadata_schema',
                    {}).get(target_schema_name, {}).get(inner_field.name)
            if field_metadata:
                target_metadata.update(field_metadata)
            schema = target_schema(dataset_name_per_field[field])
            for k, v in target_metadata.items():
                setattr(schema, k, v)
            values.append(schema.build_path())
        if target_list_size is None:
            setattr(executable, field.name, values[0])
        else:
            setattr(executable, field.name, values)

