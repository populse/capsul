# -*- coding: utf-8 -*-
import os

from capsil.api import Capsul

class ExecutionContext:
    def __init__(self):
        capsul = Capsul()
        config_file = os.environ.get('CAPSUL_CONFIG')
        if config_file:
            engine = capsul.engine(config_file=config_file)
        else:
            engine = capsul.engine()

        requirements_file = os.environ.get('CAPSUL_REQUIREMENTS')
        if requirements_file:
            with open(requirements_file) as f:
                requirements = json.load(f)
            for module_name, module_requirements in requirements.items():
                module = engine.module(module_name)
                module.init_context_with_requirements(engine, self, **module_requirements)
