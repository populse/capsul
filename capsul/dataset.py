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
from capsul.pipeline.pipeline import Process, Pipeline, Switch
from capsul.pipeline.process_iteration import ProcessIteration

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
        yield from self.schema.find(**kwargs)

    def schema_change_callback(self):
        schema_cls = self.find_schema(self.metadata_schema)
        if not schema_cls:
            raise ValueError(f'Invalid metadata schema "{self.metadata_schema}" for path "{self.path}"')
        self.schema = schema_cls(base_path=self.path)

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
    process: str = None
    sub: str
    ses: str
    data_type: str = None
    task: str = None
    acq: str = None
    ce: str = None
    rec: str = None
    run: str = None
    echo: str = None
    part: str = None
    suffix: str = None
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
        r'(?:_(?P<suffix>[^-_/]*))?\.(?P<extension>.*)$'
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
        if self.process:
            path_list += [self.process]
        path_list += [f'sub-{self.sub}',
                      f'ses-{self.ses}']
        if self.data_type:
            path_list.append(self.data_type)
        elif not self.process:
            raise ValueError('BIDS schema requires a value for either data_type or process')

        filename = [f'sub-{self.sub}',
                    f'ses-{self.ses}']
        for key in ('task', 'acq', 'ce', 'rec', 'run', 'echo', 'part'):
            value = getattr(self, key, undefined)
            if value:
                filename.append(f'{key}-{value}')
        if self.suffix:
            filename.append(f'{self.suffix}.{self.extension}')
        else:
            filename[-1] += f'.{self.extension}'
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
        if 'data_type' not in kwargs and 'process' not in kwargs:
            layout = self.__class__(self.base_path, data_type='*', **kwargs)
        else:
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
    def __init_subclass__(cls, schema, process) -> None:
        from .application import get_node_class

        super().__init_subclass__()
        if isinstance(process, str):
            process = get_node_class(process)[1]
        if 'metadata_schemas' not in process.__dict__:
            process.metadata_schemas = {}
        schemas = process.metadata_schemas
        schemas[schema] = cls
        cls.schema = schema
        setattr(process, 'metadata_schemas', schemas)
    
    # @classmethod
    # def _update_metadata(cls, metadata, process, pipeline_name, parameter,
    #                      iteration_index):
    #     # remove top pipeline name
    #     if '.' in pipeline_name:
    #         pipeline_name = pipeline_name.split('.', 1)[-1]
    #         long_parmater = f'{pipeline_name}.{parameter}'
    #     else:
    #         pipeline_name = ''
    #         long_parmater = parameter
    #     stack = [v for p, v in getattr(cls, '_', {}).items()
    #              if fnmatch.fnmatch(long_parmater, p)] \
    #         + [
    #         #getattr(cls, f'{pipeline_name}.{parameter}', None),
    #         getattr(cls, parameter, None),
    #     ]
    #     instance_process_schema = getattr(process, 'metadata_schemas', None)
    #     if instance_process_schema:
    #         stack += [v
    #                   for p, v in getattr(instance_process_schema, '_',
    #                                       {}).items()
    #                   if fnmatch.fnmatch(long_parmater, p)]
    #         #stack.append(getattr(instance_process_schema, f'{pipeline_name}.{parameter}', None))
    #         stack.append(getattr(instance_process_schema, parameter, None))
        
    #     while stack:
    #         item = stack.pop(0)
    #         if item is None:
    #             continue
    #         elif isinstance(item, list):
    #             stack = item + stack
    #         elif isinstance(item, dict):
    #             for k, v in item.items():
    #                 if callable(v):
    #                     v = v(metadata=metadata, 
    #                           process=process,
    #                           parameter=parameter,
    #                           iteration_index=iteration_index)
    #                 setattr(metadata, k, v)
    #         else:
    #             stack.insert(0, item(
    #                 metadata=metadata, 
    #                 process=process,
    #                 parameter=parameter,
    #                 iteration_index=iteration_index))                
                

class MetadataModifier:
    def __init__(self, definition, process, parameter):
        self.process = process
        self.parameter = parameter
        self.apply_functions = []
        if isinstance(definition, dict):
            self.add_apply_function(definition.get(parameter))
            for pattern, pattern_modifier in definition.get('_', {}).items():
                if fnmatch.fnmatch(parameter, pattern):
                    self.add_apply_function(pattern_modifier)
        elif callable(definition):
            self.add_apply_function(definition)
        elif isinstance(definition, list):
            for i in definition:
                self.add_apply_function(i)
        elif definition is not None:
            raise ValueError(f'Invalid value for schema modification for parameter {parameter}: {definition}')

    @property
    def is_empty(self):
        return bool(self.apply_functions)
    
    def add_apply_function(self, modifier):
        if modifier is None:
            return
        if isinstance(modifier, dict):
            modifier = functools.partial(self.apply_dict, modifier_dict=modifier)
        elif not callable(modifier):
            raise ValueError(f'Invalid value for schema modification for parameter {self.parameter}: {modifier}')
        self.apply_functions.append(modifier)
        
    @staticmethod
    def apply_dict(metadata, process, parameter, modifier_dict):
        for k, v in modifier_dict.items():
            setattr(metadata, k, v)

    @staticmethod
    def prepend(key, value, sep='_'):
        def prepend(metadata, process, parameter,
                    key=key, value=value,sep=sep):
            current_value = getattr(metadata, key, '')
            setattr(metadata, key, value + (sep + current_value if current_value else ''))
        return prepend

    @staticmethod
    def append(key, value, sep='_'):
        def append(metadata, process, parameter,
                   key=key, value=value,sep=sep):
            current_value = getattr(metadata, key, '')
            setattr(metadata, key, (current_value + sep if current_value else '') + value)
        return append

    def apply(self, metadata, process, parameter):
        for function in self.apply_functions:
            f(metadata, process, parameter)


def dprint(debug, *args, _frame_depth=1, **kwargs):
    if debug:
        import inspect
        frame = inspect.stack(context=0)[_frame_depth]
        try:
            head = f'!{frame.function}:{frame.lineno}!'
        finally:
            del frame
        print(head, ' '.join(f'{i}' for i in args), **kwargs)


def dpprint(debug, item):
    if debug:
        from pprint import pprint
        dprint(debug=debug, _frame_depth=2)
        pprint(item)


class ProcessMetadata(Controller):
    parameters_per_schema : dict[str, list[str]]
    dataset_per_parameter : dict

    def __init__(self, executable, execution_context, datasets=None):
        super().__init__()
        self.executable = executable
        self.execution_context = execution_context
        self.datasets = datasets

        self.parameters_per_schema = {}
        self.schema_per_parameter = {}
        self.dataset_per_parameter = {}
        self.iterative_schemas = set()
        if isinstance(executable, ProcessIteration):
            process = executable.process
            iterative_parameters = executable.iterative_parameters
        else:
            iterative_parameters = set()
            process = executable

        # Associate each field to a dataset
        for field in process.user_fields():
            dataset_name = self.parameter_dataset_name(executable, field)
            if dataset_name is None:
                # no completion for this field
                continue
            dataset = getattr(execution_context.dataset, dataset_name, None)
            if dataset:
                self.dataset_per_parameter[field.name] = dataset_name
                schema = dataset.metadata_schema
                self.parameters_per_schema.setdefault(schema, []).append(field.name)
                self.schema_per_parameter[field.name] = schema
                if field.name in iterative_parameters:
                    self.iterative_schemas.add(schema)
        
        for schema_name in self.parameters_per_schema:
            schema_cls = Dataset.find_schema(schema_name)
            if schema_cls is None:
                raise ValueError(f'Cannot find metadata schema named "{schema_name}"')
            if schema_name in self.iterative_schemas:
                self.add_field(schema_name, type_=list[schema_cls])
                setattr(self, schema_name, [])
            else:
                self.add_field(schema_name, type_=schema_cls)
                setattr(self, schema_name, schema_cls())

    def generate_paths(self, executable, debug=False):
        if isinstance(executable, ProcessIteration):
            ...
        else:
            ...

    def parameter_dataset_name(self, process, field):
        '''
        Find the name of the dataset associated to a process parameter
        '''
        inner_field = None
        inner_field_name = None
        if isinstance(process, Pipeline):
            inner_item = next(process.get_linked_items(
                                process, field.name), None)
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
            if dataset_name is None and self.datasets:
                dataset_name = self.datasets.get(field.name)
            # fallback 3: use "input" or "output"
            if dataset_name is None and (not self.datasets
                                        or field.name not in self.datasets):
                dataset_name = ('output' if field.is_output() else 'input')
            return dataset_name
        return None
    
    def metadata_modifications(self, process):
        result = {}
        if isinstance(process, ProcessIteration):
            for iprocess in process.iterate_over_process_parmeters():
                iresult = self.metadata_modifications(iprocess.process)
                for k, v in iresult.items():
                    if k in process.iterative_parameters:
                        result.setdefault(k, []).append(v)
                    else:
                        result[k] = v
        else:
            for field in process.user_fields():
                dprint(True, field.name)
                if process.plugs[field.name].activated:
                    schema = self.schema_per_parameter.get(field.name)
                    if schema:
                        dprint(True, schema)
                        todo = []
                        done = set()
                        if isinstance(process, Pipeline):
                            stack = list(process.get_linked_items(process, field.name,))
                            while stack:
                                node, node_parameter = stack.pop(0)
                                todo.append((node, node_parameter))
                                done.add((node, node_parameter))
                                if field.is_output():
                                    for node_field in node.user_fields():
                                        if node.plugs[node_field.name].activated and not node_field.is_output():
                                            stack.extend(i for i in 
                                                process.get_linked_items(node, 
                                                                         node_parameter)
                                                if i not in done)
                        todo.append((process, field.name))
                        for node, node_parameter in todo:
                            dpprint(True, f'{node.definition} {node_parameter}')
                            process_metadata_schema = getattr(node, 'metadata_schemas', {}).get(schema)
                            dprint(True, process_metadata_schema)
                            modifier = MetadataModifier(process_metadata_schema, node, node_parameter)
                            dprint(True, modifier)
                            if not modifier.is_empty:
                                dprint(True, modifier.apply_functions)
                                result.setdefault(field.name, []).append(modifier)
        return result
    

    def generate_paths(self, executable, debug=True):
        dprint(debug, executable.definition)
        if isinstance(executable, ProcessIteration):
            iteration_size = 0
            for schema in self.iterative_schemas:
                schema_iteration_size = len(getattr(self, schema))
                if schema_iteration_size:
                    if iteration_size == 0:
                        iteration_size = schema_iteration_size
                        first_schema = schema
                    elif iteration_size != schema_iteration_size:
                        raise ValueError(f'Iteration on schema {first_schema} has {iteration_size} element(s) which is not equal to schema {schema} ({schema_iteration_size} element(s))')
            iteration_values = {}
            dprint(debug, f'{iteration_size}')
            for iteration in range(iteration_size):
                metadatas = {}
                for i in self.parameters_per_schema:
                    if i in self.iterative_schemas:
                        metadata_list = getattr(self, i)
                        if metadata_list:
                            metadatas[i] = metadata_list[iteration]
                        else:
                            metadatas[i] = Dataset.find_schema(i)()
                    else:
                        metadatas[i] = getattr(self, i)
                self._generate_paths(executable=executable, metadatas=metadatas, iteration_index=iteration, debug=debug)
                for i in executable.iterative_parameters:
                    if executable.field(i).path_type:
                        value = getattr(executable.process, i, undefined)
                        iteration_values.setdefault(i, []).append(value)
            dpprint(debug, iteration_values)
            for k, v in iteration_values.items():
                setattr(executable, k, v)
        else:
            metadata_modifications = self.metadata_modifications(executable)
            dprint(debug, metadata_modifications)
            for schema, parameters in self.parameters_per_schema.items():
                for parameter in parameters:
                    dataset = self.dataset_per_parameter[parameter]
                    metadata = Dataset.find_schema(schema)(base_path=f'!{{dataset.{dataset}.path}}')
                    metadata.import_dict(getattr(self, schema).asdict())
                    for modifier in metadata_modifications.get(parameter, []):
                        modifier.apply(metadata, executable, parameter)
                    try:
                        path = str(metadata.build_path())   
                    except:
                        raise
                        path = undefined
                    setattr(executable, parameter, path)

    # def _generate_paths(self, executable, metadatas, iteration_index, debug):
    #     dprint(debug, executable.definition, f'{iteration_index}')
    #     for schema, parameters in self.parameters_per_schema.items():
    #         for parameter in parameters:
    #             dataset = self.dataset_per_parameter[parameter]
    #             metadata = Dataset.find_schema(schema)(base_path=f'!{{dataset.{dataset}.path}}')
    #             for other_schema in self.parameters_per_schema:
    #                 if other_schema == schema:
    #                     continue
    #                 mapping_class = Dataset.find_schema_mapping(other_schema, schema)
    #                 if not mapping_class:
    #                     continue
    #                 mapping_class.map_schemas(metadatas[other_schema], metadata)
    #             schema_metadata = metadatas[schema]
    #             for field in schema_metadata.fields():
    #                 value = getattr(schema_metadata, field.name, None)
    #                 if value is not None:
    #                     #value = value % metadata.asdict()
    #                     setattr(metadata, field.name, value)
    #             dprint(debug, '->', parameter, ':', schema)
    #             for path in self.follow_links(executable, parameter, debug=True):
    #                 dprint(debug, 'path length', len(path))
    #                 # get all pattern rules along the path
    #                 path_schemas = []
    #                 for pipeline_name, process, process_parameter in path:
    #                     metadata_schema = getattr(process, 'metadata_schemas',
    #                                               {}).get(schema)
    #                     path_schemas.append(metadata_schema)
    #                     if isinstance(process, ProcessIteration):
    #                         metadata_schema = getattr(
    #                             process.process, 'metadata_schemas',
    #                             {}).get(schema)
    #                         path_schemas.append(metadata_schema)

    #                 # merge attributes
    #                 level = len(path_schemas) - 1
    #                 for pipeline_name, process, process_parameter in reversed(path):
    #                     dprint(debug, 
    #                            'pname:', pipeline_name, 
    #                            ', def:', process.definition, 
    #                            ', par:', process_parameter,
    #                            ', lev:', level)
    #                     if isinstance(process, ProcessIteration):
    #                         metadata_schema = path_schemas[level]
    #                         if metadata_schema:
    #                             dprint(debug, 'iter meta_schema:', metadata_schema, level, iteration_index)
    #                             metadata_schema._update_metadata(
    #                                 metadata, process, process.process.name,
    #                                 process_parameter, iteration_index)
    #                         level -= 1
    #                     metadata_schema = path_schemas[level]
    #                     if metadata_schema:
    #                         metadata_schema._update_metadata(
    #                             metadata, process, pipeline_name,
    #                             process_parameter, iteration_index)
    #                     level -= 1
    #                     # we must also call all parent pipelines schemas with
    #                     # the current depth parameter name, since some upper-
    #                     # level schemas may use them witht a lower-level name
    #                     # (especially for pattern rules such as
    #                     # "LeftPipeline.*'
    #                     for ilevel in range(level, -1, -1):
    #                         metadata_schema = path_schemas[level]
    #                         if metadata_schema:
    #                             metadata_schema._update_metadata(
    #                                 metadata, process, pipeline_name,
    #                                 process_parameter, iteration_index)
    #             dpprint(debug, metadata.asdict())
    #             path = str(metadata.build_path()) % metadata.asdict()
    #             dprint(debug, parameter, '=', path)
    #             if isinstance(executable, ProcessIteration):
    #                 setattr(executable.process, parameter, path)
    #             else:
    #                 setattr(executable, parameter, path)

    # @staticmethod        
    # def follow_links(executable, parameter_name, debug=False):
    #     dprint(debug, executable.definition, parameter_name)
    #     main_field = executable.field(parameter_name)
    #     if main_field.is_output():
    #         direction = 'links_from'
    #     else:
    #         direction = 'links_to'
    #     stack = [([], executable, main_field.name, [])]
    #     done = set()
    #     while stack:
    #         node_name_path, node, field_name, path = stack.pop(0)
    #         dprint(debug, 'p:', node_name_path, ', node:', node.name, ', field:', field_name, '...')
    #         field = node.field(field_name)
    #         if node in done or not node.activated:
    #             continue
    #         done.add(node)
    #         plug = node.plugs.get(field.name)
    #         followers = []
    #         if isinstance(node, Switch):
    #             if field.name != 'switch':
    #                 for input_plug_name, output_plug_name in node.connections():
    #                     dprint(debug, 'switch', field_name, input_plug_name, output_plug_name, not main_field.is_output())
    #                     if not main_field.is_output():
    #                         if field_name == input_plug_name:
    #                             dprint(debug, 'append')
    #                             next_node, next_plug = next(executable.get_linked_items(
    #                                 node, output_plug_name))
    #                             stack.append((node_name_path, next_node, next_plug, path))
    #                     else:
    #                         if field_name == output_plug_name:
    #                             dprint(debug, 'append')
    #                             next_node, next_plug = next(executable.get_linked_items(
    #                                 node, input_plug_name))
    #                             stack.append((node_name_path, next_node, next_plug, path))
    #         elif isinstance(node, Process):
    #             path.append(('.'.join(node_name_path + [node.name]), node, field.name))
    #             if isinstance(node, Pipeline):
    #                 node_name = node.name
    #             else:
    #                 node_name = None
    #             for dest_plug_name, dest_node in (i[1:3] for i in getattr(plug, direction)):
    #                 if dest_node in done or not dest_node.activated:
    #                     continue
    #                 followers.append((node_name, dest_node, dest_plug_name))
    #             #if isinstance(node, ProcessIteration):
    #                 #followers.append((node.process.name, node.process, field.name))
    #         if followers:
    #             for next_node_name, next_node, next_plug in followers:
    #                 if next_node_name:
    #                     next_node_name_path = node_name_path + [next_node_name]
    #                 else:
    #                     next_node_name_path = node_name_path
    #                 stack.append((next_node_name_path, next_node, next_plug, path))
    #         else:
    #             dprint(debug, 'yield', path)
    #             yield path
