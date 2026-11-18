# -*- coding: utf-8 -*-

from capsul.engine import capsul_engine
import time
import traits.api as traits
import datetime
import os.path as osp


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

    def __init__(self, database, engine=None, fom=None, data_types=None,
                 data_filters=None):
        self.data_parameters = ['database', 'data_types', 'fom',
                                'data_filters']
        self.database = database
        self.fom = fom
        self.engine = engine
        self.data_types = data_types
        self.data_filters = data_filters
        self.status_for_type = {}

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
        raise NotImplementedError(
            'DataSelector is a pure virtual class. Please use one of its '
            'derived classes, or more conveniently, get_data_selector().')

    def file_status(self, filename, data_type):
        if filename is None:
            return self.statuses.ABSENT
        stat_func = self.status_for_type.get(data_type)
        if stat_func is not None:
            return stat_func(self, filename)
        return self.statuses.PRESENT

    # specific to Morphologist JSON QC report files
    @staticmethod
    def get_qc_status(proc, path):
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


def get_data_selector(database, engine=None, fom=None, data_types=None,
                      data_filters=None, database_sqlite=None,
                      type_labels=None, index_status=None):
    ''' Factory function to build a data selector corresponding to the given
    criterions. Mainly, if ``database_sqlite`` provides a SQLite filename, then
    a SQLite data selector will be returned.
    '''
    if database_sqlite is not None:
        from .sqlite_dataselector import SQLiteDataSelector
        return SQLiteDataSelector(
            database, engine=engine, fom=fom, data_types=data_types,
            data_filters=data_filters, database_sqlite=database_sqlite,
            type_labels=type_labels, index_status=index_status)

    from .data_parser import DataParser
    return DataParser(database, engine=engine, fom=fom, data_types=data_types,
                      data_filters=data_filters, type_labels=type_labels)
