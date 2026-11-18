# -*- coding: utf-8 -*-

from .data_selector import DataSelector
from capsul.attributes.completion_engine import ProcessCompletionEngine
import re
import glob
import os
import os.path as osp
import traits.api as traits
import time


class DataParser(DataSelector):

    def __init__(self, database, **kwargs):
        super().__init__(database,
                         engine=kwargs.get('engine'),
                         fom=kwargs.get('fom'),
                         data_types=kwargs.get('data_types'),
                         data_filters=kwargs.get('data_filters'))
        self.type_labels = kwargs.get('type_labels')
        self.data_parameters.append('type_labels')

    def check_parameters(self):
        super().check_parameters()
        if self.type_labels in (None, traits.Undefined):
            self.type_labels = self.data_types

    def find_data(self):
        data = []
        profile = False
        if profile:
            print('find_data')
            t0 = time.time()

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

        for i, dtype in enumerate(self.data_types):
            items = self.find_items(dtype, data_filters[i],
                                    self.status_filters[i])
            data.append((dtype, items))
            # print(dtype, ':', len(items), 'items')
            if profile:
                print('time:', time.time() - t0)

        return data

    def get_process(self, dtype, dfilt):
        engine = self.get_engine()
        if not hasattr(engine, '_modules_data') \
                or 'fom' not in engine._modules_data:
            engine.load_modules(['fom', 'axon'])
        with engine.settings as session:
            config = session.config('fom', 'global')
            config.input_fom = self.fom
            config.output_fom = self.fom
            if self.database is not None:
                config.input_directory = self.database
                config.output_directory = self.database

        procname, param = dtype.rsplit('.', 1)

        # use a cached process with its completion to speed up
        # repeated parameters scan on the same process
        if not hasattr(self, '_cached_procs'):
            self._cached_procs = {}
        if procname in self._cached_procs:
            proc, cached_atts = self._cached_procs[procname]
        else:
            proc = engine.get_process_instance(procname)
            self._cached_procs[procname] = [proc, dfilt]
            cached_atts = None
        if cached_atts != dfilt:
            pc = ProcessCompletionEngine.get_completion_engine(proc)
            att = pc.get_attribute_values()
            for k, v in att.user_traits().items():
                val = '*'
                if k in dfilt:
                    val = dfilt[k]
                setattr(att, k, val)
            # print('completion values:', att.export_to_dict())
            pc.complete_parameters()
            self._cached_procs[procname][1] = dfilt

        return proc, procname, param

    def find_items(self, dtype, dfilt, sfilt):
        profile = False
        if profile:
            t0 = time.time()

        # FIXME this is a bidouille at the moment.
        if osp.basename(self.database) in ('rawdata', 'sourcedata'):
            # assume raw bids, parse every filename to match every possible
            # shape
            exhaustive_parse = True
        else:
            exhaustive_parse = False

        proc, procname, param = self.get_process(dtype, dfilt)
        engine = self.get_engine()

        data = []

        short_procname = procname.rsplit('.')[-1]
        path_pat = getattr(proc, param)
        # print('path_pat:', path_pat)
        if profile:
            t1 = time.time()
            print('    t1 (compl):', t1 - t0)
            t0 = t1
        if exhaustive_parse:
            def walk(dirname):
                for p in os.walk(dirname):
                    for f in p[2]:
                        yield os.path.join(p[0], f)

            paths = walk(self.database)
        else:
            paths = glob.glob(path_pat)
        if profile:
            t1 = time.time()
            print('    t2 (glob) :', t1 - t0)
            t0 = t1
        for p in paths:
            for fom_type in ('input', 'output'):
                pta = engine._modules_data['fom']['fom_pta'][fom_type]
                attl = list(pta.parse_path(osp.relpath(p, self.database)))
                if len(attl) == 0:
                    continue  # pattern does not match
                atts = None
                # print('path:', p, 'attl:', len(attl), ', proc:', procname)
                if len(attl) == 1:
                    atts = attl[0]
                else:
                    com_att = {}  # keep common attributes across PTAs
                    dif_att = set()
                    for item in attl:
                        att = item[2]
                        for k, v in att.items():
                            if k in dif_att:
                                continue
                            if v != '*':
                                if com_att.get(k, v) != v:
                                    dif_att.add(k)
                                    del com_att[k]
                                else:
                                    com_att[k] = v
                    attl_filt = [item for item in attl
                                 if item[2]['fom_process'] in (procname,
                                                               short_procname)
                                 and item[2]['fom_parameter'] == param]
                    # print('attl_filt:', attl_filt)
                    if exhaustive_parse and len(attl_filt) == 0:
                        # not the searched one
                        continue
                    if len(attl_filt) != 0:
                        atts = attl_filt[0]
                    elif len(attl) != 0:
                        atts = attl[0]
                    atts[2].update(com_att)
                if atts is not None:
                    do_add = True
                    if sfilt and sfilt != 'absent':
                        status = self.status_str[self.file_status(p, dtype)]
                        if status != sfilt:
                            do_add = False
                    if do_add:
                        data.append({'attributes': atts[2], 'path': p})
                    break
        if profile:
            t1 = time.time()
            print('    t3 (fom)  :', t1 - t0)
            t0 = t1

        return data

    def prepare_status_column(self):
        # in filesystem parsing mode: nothing to do
        pass
