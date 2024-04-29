from soma.controller import Directory, File, field, undefined

from .configuration import ModuleConfiguration


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

    def is_valid_config(self, requirements, explain=False):
        if (
            getattr(self, "executable", undefined) is undefined
            and getattr(self, "mcr_directory", undefined) is undefined
        ):
            # at least one of those must be defined and valid
            if explain:
                return f"{self.name} configuration must have either 'executable' or 'mcr_directory' attribute to be defined."
            return False
        required_version = requirements.get("version")
        if required_version and getattr(self, "version", undefined) != required_version:
            if explain:
                return f"{self.name} configuration does not match required version {required_version}."
            return False
        require_mcr = requirements.get("mcr", None)
        if require_mcr:
            if getattr(self, "mcr_directory", undefined) is undefined:
                # no MCR defined
                if explain:
                    return f"{self.name} configuration requires 'mcr_directory' attribute to be defined."
                return False
            mcr_version = requirements.get("mcr_version")
            if mcr_version and getattr(self, "mcr_version", undefined) != mcr_version:
                # MCR has not the expected version
                if explain:
                    return f"{self.name} configuration does not match required MCR version {mcr_version}."
                return False
        elif require_mcr is False:
            # non-MCR explicitly required
            if getattr(self, "executable", undefined) is undefined:
                # executable is not defined
                if explain:
                    return f"{self.name} configuration requires 'executable' attribute to be defined."
                return False
        return True

    @staticmethod
    def init_execution_context(execution_context):
        """
        Configure execution (env variables) from a configured execution context
        """
        from capsul.in_context import matlab

        matlab.set_env_from_config(execution_context)
