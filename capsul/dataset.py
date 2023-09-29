# -*- coding: utf-8 -*-

'''
Metadata handling and attributes-based path generation system. In other words, this module is the completion system for Capsul processes and other executables.

The main function to be used contains most of the doc: see :func:`generate_paths`
'''

import csv
import fnmatch
import functools
import json
import operator
from pathlib import Path
import re
import sys
import importlib
import weakref

from capsul.pipeline.pipeline import Process, Pipeline
from capsul.pipeline.process_iteration import ProcessIteration

from soma.controller import Controller, Literal, Directory
from soma.undefined import undefined

global_debug = False


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
        self.on_attribute_change.add(self.schema_change_callback,
                                     'metadata_schema')
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
        schema = cls.schemas.get(metadata_schema)
        if schema is None:
            try:
                # try to import the schema from capsul.schemas
                importlib.import_module(f'capsul.schemas.{metadata_schema}')
            except ImportError:
                pass  # oh well...
            schema = cls.schemas.get(metadata_schema)
        return schema

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
        if base_path is not undefined and base_path is not None \
                and not isinstance(base_path, Path):
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

    def build_path(self, unused_meta=None):
        ''' Returns a list of path elements built from the current PathLayout
        fields values.

        This method calls :meth:`_path_listh` which should be implemented in
        subclasses.
        '''
        return functools.reduce(operator.truediv,
                                self._path_list(unused_meta=unused_meta),
                                self.base_path)

    def build_param(self, path_type=False, unused_meta=None):
        if path_type:
            return self.build_path(unused_meta=unused_meta)
        return '/'.join([str(p) for p in self._path_list(
                            unused_meta=unused_meta)
                         if p not in (None, undefined, '')])

    def _path_list(self, unused_meta=None):
        ''' Builds a path from metadata values in the fields of the current
        MetadataSchema fields. The returned path is a list of directories and
        ends with a filename. The resulting path is an
        ``os.path.join(path_list).``
        '''

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

    def _path_list(self, unused_meta=None):
        '''
        The path has the following pattern:
          sub-{sub}/ses-{ses}/{data_type}/sub-{sub}_ses-{ses}[_task-{task}][_acq-{acq}][_ce-{ce}][_rec-{rec}][_run-{run}][_echo-{echo}][_part-{part}]{modality}.{extension}
        '''
        path_list = [self.folder]
        if self.process and self.folder == 'derivative':
            path_list += [self.process]
        path_list += [f'sub-{self.sub}',
                      f'ses-{self.ses}']
        if self.data_type:
            path_list.append(self.data_type)
        elif not self.process:
            raise ValueError('BIDS schema requires a value for either '
                             'data_type or process')

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
        m = self.path_pattern.match(str(relative_path))
        extsuffix = ''
        if m:
            if m.groupdict().get('extension') == 'gz':
                m2 = self.path_pattern.match(str(relative_path)[:-3])
                if m2:
                    m = m2
                    extsuffix += '.gz'

            result.update((k, v) for k, v in m.groupdict().items()
                          if v is not None)
        folder = result.get('folder')
        sub = result.get('sub')
        extension = result.get('extension')
        if extsuffix:
            if extension:
                extension += extsuffix
            else:
                extension = 'gz'
            result['extension'] = extension
        if folder and sub:
            ses = result.get('ses')
            if ses:
                sessions_file = self.base_path / folder / f'sub-{sub}' \
                    / f'sub-{sub}_sessions.tsv'
                if sessions_file.exists():
                    sessions_data = self.tsv_to_dict(sessions_file)
                    session_metadata = sessions_data.get(f'ses-{ses}', {})
                    result.update(session_metadata)
                scans_file = self.base_path / folder / f'sub-{sub}' \
                    / f'ses-{ses}' / f'sub-{sub}_ses-{ses}_scans.tsv'
            else:
                scans_file = self.base_path / folder / f'sub-{sub}' \
                    / f'sub-{sub}_scans.tsv'
            if scans_file.exists():
                scans_data = self.tsv_to_dict(scans_file)
                scan_metadata = scans_data.get(
                    str(path.relative_to(scans_file.parent)), {})
                result.update(scan_metadata)
            extension = result.get('extension')
            if extension:
                json_path = path.parent / (path.name[:-len(extension)-1]
                                           + '.json')
            else:
                json_path = path.parent / (path.name + '.json')
            if json_path.exists():
                with open(json_path) as f:
                    result.update(json.load(f))

        return result

    def find(self, **kwargs):
        ''' Find path from existing files given fixed values for some
        parameters (using :func:`glob.glob` and filenames parsing)

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
    acquisition: str = 'default_acquisition'
    preprocessings: str = None
    longitudinal: list[str] = None
    seg_directory: str = None
    sulci_graph_version: str = '3.1'
    sulci_recognition_session: str = 'default_session'
    sulci_recognition_type: str = 'auto'
    prefix: str = None
    short_prefix: str = None
    suffix: str = None
    extension: str = None
    side: str = None
    sidebis: str = None  # when used as a sufffix
    subject_in_filename: bool = True

    find_attrs = re.compile(
        r'(?P<folder>[^-_/]*)/'
        r'sub-(?P<sub>[^-_/]*)/'
        r'ses-(?P<ses>[^-_/]*)/'
        r'(?P<data_type>[^/]*)/'
        r'sub-(?P=sub)_ses-(?P=ses)'
        r'(?:_task-(?P<task>[^-_/]*))?'
        r'_(?P<suffix>[^-_/]*)\.(?P<extension>.*)$'
    )

    def _path_list(self, unused_meta=None):
        '''
        The path has the following pattern:
        {center}/{subject}/[{modality}/][{process/][{acquisition}/][{preprocessings}/][{longitudinal}/][{analysis}/][seg_directory/][{sulci_graph_version}/[{sulci_recognition_session}]]/[side][{prefix}_][short_prefix]{subject}[_to_avg_{longitudinal}}[_{sidebis}{suffix}][.{extension}]
        '''

        if unused_meta is None:
            unused_meta = set()
        elif not isinstance(unused_meta, set):
            unused_meta = set(unused_meta)

        path_list = []
        for key in ('center', 'subject', 'modality', 'process', 'acquisition',
                    'preprocessings', 'longitudinal', 'analysis'):
            if key not in unused_meta:
                value = getattr(self, key, None)
                if value:
                    path_list.append(value)
        if 'seg_directory' not in unused_meta and self.seg_directory:
            path_list += self.seg_directory.split('/')
        if 'sulci_graph_version' not in unused_meta \
                and self.sulci_graph_version:
            path_list.append(self.sulci_graph_version)
            if 'sulci_recognition_session' not in unused_meta \
                    and self.sulci_recognition_session:
                path_list.append(self.sulci_recognition_session)
                if 'sulci_recognition_type' not in unused_meta \
                        and self.sulci_recognition_type:
                    path_list[-1] += f'_{self.sulci_recognition_type}'

        filename = []
        if 'side' not in unused_meta and self.side:
            filename.append(f'{self.side}')
        if 'prefix' not in unused_meta and self.prefix:
            filename.append(f'{self.prefix}_')
        if 'short_prefix' not in unused_meta and self.short_prefix:
            filename.append(f'{self.short_prefix}')
        if 'subject_in_filename' not in unused_meta \
                and self.subject_in_filename:
            filename.append(self.subject)
        if 'longitudinal' not in unused_meta and self.longitudinal:
            filename.append(f'_to_avg_{self.longitudinal}')
        if ('suffix' not in unused_meta and self.suffix) \
                or ('sidebis' not in unused_meta and self.sidebis):
            if filename:
                filename.append('_')
            if 'sidebis' not in unused_meta and self.sidebis:
                filename.append(f'{self.sidebis}')
            if 'sufffix' not in unused_meta and self.suffix:
                filename.append(f'{self.suffix}')
        if 'extension' not in unused_meta and self.extension:
            filename.append(f'.{self.extension}')
        path_list.append(''.join(filename))

        return path_list


class MorphologistBIDSSchema(BrainVISASchema):

    schema_name = 'morphologist_bids'

    folder: Literal['sourcedata', 'rawdata', 'derivative']
    subject_only: bool = False

    def _path_list(self, unused_meta=None):
        if unused_meta is None:
            unused_meta = set()
        if 'subject_only' not in unused_meta and  self.subject_only:
            return [self.subject]

        if unused_meta is None:
            unused_meta = set()
        path_list = super()._path_list(unused_meta=unused_meta)
        pre_path = [f'sub-{self.subject}', f'ses-{self.acquisition}', 'anat']
        if 'folder' not in unused_meta \
                and self.folder not in (undefined, None, ''):
            pre_path.insert(0, self.folder)
        return pre_path + path_list[2:]


class SchemaMapping:
    def __init_subclass__(cls) -> None:
        Dataset.schema_mappings[(cls.source_schema, cls.dest_schema)] = cls


class BidsToBrainVISA(SchemaMapping):
    source_schema = 'bids'
    dest_schema = 'brainvisa'

    @staticmethod
    def map_schemas(source, dest):
        if dest.center is undefined:
            dest.center = 'subjects'
        dest.subject = source.sub
        dest.acquisition = source.ses
        dest.extension = source.extension
        process = getattr(source, 'process', None)
        if process:
            dest.process = process


class BidsToMorphoBids(SchemaMapping):
    source_schema = 'bids'
    dest_schema = 'morphologist_bids'

    @staticmethod
    def map_schemas(source, dest):
        BidsToBrainVISA.map_schemas(source, dest)


class ProcessSchema:
    '''
    Schema definition for a given process.

    Needs to be subclassed as in, for instance::

        from capsul.pipeline.test.fake_morphologist.normalization_t1_spm12_reinit \\
            import normalization_t1_spm12_reinit

        class SPM12NormalizationBIDS(ProcessSchema,
                                     schema='bids',
                                     process=normalization_t1_spm12_reinit):
            output = {'part': 'normalized_spm12'}

    This assigns metadata to a process parameters. Here in the example, the
    parameter ``output`` of the process ``normalization_t1_spm12_reinit`` gets
    a metadata dict ``{'part': 'normalized_spm12'}``.

    The class does not need to be instantiated or registered anywhere: just its
    declaration registets it automatically. Thus just importing the subclass
    definition is enough.

    Metadata can be assigned by parameter name, in a variable corresponding to
    the parameter field::

        output = {'part': 'normalized_spm12'}

    or using wildcards. For this, a variable name cannot contain the character
    ``*`` for instance. So we are using the special class variable ``_``, which
    itself is a dict containing wildcard keys::

        _ = {
            '*': {'seg_directory': 'segmentation'},
            '*_graph': {'extension': 'arg'}
        }

    Moreover in a pipeline, sub-nodes may be assigned metadata. This can be
    given as a dict in the ``_nodes`` class variable::

        _nodes = {
            'LeftGreyWhiteClassification': {'*': {'side': 'L'}},
            'RightGreyWhiteClassification': {'*': {'side': 'R'}},
        }

    Another special class variable may contain metadata links between the
    process input and output parameters. This ``_meta_links`` variable is also
    a dict (2 levels dict actually), and contains the list of metadata which
    are propagated from a source parameter to a destination one inside the
    given process (for the fiven schema)::

        _meta_links = {
            'histo_analysis': {
                'histo': ['prefix', 'side'],
            }
        }

    in this example, the output parameter ``histo`` of the process will get its
    ``prefix`` and ``side`` metadata from the input parameter
    ``histo_analysis``.

    By default, all metadata are systematically passed from inputs to outputs,
    and merged in parameters order.

    It is also possible to use wildcards in source and destination parameter
    names, and the value may be an empty list (meaning that no metadata is
    copied from this source to this destination)::

    _meta_links = {
            'histo_analysis': {
                '*': [],
            }
        }
    '''

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


class MetadataModifier:
    def __init__(self, schema_name, process, parameter, filtered_meta=None):
        self.process = process
        self.parameter = parameter
        self.modifiers = []
        self.filtered_meta = filtered_meta

        process_schema = getattr(process, 'metadata_schemas',
                                 {}).get(schema_name)
        if process_schema:
            for pattern, modifier in getattr(process_schema, '_', {}).items():
                if fnmatch.fnmatch(parameter, pattern):
                    self.add_modifier(modifier)
            modifier = getattr(process_schema, parameter, None)
            self.add_modifier(modifier)
        pipeline = process.get_pipeline()
        if pipeline:
            pipeline_schema = getattr(pipeline, 'metadata_schemas',
                                      {}).get(schema_name)
            if pipeline_schema:
                nodes_schema = getattr(pipeline_schema, '_nodes', None)
                if nodes_schema:
                    # node_modifiers = nodes_schema.get(process.name)
                    for pattern, node_modifiers in nodes_schema.items():
                        if fnmatch.fnmatch(process.name, pattern):
                            for pattern, modifier in node_modifiers.items():
                                if fnmatch.fnmatch(parameter, pattern):
                                    self.add_modifier(modifier)

    def __repr__(self):
        return f'MetadataModifier({self.process.label}, {self.parameter}, {self.modifiers}, filtered_meta={self.filtered_meta})'

    @property
    def is_empty(self):
        return not self.modifiers

    def add_modifier(self, modifier):
        if modifier is None:
            return
        if isinstance(modifier, dict) or callable(modifier):
            self.modifiers.append(modifier)
        else:
            raise ValueError(f'Invalid value for schema modification for parameter {self.parameter}: {modifier}')

    def apply(self, metadata, process, parameter, initial_meta):
        debug = False  # (parameter == 'nobias')
        if debug: print('apply modifier to', parameter, ':', self, metadata, initial_meta)
        for modifier in self.modifiers:
            if isinstance(modifier, dict):
                for k, v in modifier.items():
                    if self.filtered_meta is not None \
                            and k not in self.filtered_meta \
                            and not any([fnmatch.fnmatch(k, fm)
                                         for fm in self.filtered_meta]):
                        continue
                    if callable(v):
                        if debug:
                            print('call modifier funciton for', k)
                            print(':', v(metadata=metadata, process=process,
                                  parameter=parameter, initial_meta=initial_meta))
                        setattr(metadata, k,
                                v(metadata=metadata, process=process,
                                  parameter=parameter,
                                  initial_meta=initial_meta))
                    else:
                        setattr(metadata, k, v)
            else:
                if debug: print('call modifier funciton')
                modifier(metadata, process, parameter,
                         initial_meta=initial_meta)


class Prepend:
    def __init__(self, key, value, sep='_'):
        self.key = key
        self.value = value
        self.sep = sep
    
    def __call__(self, metadata, process, parameter, initial_meta):
        current_value = getattr(metadata, self.key, '')
        setattr(metadata, self.key, self.value + (self.sep + current_value if current_value else ''))

    def __repr__(self):
        return f'Prepend({repr(self.key)}, {repr(self.value)}{("" if self.sep == "_" else ", sep=" + repr(self.sep))})'

class Append:
    def __init__(self, key, value, sep='_'):
        self.key = key
        self.value = value
        self.sep = sep
    
    def __call__(self, metadata, process, parameter, initial_meta):
        current_value = getattr(metadata, self.key, '')
        setattr(metadata, self.key, (current_value + self.sep if current_value else '') + self.value)

    def __repr__(self):
        return f'Append({repr(self.key)}, {repr(self.value)}{("" if self.sep == "_" else ", sep=" + repr(self.sep))})'


def dprint(debug, *args, _frame_depth=1, **kwargs):
    if debug:
        import inspect
        frame = inspect.stack(context=0)[_frame_depth]
        try:
            head = f'!{frame.function}:{frame.lineno}!'
        finally:
            del frame
        print(head, ' '.join(f'{i}' for i in args), file=sys.stderr, **kwargs)


def dpprint(debug, item):
    if debug:
        from pprint import pprint
        dprint(debug=debug, _frame_depth=2, file=sys.stderr)
        pprint(item)


class ProcessMetadata(Controller):

    def __init__(self, executable, execution_context, datasets=None,
                 debug=False):
        super().__init__()
        self.executable = weakref.ref(executable)
        self.execution_context = execution_context
        self.datasets = datasets
        self._current_iteration = None
        self.debug = debug

        self.parameters_per_schema = {}
        self.schema_per_parameter = {}
        self.dataset_per_parameter = {}
        self.iterative_schemas = set()
        self.executable().metadata = self

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
                self.parameters_per_schema.setdefault(schema, []).append(
                    field.name)
                self.schema_per_parameter[field.name] = schema
                if field.is_list() or field.name in iterative_parameters:
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

        if self.debug:
            self.dprint('Create ProcessMetadata for', self.executable().label)
            for field in process.user_fields():
                if field.path_type:
                    dataset = self.dataset_per_parameter.get(field.name)
                    schema = self.schema_per_parameter.get(field.name)
                    self.dprint(f'  {field.name} -> dataset={dataset}, schema={schema}')
            self.dprint('  Iterative schemas:', self.iterative_schemas)

    def dprint(self, *args, **kwargs):
        if isinstance(self.debug, bool) and self.debug:
            self.debug = sys.stderr
        if self.debug:
            print(*args, file=self.debug, **kwargs)

    def parameter_dataset_name(self, process, field):
        '''
        Find the name of the dataset associated to a process parameter
        '''
        dataset_name = None
        # 1: get manually given datasets
        if self.datasets and field.name in self.datasets:
            dataset_name = self.datasets[field.name]
            return dataset_name
        # Associates a Dataset name with the field
        if dataset_name is None:
            fmeta = field.metadata()
            if 'dataset' in fmeta:
                dataset_name = getattr(field, 'dataset', None)
                return dataset_name

        # not manually given: filter out non-path fields
        inner_field = None
        inner_field_name = None
        if isinstance(process, Pipeline):
            # inner_item = next(process.get_linked_items(
            #     process, field.name, direction=('links_from' if field.is_output() else 'links_to')), None)
            inner_item = next(process.get_linked_items(
                process, field.name, in_outer_pipelines=False),
                None)
        else:
            inner_item = None
        if inner_item is not None:
            inner_process, inner_field_name = inner_item
            path_type = inner_process.field(inner_field_name).path_type
        else:
            path_type = field.path_type
        if path_type:
            # fallback 1: get in inner_field (of an inner process)
            if inner_field:
                dataset_name = getattr(inner_field, 'dataset', None)
            # fallback 3: use "input" or "output"
            if dataset_name is None and (not self.datasets
                                         or field.name not in self.datasets):
                dataset_name = ('output' if field.is_output() else 'input')
            return dataset_name
        return None

    def meta_nodes_state_hash(self, process):
        kdict = {'proc': process.full_name}
        for pname, plug in process.plugs.items():
            kdict[f'plug:{pname}'] = plug.activated
        if isinstance(process, Pipeline):
            for node in process.all_nodes():
                kdict[f'node:{node.full_name}'] = node.activated
        return hash(frozenset(kdict.items()))

    def metadata_modifications(self, process):
        ''' Modifications are propagated recursively from inputs. All input
        parameters bring their metadata modifications to the whole process (and
        thus to all its outputs).

        This is a bit overkill since outputs get metatata from all indirect
        outputs, some of them being very specific (like the format extension of
        a particular upstream process output parameter, which, then, will
        propagate to all downstream outputs). Moreover we don't always
        completely know the ordering of parameters, which has a large
        ifluence here since possibly contradicting metadata are applied in
        (recursive) parameters order. For instance 'prefix' or 'suffix' are set
        differently at many places earlier.
        '''

        result = {}
        if isinstance(process, ProcessIteration):
            for iprocess in process.iterate_over_process_parmeters():
                iresult = self.metadata_modifications(iprocess)
                for k, v in iresult.items():
                    if k in process.iterative_parameters:
                        result.setdefault(k, []).append(v)
                    else:
                        result[k] = v
        else:
            cache_key = self.meta_nodes_state_hash(process)
            cached = getattr(self, '_meta_modif_cache', {}).get(cache_key)
            if cached is not None:
                return cached

            for field in process.user_fields():
                # self.debug = (field.name == 't1mri_nobias')
                done_mod = set()
                if process.plugs[field.name].activated:
                    self.dprint(
                        f'  Parse schema modifications for {field.name}')
                    schema = self.schema_per_parameter.get(field.name)
                    if schema:
                        todo = []
                        done = set()
                        if isinstance(process, Pipeline):
                            # stack of (linked_node, linked_param,
                            # intra_link_node, intra_link_param_input,
                            # intra_link_param_output)
                            stack = [(l[0], l[1], None, None, None)
                                     for l in process.get_linked_items(
                                         process, field.name,
                                         in_outer_pipelines=True)]
                            while stack:
                                node, node_parameter, intra_node, intra_src, \
                                    intra_dst = stack.pop(0)
                                self.dprint(
                                    '    connected to '
                                    f'{node.full_name}.{node_parameter}')
                                todo.insert(
                                    0, (node, node_parameter, intra_node,
                                        intra_src, intra_dst))
                                done.add(node)
                                if field.is_output():
                                    for node_field in node.user_fields():
                                        if node.plugs[
                                                node_field.name].activated \
                                                and not node_field.is_output():
                                            ext = [(i[0], i[1], node,
                                                    node_field.name,
                                                    node_parameter)
                                                   for i in
                                                   process.get_linked_items(
                                                       node,
                                                       node_field.name,
                                                       process_only=False,
                                                       direction='links_from')
                                                  if isinstance(i[0], Process) and i[0] not in done]
                                            stack.extend(ext)
                                            done.update(i[0] for i in ext)
                                            if self.debug:
                                                for n, p, ni, s, d in ext:
                                                    self.dprint(f'        + {n.full_name}.{p}, {ni} {s} {d}')
                        todo.append((process, field.name, None, None, None))
                        for node, node_parameter, intra_node, intra_src, \
                                intra_dst in todo:
                            if self.debug:
                                inname = (intra_node.full_name
                                          if intra_node is not None
                                          else None)
                                self.dprint(
                                    f'    resolve {node.name}.'
                                    f'{node_parameter} '
                                    f'{inname} {intra_src} {intra_dst}')
                            filtered_meta = None
                            if intra_node is not None:
                                filtered_meta = self.get_linked_metadata(
                                    schema, intra_node, intra_src, intra_dst)
                            if (node, node_parameter) not in done_mod:
                                # (avoid having several times the same modifier
                                # via different paths, some Prepend(), Append()
                                # may be duplicate)
                                modifier = MetadataModifier(
                                    schema, node, node_parameter,
                                    filtered_meta=filtered_meta)
                                if not modifier.is_empty:
                                    self.dprint(f'        {modifier.modifiers}')
                                    if filtered_meta is not None:
                                        self.dprint(
                                            '        filtered_meta: '
                                            f'{filtered_meta}')
                                    result.setdefault(field.name,
                                                    []).append(modifier)
                            done_mod.add((node, node_parameter))
                else:
                    self.dprint(f'  {field.name} ignored (inactive)')

        # cache the result
        self._meta_modif_cache = getattr(self, '_meta_modif_cache', {})
        self._meta_modif_cache[cache_key] = result

        return result

    def get_linked_metadata(self, schema_name, node, src, dst):
        ''' Returns the list of "linked" metadata between parameters src and
        dst in node node for the given schema.

        Such links are described in ProcessSchema.
        '''

        process_schema = getattr(node, 'metadata_schemas',
                                 {}).get(schema_name)
        filt_meta = None
        if process_schema:
            for spattern, dfilt in getattr(process_schema, '_meta_links',
                                           {}).items():
                if fnmatch.fnmatch(src, spattern):
                    for dpattern, filt in dfilt.items():
                        if fnmatch.fnmatch(dst, dpattern):
                            if filt_meta is None:
                                filt_meta = filt
                            else:
                                filt_meta += filt

        # now look in pipeline schema _nodes definitions
        full_node_name = node.full_name
        executable = self.executable()
        if isinstance(executable, ProcessIteration):
            executable = executable.process
        pipeline_schema = getattr(executable, 'metadata_schemas',
                                  {}).get(schema_name)
        if pipeline_schema:
            nodes = getattr(pipeline_schema, '_nodes', {})
            for npattern, ndef in nodes.items():
                if fnmatch.fnmatch(full_node_name, npattern):
                    meta_links = ndef.get('_meta_links', {})
                    #if meta_links:
                        #print('node schema:', npattern, 'matches', full_node_name)
                        #print('has meta_links:', meta_links)
                    for spattern, dfilt in meta_links.items():
                        if fnmatch.fnmatch(src, spattern):
                            for dpattern, filt in dfilt.items():
                                if fnmatch.fnmatch(dst, dpattern):
                                    #print('filt:', filt)
                                    if filt_meta is None:
                                        filt_meta = filt
                                    else:
                                        filt_meta += filt

        #if filt_meta is not None:
            #print('filt_meta for', schema_name, node.name, src, dst, ':', filt_meta)
        return filt_meta

    def get_schema(self, schema_name, index=None):
        schema = getattr(self, schema_name)
        if isinstance(schema, list):
            if schema:
                if index is not None:
                    schema = schema[index]
                else:
                    schema = schema[self._current_iteration]
            else:
                schema = None
        return schema

    def generate_paths(self, executable=None):
        '''
        Generate all paths for parameters of the given executable. Completion
        rules will apply using the current values of the metadata.
        '''
        # self.debug = True
        if executable is None:
            executable = self.executable()

        if self.debug:
            if self._current_iteration is not None:
                iteration = f'[{self._current_iteration}]'
            else:
                iteration = ''
            self.dprint(f'Generate paths for {executable.name}{iteration}')
            for field in executable.user_fields():
                value = getattr(executable, field.name, undefined)
                self.dprint('       ', field.name, '=', repr(value))

        if isinstance(executable, ProcessIteration):
            empty_iterative_schema = set()
            iteration_size = 0
            for schema in self.iterative_schemas:
                schema_iteration_size = len(getattr(self, schema))
                if schema_iteration_size:
                    if iteration_size == 0:
                        iteration_size = schema_iteration_size
                        first_schema = schema
                    elif iteration_size != schema_iteration_size:
                        raise ValueError(f'Iteration on schema {first_schema} has {iteration_size} element(s) which is not equal to schema {schema} ({schema_iteration_size} element(s))')
                else:
                    empty_iterative_schema.add(schema)

            for schema in empty_iterative_schema:
                setattr(self, schema, [Dataset.find_schema(schema)() for i in range(iteration_size)])

            iteration_values = {}
            for iteration in range(iteration_size):
                self._current_iteration = iteration
                executable.select_iteration_index(iteration)
                self.generate_paths(executable.process)
                for i in executable.iterative_parameters:
                    # if executable.field(i).path_type:
                    value = getattr(executable.process, i, undefined)
                    iteration_values.setdefault(i, []).append(value)
            for k, v in iteration_values.items():
                setattr(executable, k, v)
        else:
            for schema_name in self.parameters_per_schema:
                for other_schema_name in self.parameters_per_schema:
                    if other_schema_name == schema_name:
                        continue
                    source = self.get_schema(schema_name)
                    dest = self.get_schema(other_schema_name)
                    if source and dest:
                        mapping = Dataset.find_schema_mapping(schema_name, other_schema_name)
                        if mapping:
                            mapping.map_schemas(source, dest)
            if self.debug:
                for field in self.fields():
                    self.dprint('  Metadata for', field.name)
                    metadata = self.get_schema(field.name)
                    for f in metadata.fields():
                        v = getattr(metadata, f.name, undefined)
                        self.dprint('   ', f.name, '=', repr(v))
            metadata_modifications = self.metadata_modifications(executable)
            for schema, parameters in self.parameters_per_schema.items():
                proc_meta = executable.metadata_schemas.get(schema)
                params_meta = {}
                if proc_meta is not None:
                    params_meta = getattr(proc_meta, 'metadata_per_parameter',
                                          {})

                for parameter in parameters:
                    self.dprint(f'  find value for {parameter} in schema {schema}')
                    dataset = self.dataset_per_parameter[parameter]
                    metadata = Dataset.find_schema(schema)(
                        base_path=f'!{{dataset.{dataset}.path}}')
                    s = self.get_schema(schema)
                    if s:
                        metadata.import_dict(s.asdict())
                    for modifier in metadata_modifications.get(parameter, []):
                        modifier.apply(metadata, executable, parameter, s)

                    unused_meta = set()
                    for pattern, v in params_meta.items():
                        if fnmatch.fnmatch(parameter, pattern):
                            unused = v.get('unused')
                            if unused is None:
                                used = v.get('used')
                                if used is not None:
                                    unused = [
                                        f.name for f in metadata.fields()
                                        if f.name not in used]
                            if unused is not None:
                                unused_meta = unused

                    try:
                        path = str(metadata.build_param(
                            executable.field(parameter).path_type,
                            unused_meta=unused_meta))
                    except Exception:
                        path = undefined
                    if self.debug:
                        for field in metadata.fields():
                            value = getattr(metadata, field.name, undefined)
                            self.dprint(f'    {field.name} = {repr(value)}')
                        self.dprint(f'    => {path}')
                    setattr(executable, parameter, path)

    def path_for_parameter(self, executable, parameter):
        '''
        Generates a path (or value) for a given parameter.
        This is a restricted version of generate_paths(), which does not assign
        the generated value to the executable parameter but just returns it.
        '''
        # TODO: factorize some code with generate_paths()
        if executable is None:
            executable = self.executable()

        if isinstance(executable, ProcessIteration):
            empty_iterative_schema = set()
            iteration_size = 0
            for schema in self.iterative_schemas:
                schema_iteration_size = len(getattr(self, schema))
                if schema_iteration_size:
                    if iteration_size == 0:
                        iteration_size = schema_iteration_size
                        first_schema = schema
                    elif iteration_size != schema_iteration_size:
                        raise ValueError(f'Iteration on schema {first_schema} has {iteration_size} element(s) which is not equal to schema {schema} ({schema_iteration_size} element(s))')
                else:
                    empty_iterative_schema.add(schema)

            for schema in empty_iterative_schema:
                setattr(self, schema, [Dataset.find_schema(schema)() for i in range(iteration_size)])

            if parameter in executable.iterative_parameters:
                paths = []
                for iteration in range(iteration_size):
                    self._current_iteration = iteration
                    executable.select_iteration_index(iteration)
                    path = self.parh_for_parameter(executable.process,
                                                   parameter)
                    paths.append(path)
                    return paths
            else:
                path = self.parh_for_parameter(executable.process, parameter)
                return path
        else:
            for schema_name in self.parameters_per_schema:
                for other_schema_name in self.parameters_per_schema:
                    if other_schema_name == schema_name:
                        continue
                    source = self.get_schema(schema_name)
                    dest = self.get_schema(other_schema_name)
                    if source and dest:
                        mapping = Dataset.find_schema_mapping(
                            schema_name, other_schema_name)
                        if mapping:
                            mapping.map_schemas(source, dest)
            metadata_modifications = self.metadata_modifications(executable)
            for schema, parameters in self.parameters_per_schema.items():
                if parameter not in parameters:
                    continue
                proc_meta = executable.metadata_schemas.get(schema)
                params_meta = {}
                if proc_meta is not None:
                    params_meta = getattr(proc_meta, 'metadata_per_parameter',
                                          {})

                dataset = self.dataset_per_parameter[parameter]
                metadata = Dataset.find_schema(schema)(
                    base_path=f'!{{dataset.{dataset}.path}}')
                s = self.get_schema(schema)
                if s:
                    metadata.import_dict(s.asdict())
                for modifier in metadata_modifications.get(parameter, []):
                    modifier.apply(metadata, executable, parameter, s)

                unused_meta = set()
                for pattern, v in params_meta.items():
                    if fnmatch.fnmatch(parameter, pattern):
                        unused = v.get('unused')
                        if unused is None:
                            used = v.get('used')
                            if used is not None:
                                unused = [
                                    f.name for f in metadata.fields()
                                    if f.name not in used]
                        if unused is not None:
                            unused_meta = unused

                try:
                    path = str(metadata.build_param(
                        executable.field(parameter).path_type,
                        unused_meta=unused_meta))
                except Exception:
                    path = undefined

                return path
