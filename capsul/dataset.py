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
from capsul.pipeline.pipeline import Process, Pipeline, Switch

from soma.controller import Controller, Literal, Directory
from soma.undefined import undefined



class Dataset(Controller):
    '''
    Dataset representation.
    You don't need to define or instantiate this class yourself, it will be done automatically and internally in the path generation system.

    Instead, users need to define datsets in the Capsul config. See :func:`generate_paths`.
    '''
    path: Directory
    metadata_schema: str

    schemas = {}
    '''
    Schemas mapping associating a :class:`MetadataSchema` class to a name
    '''

    schema_mappings = {}
    '''
    Mapping between schemas couples and conversion functions
    '''

    def __init__(self, path=None, metadata_schema=None):
        super().__init__(self)
        self.on_attribute_change.add(self.schema_change_callback, 'metadata_schema')
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

    def schema_change_callback(self):
        schema_cls = self.find_schema(self.metadata_schema)
        if not schema_cls:
            raise ValueError(f'Invalid metadata schema "{self.metadata_schema}" for path "{self.path}"')
        self.schema = schema_cls(base_path=self.path)

    @classmethod
    def register_schema(cls, name, schema):
        cls.schemas[name] = schema

class MetadataSchema(Controller):
    '''Schema of metadata associated to a file in a :class:`Dataset`

    Abstract class: derived classes should overload the :meth:`_path_list`
    static method to actually implement path building.

    This class is a :class:`~soma.controller.controller.Controller`: attributes
    are stored as fields.
    '''
    def __init_subclass__(cls) -> None:
        result = super().__init_subclass__()
        Dataset.schemas[cls.schema_name] = cls
        return result

    def __init__(self, base_path='', **kwargs):
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
    schema_name = 'bids'

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

    def __init__(self, base_path='', **kwargs):
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
    schema_name = 'brainvisa'

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


class SchemaMapping:
    def __init_subclass__(cls) -> None:
        Dataset.schema_mappings[(cls.source_schema, cls.dest_schema)] = cls

class BidsToBrainVISA(SchemaMapping):
    source_schema = 'bids'
    dest_schema = 'brainvisa'

    @staticmethod
    def map_schemas(source, dest):
        dest.center = 'whaterver'
        dest.subject = source.sub
        dest.acquisition = source.ses
        dest.extension = source.extension
        process = getattr(source, 'process', None)
        if process:
            dest.process = process

class ProcessSchema:
    def __init_subclass__(cls, schema, process_class) -> None:
        super().__init_subclass__()
        if 'metadata_schemas' not in process_class.__dict__:
            process_class.metadata_schemas = {}
        schemas = process_class.metadata_schemas
        schemas[schema] = cls
        setattr(process_class, 'metadata_schemas', schemas)
    
    @classmethod
    def _update_metadata(cls, metadata, process, pipeline_name, parameter):
        stack = [
            getattr(cls, parameter, None),
            getattr(cls, f'{pipeline_name}.{parameter}', None),
            getattr(cls, '_', {}).get('*'),
        ]
        while stack:
            item = stack.pop(0)
            if item is None:
                continue
            elif isinstance(item, list):
                stack = item + stack
            elif isinstance(item, dict):
                for k, v in item.items():
                    setattr(metadata, k, v)
            else:
                stack.insert(0, item(metadata, process, parameter, pipeline_parameter))                
                

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


def dprint(debug, *args, **kwargs):
    if debug:
        import inspect
        frame = inspect.stack(context=0)[1]
        try:
            head = f'!{frame.function}:{frame.lineno}!'
        finally:
            del frame
        print(head, *args, **kwargs)


def dpprint(debug, item):
    if debug:
        from pprint import pprint
        dprint(debug=debug)
        pprint(item)


class ProcessMetadata(Controller):
    parameters_per_schema : dict[str, list[str]]
    dataset_per_parameter : dict

    def __init__(self, executable, execution_context, datasets=None):
        super().__init__()

        self.parameters_per_schema = {}
        self.dataset_per_parameter = {}

        # Associate each field to a dataset
        for field in executable.user_fields():
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
            if path_type:
                # Associates a Dataset name with the field
                dataset_name = getattr(field, 'dataset', None)
                # fallback 1: get in inner_field (of an inner process)
                if dataset_name is None and inner_field:
                    dataset_name = getattr(inner_field, 'dataset', None)
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
                dataset = getattr(execution_context.dataset, dataset_name, None)
                if dataset:
                    self.dataset_per_parameter[field.name] = dataset_name
                    schema = dataset.metadata_schema
                    self.parameters_per_schema.setdefault(schema, []).append(field.name)
        
        for schema_name in self.parameters_per_schema:
            schema_cls = Dataset.find_schema(schema_name)
            if schema_cls is None:
                raise ValueError(f'Cannot find metadata schema named "{schema_name}"')
            self.add_field(schema_name, type_=Controller)
            setattr(self, schema_name, schema_cls())

    def generate_paths(self, executable, debug=False):
        dprint(debug, executable.definition)
        for schema, parameters in self.parameters_per_schema.items():
            for parameter in parameters:
                dataset = self.dataset_per_parameter[parameter]
                metadata = Dataset.find_schema(schema)(base_path=f'!{{dataset.{dataset}.path}}')
                for other_schema in self.parameters_per_schema:
                    if other_schema == schema:
                        continue
                    mapping_class = Dataset.find_schema_mapping(other_schema, schema)
                    if not mapping_class:
                        continue
                    mapping_class.map_schemas(getattr(self, other_schema), metadata)
                schema_metadata = getattr(self, schema)
                for field in schema_metadata.fields():
                    value = getattr(schema_metadata, field.name, None)
                    if value is not None:
                        setattr(metadata, field.name, value)
                dprint(debug, '->', parameter, ':', schema)
                for path in self.follow_links(executable, parameter, debug=debug):
                    dprint(debug, 'path length', len(path))
                    for pipeline_name, process, process_parameter in reversed(path):
                        dprint(debug, pipeline_name, process.definition, process_parameter)
                        metadata_schema = getattr(process, 'metadata_schemas', {}).get(schema)
                        dprint(debug, 'metadata_schema =', metadata_schema)
                        if metadata_schema:
                            metadata_schema._update_metadata(metadata, executable, pipeline_name, process_parameter)
                dpprint(debug, metadata.asdict())
                path = str(metadata.build_path())
                dprint(debug, parameter, '=', path)
                setattr(executable, parameter, path)




    @staticmethod        
    def follow_links(executable, parameter_name, debug=False):
        dprint(debug, executable.definition, parameter_name)
        main_field = executable.field(parameter_name)
        if main_field.is_output():
            direction = 'links_from'
        else:
            direction = 'links_to'
        stack = [([], executable, main_field.name, [])]
        done = set()
        while stack:
            node_name_path, node, field_name, path = stack.pop(0)
            dprint(debug, node_name_path, str(node), field_name, '...')
            field = node.field(field_name)
            if node in done or not node.activated:
                continue
            done.add(node)
            plug = node.plugs.get(field.name)
            followers = []
            if isinstance(node, Switch):
                if field.name != 'switch':
                    for input_plug_name, output_plug_name in node.connections():
                        dprint(debug, 'switch', dest_plug_name, input_plug_name, output_plug_name, not main_field.is_output())
                        if not main_field.is_output():
                            if dest_plug_name == input_plug_name:
                                dprint(debug, 'append')
                                next_node, next_plug = next(executable.get_linked_items(
                                    node, output_plug_name))
                                stack.append((node_name_path, next_node, next_plug, path))
                        else:
                            if dest_plug_name == output_plug_name:
                                dprint(debug, 'append')
                                next_node, next_plug = next(executable.get_linked_items(
                                    node, input_plug_name))
                                stack.append((node_name_path, next_node, next_plug, path))
            elif isinstance(node, Process):
                path.append(('.'.join(node_name_path + [node.name]), node, field.name))
                if isinstance(node, Pipeline):
                    node_name = node.name
                else:
                    node_name = None
                for dest_plug_name, dest_node in (i[1:3] for i in getattr(plug, direction)):
                    if dest_node in done or not dest_node.activated:
                        continue
                    followers.append((node_name, dest_node, dest_plug_name))
            if followers:
                for next_node_name, next_node, next_plug in followers:
                    if next_node_name:
                        next_node_name_path = node_name_path + [next_node_name]
                    else:
                        next_node_name_path = node_name_path
                    stack.append((next_node_name_path, next_node, next_plug, path))
            else:
                yield path

