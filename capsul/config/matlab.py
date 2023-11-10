# -*- coding: utf-8 -*-

from .configuration import ModuleConfiguration
from soma.controller import Directory, undefined, File, field


class MatlabConfiguration(ModuleConfiguration):
    """Matlab configuration module

    *Specifying requirements:*

    - To be valid, eiher ``executable`` or ``mcr_directory`` should have a
      value
    - ``version`` may be specified in requirements to match (exactly) the
      ``version`` string of the module
    - ``mcr`` (bool) may require ``mcr_directory`` (if True) or ``executable``
      (if False)
    - ``mcr_version`` may require a specific ``mcr_version``, if ``mcr`` is
      True
    """

    executable: File = field(optional=True)
    mcr_directory: Directory = field(optional=True)
    version: str
    mcr_version: str = field(optional=True)

    name = "matlab"

    def is_valid_config(self, requirements):
        if (
            getattr(self, "executable", undefined) is undefined
            and getattr(self, "mcr_directory", undefined) is undefined
        ):
            # at least one of those must be defined and valid
            return False
        required_version = requirements.get("version")
        if required_version and getattr(self, "version", undefined) != required_version:
            return False
        require_mcr = requirements.get("mcr", None)
        if require_mcr:
            if getattr(self, "mcr_directory", undefined) is undefined:
                # no MCR defined
                return False
            mcr_version = requirements.get("mcr_version")
            if mcr_version and getattr(self, "mcr_version", undefined) != mcr_version:
                # MCR has not the expected version
                return False
        elif require_mcr is False:
            # non-MCR explicitly required
            if getattr(self, "executable", undefined) is undefined:
                # executable is not defined
                return False
        return True


def init_execution_context(execution_context):
    """
    Configure an execution context given a capsul_engine and some requirements.
    """
    config = execution_context.config["modules"]["matlab"]
    execution_context.matlab = MatlabConfiguration()
    execution_context.matlab.import_dict(config)
