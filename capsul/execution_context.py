# -*- coding: utf-8 -*-
import os

from .engine.local import LocalEngine
from capsul.api import debug

class ExecutionContext:
    def __init__(self, execution_info, tmp):
        self.execution_info = execution_info
        self.tmp = tmp
        self.config = self.execution_info['config']
        debug('ExecutionContext', self.config['modules'])
        for module_name, module_config in self.config['modules'].items():
            debug('config module', module_name)
            module = LocalEngine.module(module_name)
            module.init_execution_context(self)
