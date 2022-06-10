# -*- coding: utf-8 -*-

'''
Metadata handling and attributes-based path generation system. In other words, this module is the completion system for Capsul processes and other executables.

The main function to be used contains most of the doc: see :func:`generate_paths`
'''

import csv
import functools
import json
import operator
from pathlib import Path
import re
import fnmatch

from soma.controller import Controller, Literal, Directory
from soma.undefined import undefined


class MetadataSchema(Controller):
    '''Schema of metadata associated to a file in a :class:`Dataset`

    Abstract class: derived classes should overload the :meth:`_path_list`
    static method to actually implement path building.

    This class is a :class:`~soma.controller.controller.Controller`: attributes
    are stored as fields.
    '''
    def __init__(self, base_path, **kwargs):
        super().__init__(**kwargs)
        if not isinstance(base_path, Path):
            self.base_path = Path(base_path)
        else:
            self.base_path = base_path

    def get(self, name, default=None):
        '''
        Shortcut to get an attribute with a None default value.
        Used in :meth:`_path_list` specialization to have a 
        shorter code.
        '''
        return getattr(self, name, default)

    def build_path(self):
        ''' Returns a list of path elements built from the current PathLayout
        fields values.

        This method calls :meth:`_path_listh` which should be implemented in
        subclasses.
        '''            
        return functools.reduce(operator.truediv,
                                self._path_list(),
                                self.base_path)

    def _path_list(self):
        raise NotImplementedError(
            '_path_list() must be specialized in MetadataSchema subclasses.')

    def metadata(self, path):
        '''
        Parse the ``path`` argument to extract an attributes dict from it.

        The base method is not implemented, it must be reimplemented in subclasses that allow path -> attributes parsing. Not all schemas will allow it.
        '''
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

    def __init__(self, base_path, **kwargs):
        super().__init__(base_path, **kwargs)

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
        if not isinstance(path, Path):
            path = Path(path)
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
        layout = self.__class__(self.base_path, **kwargs)
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
    '''Metadata schema for BrainVISA datasets.
    '''
    center: str
    subject: str
    modality: str = None
    process: str = None
    analysis: str = 'default_analysis'
    acquisition: str = None
    preprocessings: str = None
    longitudinal: list[str] = None
    seg_directory: str = None
    sulci_graph_version: str = None
    sulci_recognition_session: str = None
    prefix: str = None
    short_prefix: str = None
    suffix: str = None
    extension: str = None
    side: str = None
    sidebis: str = None  # when used as a sufffix

    find_attrs = re.compile(
        r'(?P<folder>[^-_/]*)/'
        r'sub-(?P<sub>[^-_/]*)/'
        r'ses-(?P<ses>[^-_/]*)/'
        r'(?P<data_type>[^/]*)/'
        r'sub-(?P=sub)_ses-(?P=ses)'
        r'(?:_task-(?P<task>[^-_/]*))?'
        r'_(?P<suffix>[^-_/]*)\.(?P<extension>.*)$'
    )

    def _path_list(self):
        '''
        The path has the following pattern:
        {center}/{subject}/[{modality}/][{process/][{acquisition}/][{preprocessings}/][{longitudinal}/][{analysis}/][seg_directory/][{sulci_graph_version}/[{sulci_recognition_session}]]/[side][{prefix}_][short_prefix]{subject}[_to_avg_{longitudinal}}[_{sidebis}{suffix}][.{extension}]
        '''

        attributes = tuple(f.name for f in self.fields())

        path_list = [self.center, self.subject]
        for key in ('modality', 'process', 'acquisition', 'preprocessings', 'longitudinal'):
            value = getattr(self, key, None)
            if value:
                path_list.append(value)
        if getattr(self, 'analysis', None):
            path_list.append(self.analysis)
        if self.seg_directory:
            path_list += self.seg_directory.split('/')
        if self.sulci_graph_version:
            path_list.append(self.sulci_graph_version)
            if self.sulci_recognition_session:
                path_list.append(self.sulci_recognition_session)

        filename = []
        if self.side:
            filename.append(f'{self.side}')
        if self.prefix:
            filename.append(f'{self.prefix}_')
        if self.short_prefix:
            filename.append(f'{self.short_prefix}')
        filename.append(self.subject)
        if self.longitudinal:
            filename.append(f'_to_avg_{self.longitudinal}')
        if self.suffix or self.sidebis:
            filename.append('_')
            if self.sidebis:
                filename.append(f'{self.sidebis}')
            if self.suffix:
                filename.append(f'{self.suffix}')
        if self.extension:
            filename.append(f'.{self.extension}')
        path_list.append(''.join(filename))
        return path_list

class ProcessSchema:
    def __init_subclass__(cls, schema, process_class) -> None:
        super().__init_subclass__()
        if 'metadata_schemas' not in process_class.__dict__:
            process_class.metadata_schemas = {}
        schemas = process_class.metadata_schemas
        schemas[schema] = cls
        setattr(process_class, 'metadata_schemas', schemas)
    
    @classmethod
    def _update_metadata(cls, metadata, process, parameter, iteration_index):
        stack = [
            getattr(cls, parameter, None),
            getattr(cls, '_', None),
        ]
        while stack:
            item = stack.pop(0)
            if item is None:
                continue
            elif isinstance(item, list):
                stack = item + stack
            elif isinstance(item, dict):
                metadata.update(item)
            else:
                stack.insert(0, item(metadata, process, parameter, iteration_index))


    @staticmethod
    def prepend(key, value, sep='_'):
        def prepend(metadata, process, parameter, iteration_index,
                    key=key, value=value,sep=sep):
            current_prefix = metadata.get(key)
            metadata[key] = value + (sep + current_prefix if current_prefix else '')
        return prepend

    @staticmethod
    def append(key, value, sep='_'):
        def append(metadata, process, parameter, iteration_index,
                   key=key, value=value,sep=sep):
            current_prefix = metadata.get(key)
            metadata[key] = (current_prefix + sep if current_prefix else '') + value
        return append


def bids_to_brainvisa(bids):
    result = dict(
        center='whaterver',
        subject=bids['sub'],
        acquisition=bids['ses'],
        extension = 'nii')
    process = bids.get('process')
    if process:
        result['process'] = process
    return result

class Dataset(Controller):
    '''
    Dataset representation.
    You don't need to define or instantiate this class yourself, it will be done automatically and internally in the path generation system.

    Instead, users need to define datsets in the Capsul config. See :func:`generate_paths`.
    '''
    path: Directory
    metadata_schema: str

    schemas = {
        'bids': BIDSSchema,
        'brainvisa': BrainVISASchema,
    }
    '''
    Schemas mapping associating a :class:`MetadataSchema` class to a name
    '''

    schema_mappings = {
        ('bids', 'brainvisa'): bids_to_brainvisa,
    }
    '''
    Mapping between schemas couples and conversion functions
    '''

    def __init__(self, path=None, metadata_schema=None):
        super().__init__(self)
        self.on_attribute_change.add(self.changed_schema, 'metadata_schema')
        if path is not None:
            if isinstance(path, Path):
                self.path = str(path)
            else:
                self.path = path          
            if metadata_schema is None:
                capsul_json = Path(self.path) / 'capsul.json'
                if capsul_json.exists():
                    with capsul_json.open() as f:
                        metadata_schema = json.load(f).get('metadata_schema')
        if metadata_schema:
            self.metadata_schema = metadata_schema
    
    @classmethod
    def find_schema(cls, metadata_schema):
        return cls.schemas.get(metadata_schema)

    @classmethod
    def find_schema_mapping(cls, source_schema, target_schema):
        return cls.schema_mappings.get((source_schema, target_schema))

    def find(self, **kwargs):
        yield from self.schema(self.path).find(**kwargs)

    def changed_schema(self):
        self.schema = self.find_schema(self.metadata_schema)
        if not self.schema:
            raise ValueError(f'Invalid metadata schema "{self.metadata_schema}" for path "{self.path}"')

    @classmethod
    def register_schema(cls, name, schema):
        cls.schemas[name] = schema

def generate_paths(executable, context, metadata=None, fields=None,
                   ignore=None, datasets=None, source_fields=None,
                   debug=False):
    ''' Generate path values for a given executable (node, process or pipeline), which actually implements completion.

    In order to work, several things need to be setup first:

    - define or use :class:`MetadataSchema` subclasses, such as :class:`BIDSSchema` or :class:`BrainVISASchema`, which role is to store attribute values for executable parameters

    - add new schema classes to :attr:`Dataset.schemas`

    - define Datasets (data directories) and the schema they are using in the Capsul config. Each dataset has a name::

        config = {
            'local': {
                'dataset': {
                    'input': {
                        'path': '/data/bids_database',
                        'metadata_schema': 'bids',
                    },
                    'output': {
                        'path': '/data/brainvisa_database',
                        'metadata_schema': 'brainvisa',
                    }
                }
            }
        }
        capsul = Capsul()
        capsul.config.import_dict(config)

      Note that default names ``input`` and ``output`` are used according to the fields input/output states, if no other are specified, and unless the path generation system is told not to do so.

    - define a mapping between executables fields and the dataset they are using. This can be done in two different ways:

      1. When defining executable traits, set ``dataset`` in their metadata::

          class TestProcess(Process):
              input_param: field(type_=File, dataset='input_dataset')
              output_param: field(type_=File, dataset='output_dataset')

      2. Externally by providing the ``datasets`` parameter dict to the ``generate_paths`` function::

            datasets = {
                't1mri': 'input_dataset',
                'template': 'shared_dataset',
                'segmented_mri': 'output_dataset'
            }
            generate_paths(executable, context, datasets=datasets)

    - define attributes values associated to executable parameters. This is defined in executables ``metadata_schema`` variable, and it is a dict which can define values for every possible schema. For instance if we have 3 schemas, ``bids``, ``braivisa`` and ``shared`` defined in :attr:`Dataset.schemas`::

        Morphologist.metadata_schema = dict(
            bids={
                '*': {'pipeline': 'morphologist'},
                'left_labelled_graph': {'part': 'left_hemi'},
                'right_labelled_graph': {'part': 'right_hemi'},
            },
            brainvisa={
                '*': {'modality': 't1mri'},
                'imported_t1mri': {'analysis': undefined},
                'left_labelled_graph': {
                    'seg_directory': 'folds',
                    'sulci_graph_version': '3.1',
                    'sulci_recognition_session': 'default_session_auto',
                    'short_prefix': 'L',
                    'suffix': 'default_session_auto',
                    'extension': 'arg'},
                'right_labelled_graph': {
                    'seg_directory': 'folds',
                    'sulci_graph_version': '3.1',
                    'sulci_recognition_session': 'default_session_auto',
                    'short_prefix': 'R',
                    'suffix': 'default_session_auto',
                    'extension': 'arg'},
                'Talairach_transform': {
                    'analysis': undefined,
                    'seg_directory': 'registration',
                    'short_prefix': 'RawT1-',
                    'suffix': '%(acquisition)s_TO_Talairach-ACPC',
                    'extension': 'trm'},
            },
            shared={
                'template': {'data_id': 'normalization_template'}
            },
        )

      The special entry ``*`` in each schema dict is used as default for all parameters in the executable.

    - finally, instantiate the process and set its input parameter(s) and call ``generate_paths``::

        process = executable(
            'capsul.pipeline.test.fake_morphologist.morphologist.Morphologist')
        process.t1mri = '/data/bids_database/rawdata/sub-aleksander/ses-m0/anat/sub-aleksander_ses-m0_T1w.nii'
        execution_context = capsul.engine.execution_context(process)
        generate_paths(process, execution_context, datasets=datasets,
                       source_fields=['t1mri'])

    Parameters
    ----------
    executable: executable :class:`~capsul.process.node.Node` instance
        The executable to perform parameters paths generation on. Its parameters values will be modified after the operation (it is the goal).
    context: Capsul execution context (:class:`capsul.execution_context.ExecutionContext` instance)
        obtained for the executable from the capsul engine::

            execution_context = capsul.engine.execution_context(process)

    metadata: dict[str, str] (optional)
        initial metadata values
    fields: iterable (optional)
        a list of field instances or names that will be processed in the executable. If not specified, all fields will be used, otherwise the path generation will be limited to the given fields.
    ignore: list[str] (optional)
        fields names to be ignored. If ``fields`` is used, ``ignore`` is pretty pointless.
    datasets: dict[str, str] (optional)
        mapping between fields names and dataset names. Used when fields themselves do not have the ``dataset`` metadata.
    source_fields: list[str] (optional)
        if not specified, any field which actually has a path value in the executable will be considered as a "source", and any path fields with no value will be considered as a "target". A "source" means that it will be parsed for attributes in its dataset schema: attributes will be infered from the parsing of the value (for this, the :class:`MetadataSchema` used for it must have a :meth:`~MetadataSchema.metadata` method defined). Values will then, in turn, be used to generate paths for "target" fields.
        If ``source_fields`` is specified, then only the fields listed here will be considered as "sources", thus path generation will override other fields values when they already have one.
    debug: bool or file-like object (optional)
        Print debug information while generating paths. ``debug`` may be ``True`` (print to ``stdout``) or a file-like object, with a ``write`` method.
    '''
    # avoid circular import
    from capsul.pipeline.pipeline import Pipeline
    from capsul.pipeline import pipeline_tools

    def dprint(*args, **kwargs):
        if debug:
            if debug is True:
                import sys
                file = sys.stderr
            else:
                file = debug

    if metadata is None:
        metadata = {}
    dprint('generate_paths:', executable.name)
    dprint('metadata:', metadata)
    source_field_per_schema = {}
    target_field_per_schema = {}
    dataset_name_per_field = {}

    if fields is None:
        fields = executable.user_fields()
    else:
        fields = (executable.field(i) for i in fields)
    for field in fields:
        if ignore and field.name in ignore:
            continue
        inner_field = None
        inner_field_name = None
        if isinstance(executable, Pipeline):
            inner_item = next(executable.get_linked_items(
                                executable, field.name), None)
        else:
            inner_item = None
        if inner_item is not None:
            inner_process, inner_field_name = inner_item
            path_type = inner_process.field(inner_field_name).path_type
        else:
            path_type = field.path_type
        dprint(f'field {field.name}: path_type = {path_type}')
        if path_type:
            # Associates a Dataset name with the field
            dataset_name = getattr(field, 'dataset', None)
            # fallback 1: get in inner_field (of an inner process)
            if dataset_name is None and inner_field:
                dataset_name = getattr(inner_field, 'dataset', None)
                if dataset_name:
                    dprint(f'dataset taken from inner field: {inner_process.name}.{inner_field_name}')
            # fallback 2: get manually given datasets
            if dataset_name is None and datasets:
                dataset_name = datasets.get(field.name)
            # fallback 3: use "input" or "output"
            if dataset_name is None and (not datasets
                                         or field.name not in datasets):
                dataset_name = ('output' if field.is_output() else 'input')
            if dataset_name is None:
                # no completion for this field
                continue
            dataset = getattr(context.dataset, dataset_name, None)
            value = getattr(executable, field.name, undefined)
            dprint(f'dataset: {dataset}, value: {value}')
            if value is undefined or (source_fields is not None
                                      and field.name not in source_fields):
                if dataset is None:
                    if not field.optional:
                        raise ValueError(f'No dataset "{dataset_name}" found '
                            'in execution context. It is required to generate '
                            f'path for parameter "{field.name}"')
                else:
                    dprint(f'target field {field.name} -> dataset {dataset_name}: schema {dataset.metadata_schema}')
                    dataset_name_per_field[field] = dataset_name
                    target_field_per_schema.setdefault(dataset.metadata_schema, []).append(field) 
            else:
                if dataset is not None:
                    dprint(f'source field {field.name} -> dataset {dataset_name}: schema {dataset.metadata_schema}')
                    dataset_name_per_field[field] = dataset_name
                    source_field_per_schema.setdefault(dataset.metadata_schema, []).append(field) 
                else:
                    dprint(f'source field {field.name} -> ignored because dataset {dataset_name} not found')

    initial_metadata = metadata

    if not target_field_per_schema:
        return

    for target_schema_name, target_fields in target_field_per_schema.items():
        target_schema = Dataset.find_schema(target_schema_name)
        if target_schema is None:
            raise ValueError(f'Cannot find metadata schema {target_schema_name}')

        metadata = initial_metadata

        global_metadata = getattr(executable, 'metadata_schema',
                                  {}).get(target_schema_name, {}).get('*', {})

        target_list_fields = [i for i in target_fields if i.is_list()]
        if target_list_fields and len(target_list_fields) != len(target_fields):
            l = ', '.join(i.name for i in target_list_fields)
            s = ', '.join(i.name for i in target_fields if not i.is_list())
            raise ValueError(f'Cannot generate paths for parameters {l} that are expecting lists ans {s} that are single paths')

        if isinstance(metadata, (list, tuple)):
            target_list_size = len(metadata)
        else:
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
        source_metadatas = ([{'list_index': 0}] if target_list_size is None
                            else [{'list_index': i} for i in range(target_list_size)])
        if not isinstance(metadata, (list, tuple)):
            metadata = [metadata] * (1 if target_list_size is None else target_list_size)
        dprint(f'target schema = {target_schema_name}')
        dprint(f'target list size = {target_list_size}')
        dprint(f'global_metadata = {global_metadata}')

        for source_schema_name, source_fields in source_field_per_schema.items():
            dprint(f'schema {source_schema_name} -> source fields: {", ".join(i.name for i in source_fields)}')
            source_schema = Dataset.find_schema(source_schema_name)
            if not source_schema:
                dprint(f'cannot get schema {source_schema_name}')
                continue
            if source_schema_name != target_schema_name:
                mapping = Dataset.find_schema_mapping(source_schema_name, target_schema_name)
                if mapping is None:
                    dprint(f'cannot get mapping between schemas {source_schema_name} and {target_schema_name}')
                    continue
            else:
                mapping = None
            for list_index in ((None,) if target_list_size is None else range(target_list_size)):
                merged_metadata = source_metadatas[(0 if list_index is None else list_index)]
                dprint(f'list_index: {list_index}: {merged_metadata}')
                for field in source_fields:
                    path = getattr(executable, field.name)
                    if isinstance(path, list):
                        path = path[list_index]
                    dprint(f'source path for: {field.name}: {path}')
                    schema = source_schema(context.dataset[dataset_name_per_field[field]].path)
                    path_metadata = schema.metadata(path)
                    dprint(f'path {path} -> {path_metadata}')
                    if mapping is not None:
                        path_metadata = mapping(path_metadata)
                    dprint(f'schema mapping -> {path_metadata}')
                    for k, v in path_metadata.items():
                        if k in merged_metadata:
                            if merged_metadata[k] != v:
                                merged_metadata[k] = undefined
                        else:
                            merged_metadata[k] = v
                    dprint(f'merged metadata -> {merged_metadata}')

        for field in target_fields:
            if isinstance(executable, Pipeline):
                inner_item = next(executable.get_linked_items(
                                    executable, field.name), None)
            else:
                inner_item = None
            if inner_item is not None:
                inner_process, inner_field_name = inner_item
                inner_field = inner_process.field(inner_field_name)
                dprint(f'inner field for {field.name}: {inner_process.name}.{inner_field_name} ({inner_process.definition})')
            else:
                inner_process = inner_field = inner_field_name = None
            values = []
            for source_metadata in source_metadatas:
                target_metadata = dict((k, v) for k, v in source_metadata.items() if v is not undefined)
                dprint(f'for {field.name}: source_metadata = {target_metadata}')
                target_metadata.update(global_metadata)
                dprint(f'for {field.name}: given metadata = {metadata[source_metadata["list_index"]]}')
                target_metadata.update(metadata[source_metadata['list_index']])
                if inner_field:
                    inner_metadata_schema = getattr(inner_process, 'metadata_schemas', {}).get(target_schema_name)
                    if inner_metadata_schema:
                        inner_metadata_schema._update_metadata(target_metadata, inner_process, inner_field.name, None)
                outer_metadata_schema = getattr(executable, 'metadata_schemas', {}).get(target_schema_name)
                if outer_metadata_schema:
                    outer_metadata_schema._update_metadata(target_metadata, executable, field.name, None)                
                dprint(f'for {field.name}: target_metadata = {target_metadata}')
                schema = target_schema(f'{{dataset.{dataset_name_per_field[field]}.path}}')
                dprint('schema:', schema)
                d = None
                for k, v in target_metadata.items():
                    if isinstance(v, str) and v and v.startswith('!'):
                        if d is None:
                            d = {
                                'list_index': source_metadata.get('list_index'),
                                'executable': executable,
                                'pipeline': executable,
                                'field': field.name,
                                'pipeline_field': field.name,
                            }
                            if inner_process:
                                d['executable'] = inner_process
                                d['field'] = inner_field_name
                            d.update(target_metadata)
                        #print('eval:', f"f'{v[1:]}'", 'with exec:', d['executable'])
                        v = eval(f"f'{v[1:]}'", d, d)
                        #print('->', v)
                    setattr(schema, k, v)
                    # update d
                    if d is not None:
                        d[k] = v
                values.append('!' + str(schema.build_path()))
            if target_list_size is None:
                dprint(f'set value for {executable.name}.{field.name}:', values[0])
                setattr(executable, field.name, values[0])
            else:
                dprint(f'set value for {executable.name}.{field.name}:', values)
                setattr(executable, field.name, values)
