# -*- coding: utf-8 -*-

from capsul.engine import capsul_engine
import time
import traits.api as traits
import datetime
import os
import os.path as osp
import re


class DataSelector:
    ''' Data selector, base class.
    The data selection mechanism allows to parse, store, query and filter data.
    The base class is abstract and should not be instantiated.

    Use :meth:`get_data_selector` instead to build the appropriate data
    selector.

    The use the :meth:`get_data` method to parse/query data.

    Ex::

        parser = get_data_selector(
            '/home/albert/dataset',
            database_sqlite='/home/albert/dataset/capsul-2.6.sqlite')
        data = parser.get_data(
            data_types=[
                'morphologist.capsul.morphologist.t1mri',
                'morphologist.capsul.morphologist.Report_report_json'],
            data_filters={'.*': {'center': 'subjects'},
                          'B': {'file_status': 'ok'}},
            type_labels=['A', 'B'])
    '''

    class statuses:
        ''' Status list as an enum '''
        UNDEFINED = -1
        OK = 0
        PRESENT = 1
        WARNING = 2
        SUSPICIOUS = 3
        BAD = 4
        ABSENT = 5
        # VALID_* for manually validated (marked OK)
        VALID_OK = 8
        VALID_PRESENT = 9
        VALID_WARNING = 10
        VALID_SUSPICIOUS = 11
        VALID_BAD = 12
        VALID_ABSENT = 13
        # INVALID_* for manually invalidated (marked bad)
        INVALID_OK = 16
        INVALID_PRESENT = 17
        INVALID_WARNING = 18
        INVALID_SUSPICIOUS = 19
        INVALID_BAD = 20
        INVALID_ABSENT = 21

    status_str = {
        statuses.UNDEFINED: 'undefined',
        statuses.OK: 'ok',
        statuses.PRESENT: 'present',
        statuses.WARNING: 'warning',
        statuses.SUSPICIOUS: 'suspicious',
        statuses.BAD: 'bad',
        statuses.ABSENT: 'absent',
        statuses.VALID_OK: 'valid_ok',
        statuses.VALID_PRESENT: 'valid_present',
        statuses.VALID_WARNING: 'valid_warning',
        statuses.VALID_SUSPICIOUS: 'valid_suspicious',
        statuses.VALID_BAD: 'valid_bad',
        statuses.VALID_ABSENT: 'valid_absent',
        statuses.INVALID_OK: 'invalid_ok',
        statuses.INVALID_PRESENT: 'invalid_present',
        statuses.INVALID_WARNING: 'invalid_warning',
        statuses.INVALID_SUSPICIOUS: 'invalid_suspicious',
        statuses.INVALID_BAD: 'invalid_bad',
        statuses.INVALID_ABSENT: 'invalid_absent',
    }
    ''' string identifiers for status enums '''

    def __init__(self, database, engine=None, fom=None, data_types=None,
                 data_filters=None, type_labels=None, status_for_type=None,
                 upstream_selector=None,
                 **kwargs):
        self.data_parameters = ['database', 'data_types', 'fom',
                                'data_filters', 'type_labels',
                                'upstream_selector']
        self.database = database
        self.fom = fom
        self.engine = engine
        self.data_types = data_types
        self.data_filters = data_filters
        self.type_labels = type_labels
        self.status_for_type = ({} if status_for_type is None
                                else status_for_type)
        self.upstream_selector = upstream_selector
        self.remaining_args = kwargs

    def set_parameters(self, **kwargs):
        for p in self.data_parameters:
            if p in kwargs:
                setattr(self, p, kwargs[p])

    def check_parameters(self):
        if self.data_types in (None, traits.Undefined):
            raise ValueError('data_types is required')
        if self.database in (None, traits.Undefined, ''):
            engine = self.get_engine()
            with engine.settings as session:
                config = session.config("fom", "global")
                self.database = config.input_directory
        if self.fom in (None, traits.Undefined, ''):
            engine = self.get_engine()
            with engine.settings as session:
                config = session.config("fom", "global")
                self.fom = config.input_fom
        if self.type_labels in (None, traits.Undefined):
            self.type_labels = self.data_types
        if isinstance(self.upstream_selector, dict):
            self.build_upstream_selector()

    def get_data(self, **kwargs):
        ''' The main method of the DataSelector class. Performs parsing /
        querying / filtering and returns data found.

        The keyword arguments allow to specify selection parameters. The base
        ones are listed here, but specialized selectors may support more
        parameters. Some of them may be given upon construction (see :func:`get_data_selector`), and might be overriden here.

        database: str
            database directory to query
        fom: str
            the FOM model to apply (ex: 'morphologist-bids-2.0', 'morphologist-auto-1.0', 'raw-bids-1.0'...)
        data_types: (mandatory), list of str
            each element is a process + parameter name in capsul which determines a data type to look for. Ex::

                ['morphologist.capsul.morphologist.t1mri',
                 'morphologist.capsul.morphologist.Report_report_json']

        data_filters: list, dict, or str
            if specified as str, will be evaluated as a python expression to
            form a list or a dict.
        type_labels: list
            assigns a label to each data type, to provide shorter names in
            data_filters.

        '''
        self.set_parameters(**kwargs)
        self.check_parameters()
        t0 = time.time()
        self.t0 = t0
        data = self.find_data()
        t1 = time.time()
        print('query/parse time:', datetime.timedelta(seconds=t1 - t0))

        return data

    def get_engine(self):
        if self.engine is not None:
            return self.engine
        self.engine = capsul_engine()
        self.engine.load_module("capsul.engine.module.fom")
        return self.engine

    def find_data(self):
        data = []
        profile = False
        if profile:
            print('find_data')
            t0 = time.time()

        data_filters = self.prepare_filters()

        for i, dtype in enumerate(self.data_types):
            items = list(self.find_items(dtype, data_filters[i],
                                         self.status_filters[i]))
            data.append((dtype, items))
            # print(dtype, ':', len(items), 'items')
            if profile:
                print('time:', time.time() - t0)

        return data

    def find_items(self, dfilt, sfilt):
        ''' This method needs to be overloaded in concrete classes.

        Its output is a generator, where each element is a dictionary, with 2
        entries:

        path: str
            full file path
        attributes: dict
            the attributes dictionaty for the file. It generally corresponds to
            the FOM attributes. In some special DataSelector subclasses like
            :class:`ExhaustiveDataSelector` or :class:`FilesListSelector` which
            are meant to be only data sources, the attributes dictionary may be
            missing.
        '''
        raise NotImplementedError(
            'DataSelector is an abstract class: you should use one of its '
            'derived classes, or better, use get_data_selector().')

    def prepare_filters(self):
        data_filters = [{} for i in range(len(self.data_types))]
        self.status_filters = [{} for i in range(len(self.data_types))]
        self.need_status = False
        if self.data_filters:
            if isinstance(self.data_filters, str):
                df = eval(self.data_filters)
            else:
                df = self.data_filters
            if isinstance(df, list):
                data_filters = df
            elif isinstance(df, dict):
                for k, v in df.items():
                    kr = re.compile(k)
                    cols = [i for i, c in enumerate(self.type_labels)
                            if kr.match(c)]
                    if len(cols) == 0:
                        raise ValueError(
                            f'data filer column "{k}" is not found')
                    sf = v.get('file_status')
                    if sf:
                        v = {x: y for x, y in v.items() if x != 'file_status'}
                        self.need_status = True
                    for i in cols:
                        data_filters[i].update(v)
                        if sf:
                            self.status_filters[i] = sf
            else:
                raise ValueError('data_filters is not recognized')

        if self.need_status:
            self.prepare_status_column()

        return data_filters

    def prepare_status_column(self):
        # in filesystem parsing mode: nothing to do
        pass

    def file_status(self, filename, data_type):
        if filename is None:
            return self.statuses.ABSENT
        stat_func = self.status_for_type.get(data_type)
        if stat_func is not None:
            return stat_func(self, filename)
        return self.statuses.PRESENT

    def build_upstream_selector(self):
        kwargs = dict(self.upstream_selector)
        for p in ('database', 'engine', 'data_types', 'fom', 'data_filters',
                  'type_labels'):
            if p not in kwargs:
                v = getattr(self, p)
                if v not in (None, traits.Undefined, ''):
                    kwargs[p] = v
        self.upstream_selector = get_data_selector(**kwargs)

    # specific to Morphologist JSON QC report files
    @staticmethod
    def get_qc_status(proc, path):
        ''' Get the QC status from a Morphologist JSON QC file.

        To be used in ``status_for_type`` mapping parameter.
        '''
        import json

        if not osp.exists(path):
            return proc.statuses.BAD
        with open(path) as f:
            report = json.load(f)
        stat = {
            'OK': proc.statuses.OK,
            'Warning': proc.statuses.WARNING,
            'Suspicious': proc.statuses.SUSPICIOUS,
            'Bad': proc.statuses.BAD,
        }
        status = report.get('status', 'Bad')
        return stat[status]


class ExhaustiveDataSelector(DataSelector):
    ''' This DataSelector walks the entire database directory tree and returns
    every file. Each element is a dict with one item: "path". No attributes.

    You normally use it as as data source (``upstream_selector``) for a
    :class:`~.data_parser.DataParser`
    '''

    def find_items(self, dtype, dfilt, sfilt):
        '''
        '''
        for p in os.walk(self.database):
            for f in p[2]:
                yield {'path': os.path.join(p[0], f)}


class FilesListSelector(DataSelector):
    ''' Iterates over a given files list. Each element is a dict with one item:
    "path". No attributes.

    You normally use it as as data source (``upstream_selector``) for a
    :class:`~.data_parser.DataParser`
    '''

    def __init__(self, database, files_list, **kwargs):
        super().__init__(database, **kwargs)
        self.files_list = files_list
        self.data_parameters.append('files_list')

    def find_items(self, dtype, dfilt, sfilt):
        '''
        '''
        for path in self.files_list:
            yield {'path': path}


class DictListSelector(DataSelector):
    ''' Iterates over a given list of files. Each element is a dict with the
    same shape as the :class:`.data_parser.DataParser` output.

    The ``dict_list`` may be a list of dicts, or a JSON filename.

    You normally use it either directly, or as as data source
    (``upstream_selector``) for a :class:`~.data_parser.DataFilter`
    '''

    def __init__(self, database, dict_list, **kwargs):
        super().__init__(database, **kwargs)
        self.dict_list = dict_list
        self.data_parameters.append('dict_list')

    def find_items(self, dtype, dfilt, sfilt):
        '''
        '''
        import json

        if isinstance(self.dict_list, str):
            with open(self.dict_list) as f:
                self.dict_list = json.load(f)
        dict_list = self.dict_list
        if isinstance(dict_list, dict):
            dict_list = dict_list.get(dtype, [])
        for path in dict_list:
            yield path


def get_data_selector(database, engine=None, fom=None, data_types=None,
                      data_filters=None, database_sqlite=None,
                      type_labels=None, status_for_type=None,
                      index_status=None, type=None, **kwargs):
    ''' Factory function to build a data selector corresponding to the given
    criterions. Mainly, if ``database_sqlite`` provides a SQLite filename, then
    a SQLite data selector will be returned.

    The ``type`` parameter allows to select the intended data selector. If
    omitted, the type will be eguesses from other parameters, if possible.

    Currently supported types are:

    sqlite:
        :class:`~.sqlite_dataselector.SQLiteDataSelector`
    files_list:
        :class:`FilesListSelector`
    dict_list:
        :class:`DictListSelector`
    exhaustive:
        :class:`ExhaustiveDataSelector`
    parser:
        :class:`~.data_parser.DataParser`
    filter:
        :class:`~.data_parser.DataFilter`

    The ``upstream_selector`` parameter can be used to build a chain of
    selectors: the value of this parameter is a dictionary defining the
    upstream selector in the chain, and it may also conain an
    upstream_selector, and so on.

    The status_for_type is a dictionary of {type: function}. Such functions
    will be called to evaluate the status of a file of the given type. For
    instance, you may use the :meth:`DataSelector.get_qc_status` function to
    read Morphologist QC status files and get a status code from them.

    Ex::

        sel = data_selector.get_data_selector(
            '/home/charles-axel/raw_data',
            fom='raw-bids-1.0',
            upstream_selector={'type': 'exhaustive'})
        data = list(sel.get_data(
            data_types=['morphologist.capsul.import_t1_mri.ImportT1Mri.input'],
            data_filters={'.*': {'subject': 'hericart'}}))
    '''
    if type is None:
        if database_sqlite is not None:
            type = 'sqlite'
        elif 'files_list' in kwargs:
            type = 'files_list'
        elif 'dict_list' in kwargs:
            type = 'dict_list'
        elif kwargs.get('exhaustive', False):
            type = 'exhaustive'
        else:
            type = 'parser'

    if type == 'sqlite':
        from .sqlite_dataselector import SQLiteDataSelector
        return SQLiteDataSelector(
            database, engine=engine, fom=fom, data_types=data_types,
            data_filters=data_filters, database_sqlite=database_sqlite,
            type_labels=type_labels, status_for_type=status_for_type,
            index_status=index_status, **kwargs)

    elif type == 'files_list':
        return FilesListSelector(database, **kwargs)

    elif type == 'dict_list':
        return DictListSelector(database, **kwargs)

    elif type == 'exhaustive':
        kwargs = {k: v for k, v in kwargs.items() if k != 'exhaustive'}
        return ExhaustiveDataSelector(database, engine=engine, **kwargs)

    elif type == 'filter':
        from .data_parser import DataFilter
        return DataFilter(database, engine=engine, fom=fom,
                          data_types=data_types,
                          data_filters=data_filters, type_labels=type_labels,
                          status_for_type=status_for_type,
                          **kwargs)

    from .data_parser import DataParser
    return DataParser(database, engine=engine, fom=fom, data_types=data_types,
                      data_filters=data_filters, type_labels=type_labels,
                      status_for_type=status_for_type,
                      **kwargs)
