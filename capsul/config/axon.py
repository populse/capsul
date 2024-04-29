from soma.controller import Directory, File, field, undefined

from .configuration import ModuleConfiguration


def axon_default_shared_dir():
    # cannot be implemented as a static method of AxonConfiguration
    # because it is used in a class field, which is evaluated before the class
    # is built

    try:
        from soma import config as soma_config

        shared_dir = soma_config.BRAINVISA_SHARE
    except ImportError:
        return undefined
    return shared_dir


def axon_default_version():
    # cannot be implemented as a static method of AxonConfiguration
    # because it is used in a class field, which is evaluated before the class
    # is built

    try:
        from soma import config as soma_config

        return soma_config.shortVersion
    except ImportError:
        return undefined


class AxonConfiguration(ModuleConfiguration):
    """Axon configuration module"""

    version: str = field(default_factory=axon_default_version)
    shared_directory: Directory = field(default_factory=axon_default_shared_dir)
    user_level: int = field(default=0)
    name = "axon"

    def is_valid_config(self, requirements, explain=False):
        required_version = requirements.get("version")
        if required_version and getattr(self, "version", undefined) != required_version:
            if explain:
                return f"{self.name} configuration does not match required version {required_version}."
            return False
        return True

    @staticmethod
    def axon_default_shared_dir():
        return axon_default_shared_dir()

    @staticmethod
    def axon_default_version():
        return axon_default_version()
