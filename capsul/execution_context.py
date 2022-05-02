# -*- coding: utf-8 -*-

from populse_db import Database
from soma.controller import Controller, OpenKeyDictController

from .dataset import Dataset


class ExecutionContext(Controller):
    dataset: OpenKeyDictController[Dataset]

    def __init__(self, config=None, executable=None):
        super().__init__()
        self.dataset = OpenKeyDictController[Dataset]()
        if config is not None:
            self.import_dict(config)
        self.executable = executable

class ExecutionStatus:
    def __init__(self, path):
        self.db = Database(path)
        self.collection = None
    
    def __enter__(self):
        session = self.db.__enter__()
        if not session.has_collection('status'):
            session.add_collection('status')
            status = session['status']
            status.add_field('status', str)
            status.add_field('executable', dict)
            status.add_field('execution_context', dict)
            status.add_field('debug_messages', list[str])
            status.add_field('error', str)
            status.add_field('error_detail', str)
            status.add_field('output_fields', dict)
            status.add_field('start_time', str)
            status.add_field('pid', int)
            status[''] = {}
        self.collection = session['status']
        return self
    
    def __exit__(self, *args):
        self.db.__exit__(*args)
        self.session = None
    
    def __getitem__(self, name):
        result = self.get(name, ...)
        if result is ...:
            raise KeyError(name)
        return result

    def get(self, name, default=None):
        row = self.collection.document('', fields=[name], as_list=True)
        if row is None or row[0] is None:
            return default
        return row[0]
    
    def __setitem__(self, name, value):
        self.collection.update_document('', {name: value})

    def update(self, kwargs):
        self.collection.update_document('', kwargs)

    def as_dict(self, keys=None):
        if keys:
            return dict((k, v) for k, v in self.collection.document('', fields=keys).items() if v is not None)
        else:
            return self.collection.document('')
