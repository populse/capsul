# -*- coding: utf-8 -*-

from soma.controller import Controller, OpenKeyDictController

from .dataset import Dataset

class ExecutionContext(Controller):
    dataset: OpenKeyDictController[Dataset]

    def __init__(self, config=None):
        super().__init__()
        self.dataset = OpenKeyDictController[Dataset]()
        if config is not None:
            self.import_dict(config)
