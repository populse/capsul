# -*- coding: utf-8 -*-

from typing import Union

from soma.controller import Controller, OpenKeyDictController

from .dataset import Dataset
from .api import Process

class ExecutionContext(Controller):
    dataset: OpenKeyDictController[Dataset]

    def __init__(self, config=None, executable=None):
        super().__init__()
        self.dataset = OpenKeyDictController[Dataset]()
        if config is not None:
            self.import_dict(config)
        self.executable = executable
