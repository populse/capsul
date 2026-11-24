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
    ''' Data selector which will parse existing files on a filesystem based on
the FOM description system.
    '''

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
        '''
        '''
        profile = False
        if profile:
            t0 = time.time()

        proc, procname, param = self.get_process(dtype, dfilt)
        engine = self.get_engine()

        short_procname = procname.rsplit('.')[-1]
        path_pat = getattr(proc, param)
        # print('path_pat:', path_pat)
        if profile:
            t1 = time.time()
            print('    t1 (compl):', t1 - t0)
            t0 = t1

        exhaustive_parse = False
        if self.upstream_selector:
            def walk_upstream(dtype, dfilt, sfilt):
                for item in self.upstream_selector.find_items(dtype, dfilt,
                                                              sfilt):
                    yield item['path']

            paths = walk_upstream(dtype, dfilt, sfilt)
            exhaustive_parse = True

        else:
            paths = glob.iglob(path_pat)
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
                # print('path:', p, 'attl:', len(attl), ', proc:', procname, short_procname)
                if exhaustive_parse:
                    # filter dfilt here because path_pat has not been used
                    fatts = []
                    for att in attl:
                        attd = att[2]
                        for k, v in dfilt.items():
                            if k not in attd or attd[k] != v:
                                break
                        else:
                            fatts.append(att)
                    attl = fatts
                if len(attl) == 1 and not exhaustive_parse:
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
                        yield {'attributes': atts[2], 'path': p}
                    break
        if profile:
            t1 = time.time()
            print('    t3 (fom)  :', t1 - t0)
            t0 = t1


class DataFilter(DataSelector):

    def find_items(self, dtype, dfilt, sfilt):
        '''
        '''
        if self.upstream_selector is None:
            raise ValueError(
                'DataFilter needs to have an upstream selector as a data '
                'source.')

        profile = False
        if profile:
            t0 = time.time()

        refilt = {re.compile(k): re.compile(v) for k, v in dfilt.items()}

        for patt in self.upstream_selector.find_items(dtype, dfilt, sfilt):
            keep = True
            attd = patt['attributes']
            for k, v in refilt.items():
                found = False
                for ka, va in attd.items():
                    if k.match(ka):
                        found = True
                        if not v.match(va):
                            keep = False
                            break
                if not keep:
                    break
                if not found:
                    # no key matches the resquested one: reject
                    # (this behaviour is sometimes questionable if k is a
                    # pattern)
                    keep = False
                    break
            else:
                keep = True
            if not keep:
                continue

            do_add = True
            if sfilt and sfilt != 'absent':
                status = self.status_str[self.file_status(patt['path'], dtype)]
                if status != sfilt:
                    do_add = False
            if do_add:
                yield patt

        if profile:
            t1 = time.time()
            print('    t3 (fom)  :', t1 - t0)
            t0 = t1
