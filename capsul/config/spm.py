# -*- coding: utf-8 -*-

from .configuration import ModuleConfiguration
from soma.controller import Directory, undefined


class SPMConfiguration(ModuleConfiguration):
    """SPM configuration module"""

    directory: Directory
    version: str
    standalone: bool = False
    name = "spm"

    module_dependencies = ["matlab"]

    def is_valid_config(self, requirements):
        required_version = requirements.get("version")
        if required_version and getattr(self, "version", undefined) != required_version:
            return False
        if self.standalone:
            return {"matlab": {"mcr": True}}
        else:
            return {"matlab": {"mcr": False}}


def init_execution_context(execution_context):
    """
    Configure an execution context given a capsul_engine and some requirements.
    """
    config = execution_context.config["modules"]["spm"]
    execution_context.spm = SPMConfiguration()
    execution_context.spm.import_dict(config)
