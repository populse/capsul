# -*- coding: utf-8 -*-

from .data_parser import DataParser
import traits.api as traits
import capsul.info as cinfo
from capsul.api import Pipeline, Process
import sqlite3
import os.path as osp
import time


class SQLiteDataSelector(DataParser):

    IndexStatus = {
        'Use',
        'Force',
        'Set_if_absent'
    }

    def __init__(self, database, **kwargs):
        super().__init__(database, **kwargs)
        self.database_sqlite = kwargs.get('database_sqlite')
        self.index_status = kwargs.get('index_status')
        self.db = None
        self.data_parameters.append('database_sqlite')
        self.data_parameters.append('index_status')

    def check_parameters(self):
        init_fom = self.fom
        super().check_parameters()
        if self.database_sqlite in (None, traits.Undefined, ''):
            self.database_sqlite = osp.join(
                self.database,
                'capsul-{cinfo.version_major}.{cinfo.version_minor}.sqlite')
        self.db = sqlite3.connect(self.database_sqlite)
        if init_fom in (None, traits.Undefined, '') and self.db is not None:
            self.fom = list(self.db.execute('SELECT fom_name FROM fom'))[0][0]
        if self.index_status in (None, traits.Undefined, ''):
            self.index_status = 'Set_if_absent'
        elif self.index_status not in self.IndexStatus:
            raise ValueError(
                'index_status "{self.index_status}" not in allowed values: '
                f'{self.IndexStatus}')

    def find_items(self, dtype, dfilt, sfilt):
        '''
        '''
        profile = False
        if profile:
            t0 = time.time()

        proc, procname, param = self.get_process(dtype, dfilt)

        data = []
        cols = [x[1] for x in self.db.execute('PRAGMA table_info(files)')]
        keys = ', '.join(cols)
        names = self.proc_param_names(proc, procname, param)
        for procname, param, att in names:
            dfilt2 = dict(dfilt)
            incompatible = False
            for k, v in att.items():
                if k in dfilt2 and dfilt2[k] != v:
                    incompatible = True
                    break
                dfilt2[k] = v
            if incompatible:
                continue
            where = ' AND '.join(f'({k} == "{v}" OR {k} IS NULL)'
                                 for k, v in dfilt2.items())
            where2 = [f'fom_process = "{procname}"',
                      f'fom_parameter = "{param}"']
            if where != '':
                where2.insert(0, where)
            sql = f'SELECT {keys} FROM files WHERE ' + ' AND '.join(where2)
            items = list(self.db.execute(sql))
            if len(items) == 0:
                continue  # look for next name
            for item in items:
                atts = {k: v for k, v in zip(cols, item) if v is not None}
                path = osp.join(self.database, atts['filename'])
                del atts['filename']
                do_add = True
                if sfilt and sfilt != 'absent':
                    status = self.status_str[self.file_status(path, dtype)]
                    if status != sfilt:
                        do_add = False
                if do_add:
                    data.append({'attributes': atts, 'path': path})
            break  # procname found, don't continue search

        if profile:
            t1 = time.time()
            print('    t1 (compl):', t1 - t0)

        return data

    def proc_param_names(self, proc, procname, param):
        names = []
        fallbacks = []
        fom = self.get_engine()._modules_data[
            'fom']['all_foms'][self.fom]
        todo = []
        if isinstance(proc, Pipeline):
            node = proc.pipeline_node
        else:
            node = proc
        if not procname:
            procname = proc.name
        todo.append((node, procname, param, {}))
        while todo:
            node, procname, param, attr = todo.pop(0)
            # check for FOM-imposed attributes on the process
            fom_patterns = fom.patterns.get(procname)
            if fom_patterns is not None:
                pa = fom_patterns.get('.process_attributes', {})
                attr.update(pa)
            names.append((procname, param, attr))
            if isinstance(node, Process):
                break
            if hasattr(node, 'process'):
                fb = (node.process.name, param, attr)
                if fb not in fallbacks:
                    fallbacks.append(fb)
            plug = node.plugs[param]
            links = [plug.links_to, plug.links_from][int(plug.output)]
            for link in links:
                todo.append((link[2], f'{procname}.{link[0]}', link[1], attr))

        return names + [fb for fb in fallbacks if fb not in names]

    def prepare_status_column(self):
        # check / add status cols in SQLite database
        self.status_db_col = None
        if self.index_status in ('Use', 'Force', 'Set_if_absent') \
                and self.db is not None:
            cname = 'database_qc_status'
            # # reopen DB in this thread
            # if self.database_sqlite:
            #     self.db = sqlite3.connect(self.database_sqlite)
            cols = [c[1] for c in
                    self.db.execute('PRAGMA table_info(files)')]
            self.db_cols = cols
            if cname in cols:
                self.status_db_col = cname
                return  # OK
            if self.index_status in ('Force', 'Set_if_absent'):
                for col in range(len(self.data_types)):
                    data_type = self.data_types[col]
                    stat_func = self.status_for_type.get(data_type)
                    if stat_func is not None:
                        # create missing column
                        self.db.execute(
                            f'ALTER TABLE files ADD {cname} INTEGER DEFAULT -1')
                        self.status_db_col = cname
                        cols = [c[1] for c in
                                self.db.execute('PRAGMA table_info(files)')]
                        self.db_cols = cols
                        return

    def file_status(self, filename, data_type):
        if filename is None:
            return self.statuses.ABSENT
        stat_func = self.status_for_type.get(data_type)
        if stat_func is not None:
            if self.status_db_col is not None and \
                    self.index_status in ('Use', 'Set_if_absent'):
                rfname = osp.relpath(filename, self.database)
                if not hasattr(self, 'file_statuses'):
                    # cache all statuses in a single request
                    statusl = self.db.execute(
                        f'SELECT DISTINCT filename, {self.status_db_col} FROM files WHERE {self.status_db_col} IS NOT NULL')
                    self.file_statuses = {
                        status[0]: status[1] for status in statusl}
                status = self.file_statuses.get(rfname, self.statuses.PRESENT)
                if status >= 0 or self.index_status != 'Set_if_absent':
                    return status
                # print('Empty status')
            status = stat_func(self, filename)
            if self.status_db_col is not None \
                    and self.index_status in ('Force', 'Set_if_absent'):
                rfname = osp.relpath(filename, self.database)
                self.db.execute(
                    f'UPDATE files SET {self.status_db_col}="{status}" WHERE filename="{rfname}"')
                self._commit = True
                if not hasattr(self, 'file_statuses'):
                    self.file_statuses = {}
                self.file_statuses[rfname] = status
            return status
        return self.statuses.PRESENT

    def build_sqlite_index(self, data_type=None):
        from capsul.attributes import fom_index

        if data_type is not None:
            self.data_types = [data_type]
        self.check_parameters()
        engine = self.get_engine()
        proc, procname, param = self.get_process(self.data_types[0], {})

        fom_index.build_fom_sqlite_index(
            engine, self.database_sqlite, directory=self.database,
            main_process=proc, clear_db=True)
