# -*- coding: utf-8 -*-
from capsul.attributes.completion_engine import ProcessCompletionEngine
import capsul.info as capinfo
import soma.info as sominfo
import traits.api as traits
import os
import os.path as osp
import sqlite3
import time
import datetime


def build_fom_sqlite_index(engine, sqlite_file, directory=None,
                           main_process=None, clear_db=True):
    t0 = time.time()
    cols = ['filename']
    if main_process is not None:
        # force loading all relatesd FOMS and switch to the most complete one
        pc = ProcessCompletionEngine.get_completion_engine(main_process)
        attributes = pc.get_attribute_values()
        for t in attributes.user_traits():
            if t not in ('generated_by_process', 'generated_by_parameter'):
                cols.append(t)
            if getattr(attributes, t) in (None, traits.Undefined):
                setattr(attributes, t, 'X')
        pc.complete_parameters()

    with engine.settings as session:
        config = session.config('fom', 'global')
        if directory is None:
            directory = config.input_directory
        if directory != config.input_directory \
                and directory == config.output_directory:
            fom = config.output_fom
        else:
            fom = config.input_fom
        config.input_directory = directory
        config.output_directory = directory

    if clear_db and osp.exists(sqlite_file):
        os.unlink(sqlite_file)
    db = sqlite3.connect(sqlite_file)
    db.execute('CREATE TABLE IF NOT EXISTS fom '
               '(fom_name, capsul_version, fom_version)')
    db.execute(f'CREATE TABLE IF NOT EXISTS files ({", ".join(cols)})')
    capver = f'{capinfo.version_major}.{capinfo.version_minor}'
    somver = f'{sominfo.version_major}.{sominfo.version_minor}'
    db.execute('INSERT OR REPLACE INTO fom (fom_name, capsul_version, '
               f'fom_version) VALUES ("{fom}", "{capver}", "{somver}")')
    # get existing cols
    db_cols = set()
    for col in db.execute('PRAGMA table_info(files)'):
        db_cols.add(col[1])

    pta = engine._modules_data['fom']['fom_pta']['all'][fom]
    nfiles = 0
    nindex = 0

    for dirpath, dirnames, filenames in os.walk(directory):
        for p in dirnames + filenames:
            path = osp.join(dirpath, p)
            rpath = osp.relpath(path, directory)
            # print('test:', rpath)
            nfiles += 1
            for pdef in pta.parse_path(rpath):
                nindex += 1
                # print('index:', rpath)
                # print(pdef)
                d = {k: v for k, v in pdef[2].items() if k != 'fom_name'}
                d['filename'] = rpath
                new_cols = [c for c in d if c not in db_cols]
                for col in new_cols:
                    db.execute(f'ALTER TABLE files ADD {col}')
                db_cols.update(new_cols)
                values = ", ".join([f'"{x}"' for x in d.values()])
                db.execute('INSERT OR REPLACE INTO files '
                           f'({", ".join(d.keys())}) VALUES ({values})')
            if nfiles % 1000 == 0:
                print(f'\rfiles: {nfiles}, indexed: {nindex}', end='')

    db.commit()

    print()
    print('parsed files:', nfiles)
    print('indexed items:', nindex)
    print('parsing time:', datetime.timedelta(seconds=time.time() - t0))
