# -*- coding: utf-8 -*-

from capsul.api import Process
from traits.api import File, Undefined
import os


class WriteEngineConfig(Process):
    """Write the current engine config to a JSON file.

    The process is for instance useful when run from Axon, through axon/capsul
    wrapping, to write the BrainVisa/Axon config for reuse in later Capsul
    processing.

    Run it using::

        axon-runprocess capsul://capsul.engine.write_engine_config engine.json

    Then pass it to ``python -m capsul --config`` option::

        python -m capsul --config engine.json capsul.engine.write_engine_config engine2.json
    """
    output_config_file = File(
        output=True, optional=False, allowed_extensions=['.json'],
        desc="output JSON config file")

    def requirements(self):
        # requires current settings modules
        ce = self.get_study_config().engine
        c = ce.settings.select_configurations('global',
                                              check_invalid_mods=True)
        req = {k: 'any' for k in c if k != 'capsul_engine'}
        req = ce.settings.select_configurations(
            'global', uses=req, check_invalid_mods=True).get(
                'capsul_engine', {}).get('uses', {})
        return req

    def _run_process(self):
        import json
        config = self.get_study_config().engine.settings.export_config_dict()
        if len(config) == 1:
            param_file = os.environ.get('SOMAWF_INPUT_PARAMS')
            if param_file and os.path.exists(param_file):
                with open(param_file) as f:
                    params = json.load(f)
                config = {'global': params.get('configuration_dict')}

        with open(self.output_config_file, 'w') as f:
            json.dump(config, f)

