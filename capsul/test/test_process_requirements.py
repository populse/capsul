import tempfile
import unittest
import shutil
import json
import os.path as osp

from pathlib import Path

from soma.controller import File, field

import capsul.api
from capsul.api import Capsul, Pipeline, Process


class ProcessWithSpm12(Process):
    input_file: File
    output_file: File = field(write=True)
    has_run: bool = field(output=True)

    def execute(self, context):
        assert self.input_file == "input.txt"
        assert self.output_file == "output.txt"
        self.has_run = True

ProcessWithSpm12.requirements = {"spm": {"version": "12"}}

class ProcessRequirementsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="capsul_test_process_requirements"))

        return super().setUp()
    
    def tearDown(self):
        shutil.rmtree(self.tmp)
        return super().tearDown()

    def test_spm(self):

        def generate_spm_configuration(config_file, spm_versions, matlab=True):
            # Configuration base dictionary
            config = {
                "builtin": {
                    "persistent": False
                }
            }

            # Create fake SPM directories
            i = 0
            for version in spm_versions:
                fakespm_name = f"spm_{version}_{i}"
                fakespm = self.tmp / "software" / fakespm_name
                fakespm.mkdir(parents=True, exist_ok=True)

                # Write a file containing only the version string that will be used
                # by fakespm module to check installation.
                # (fakespm / "spm").write_text(version)
                # Write a fake template file
                # (fakespm / "template").write_text(f"template of spm {version}")

                fakespm_config = {
                    "directory": str(fakespm),
                    "version": version,
                    "standalone": True,
                }

                config["builtin"].setdefault("spm", {})[
                    fakespm_name
                ] = fakespm_config

                if matlab:
                    matlab_config = {
                        "mcr_directory": str(self.tmp / "software" / "matlab"),
                    }
                    config["builtin"].setdefault("matlab", {})["matlab"] = matlab_config
                i+=1

            # Create a configuration file

            with config_file.open("w") as f:
                json.dump(config, f)

        def get_execution_context_for_config(config_file, process_name):
            capsul = Capsul("test_process_requirements",
                        site_file=config_file,
                        user_file=None,
                        database_path=osp.join(self.tmp, "capsul_engine_database.sqlite"))
    
            # Create  process    
            p = capsul.executable(process_name)
            p.input_file = "input.txt"
            p.output_file = "output.txt"

            with capsul.engine() as engine:
                context = engine.execution_context(p)
                dict_context = context.asdict()
                return dict_context

        # Check error messages in following cases :
        # 1 - multiple spm config are valid
        # 2 - no spm config defined correctly
        # 3 - multiple spm config defined incorrecly
        # 4 - spm standalone config defined correctly

        config_file = self.tmp / "capsul_config.json"
        
        # 1 - multiple spm config are valid
        generate_spm_configuration(config_file, 
                                   spm_versions=("12","12"))
        
        # Check that exception is raised  
        with self.assertRaises(RuntimeError) as context:
            get_execution_context_for_config(config_file, 
                                             "capsul.test.test_process_requirements.ProcessWithSpm12")
        self.assertTrue('Execution environment "builtin" has 2 possible configurations for module spm' == str(context.exception))


        # 2 - no spm config defined correctly
        generate_spm_configuration(config_file, 
                                   spm_versions=("8",))
        
        with self.assertRaises(RuntimeError) as context:
            get_execution_context_for_config(config_file, 
                                            "capsul.test.test_process_requirements.ProcessWithSpm12")
            
        self.assertTrue('''Execution environment "builtin" has no valid configuration for module spm.
  - spm_8_0 is not valid for requirements: spm configuration does not match required version 12''' == str(context.exception))


        # 3 - multiple spm config defined incorrecly
        generate_spm_configuration(config_file, 
                                   spm_versions=("8","8"))
        
        with self.assertRaises(RuntimeError) as context:
            get_execution_context_for_config(config_file, 
                                                "capsul.test.test_process_requirements.ProcessWithSpm12")
        self.assertTrue('''Execution environment "builtin" has no valid configuration for module spm.
  - spm_8_0 is not valid for requirements: spm configuration does not match required version 12
  - spm_8_1 is not valid for requirements: spm configuration does not match required version 12''' == str(context.exception))
  
        # 4 - matlab config not defined correctly
        generate_spm_configuration(config_file, 
                                   spm_versions=("8", "12"),
                                   matlab=False)
        
        with self.assertRaises(RuntimeError) as context:
            get_execution_context_for_config(config_file, 
                                                "capsul.test.test_process_requirements.ProcessWithSpm12")
        print(str(context.exception))
        self.assertTrue('''Execution environment "builtin" has no valid configuration for module matlab.''' == str(context.exception))
  
        # 5 - spm standalone config defined correctly
        generate_spm_configuration(config_file, 
                                   spm_versions=("8", "12"))
        
        context_dict = get_execution_context_for_config(config_file, 
                                        "capsul.test.test_process_requirements.ProcessWithSpm12")
        
        self.assertEqual(
            context_dict,
            {
                'python_modules': [], 
                'config_modules': ['spm', 'matlab'], 
                'dataset': {}, 
                'spm': {
                    'directory': f'{self.tmp}/software/spm_12_1', 
                    'version': '12', 
                    'standalone': True
                }, 
                'matlab': {
                    'mcr_directory': f'{self.tmp}/software/matlab'
                }
            }
        )
        
if __name__ == '__main__':
    unittest.main()