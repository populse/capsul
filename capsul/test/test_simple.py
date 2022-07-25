# -*- coding: utf-8 -*-
import unittest

import capsul.api
from capsul.api import Capsul, Process, Pipeline
from soma.controller import field, File


class ProcessWithInputAndOutputFiles(Process):
    input_file: File
    output_file: File = field(write=True)
    has_run: bool = field(output=True)
    def execute(self, context):
        assert self.input_file == 'input.txt'
        assert self.output_file == 'output.txt'
        self.has_run = True


class ProcessWithOutputFile(Process):
    output_file: File = field(write=True)
    def execute(self, context):
        assert self.output_file is not None and self.output_file != ''
        with open(self.output_file, 'w') as f:
            f.write('ProcessWithOutputFile has run!\n')
        print(self.output_file)


class ProcessWithInputFile(Process):
    input_file: File
    name_of_input_file: str = field(output=True)
    has_run: bool = field(output=True)
    def execute(self, context):
        assert self.input_file is not None and self.input_file != ''
        with open(self.input_file, 'r') as f:
            file_contents = f.read()
        assert file_contents == 'ProcessWithOutputFile has run!\n'
        self.name_of_input_file = str(self.input_file)
        self.has_run = True


class PipelineWithInputAndOutputFiles(Pipeline):
    def pipeline_definition(self):
        self.add_process('process', ProcessWithInputAndOutputFiles)
        self.export_parameter('process', 'input_file')
        self.export_parameter('process', 'output_file')
        self.export_parameter('process', 'has_run', 'process_has_run')


class SimplePipelineTests(unittest.TestCase):
    def test_input_and_output_files(self):
        p = capsul.api.executable(PipelineWithInputAndOutputFiles)
        p.input_file = 'input.txt'
        p.output_file = 'output.txt'
        with Capsul().engine() as ce:
            ce.run(p)
        assert p.process_has_run

    def test_custom_pipeline_with_input_and_output_files(self):
        p = capsul.api.executable({
            "type": "custom_pipeline",
            "name": "simple_pipeline_with_output_file",
            "definition": {
                "export_parameters": False,
                "executables": {
                    "process": {
                        "definition": "capsul.test.test_simple.ProcessWithInputAndOutputFiles",
                        "type": "process",
                    },
                },
                "links": [
                    "input->process.input_file",
                    "process.output_file->output",
                    "process.has_run->process_has_run",
                ],
            },
        })
        p.input = 'input.txt'
        p.output = 'output.txt'
        with Capsul().engine() as ce:
            ce.run(p)
        assert p.process_has_run

    def test_intermediate_temporary_file(self):
        p = capsul.api.executable({
            "type": "custom_pipeline",
            "name": "pipeline_with_intermediate_temporary_file",
            "definition": {
                "export_parameters": False,
                "executables": {
                    "process1": {
                        "definition": "capsul.test.test_simple.ProcessWithOutputFile",
                        "type": "process",
                    },
                    "process2": {
                        "definition": "capsul.test.test_simple.ProcessWithInputFile",
                        "type": "process",
                    },
                },
                "links": [
                    "process1.output_file->process2.input_file",
                    "process2.name_of_input_file->name_of_intermediate_file",
                    "process2.has_run->process_has_run",
                ],
            },
        })
        with Capsul().engine() as ce:
            ce.run(p)
        assert p.process_has_run
        #print(p.name_of_intermediate_file)
