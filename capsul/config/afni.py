# -*- coding: utf-8 -*-

from .configuration import ModuleConfiguration
from soma.controller import Directory, undefined, File, field


class AfniConfiguration(ModuleConfiguration):
    """AFNI configuration module"""

    version: str
    directory: Directory = field(optional=True)
    name = "afni"

    def is_valid_config(self, requirements):
        required_version = requirements.get("version")
        if required_version and getattr(self, "version", undefined) != required_version:
            return False
        return True


def init_execution_context(execution_context):
    """
    Configure an execution context given a capsul_engine and some requirements.
    """
    config = execution_context.config["modules"]["afni"]
    execution_context.afni = AfniConfiguration()
    execution_context.afni.import_from_dict(config)
