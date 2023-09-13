# -*- coding: utf-8 -*-

import unittest
import os
import os.path as osp
import sys
import tempfile
from soma.controller import File, field
from capsul.api import Process, Pipeline, Capsul
import shutil
from six.moves import zip


class DummyProcess1(Process):
    """ Dummy Test Process
    """
    input: File
    nb_outputs: int = 0
    output: field(type_=list[File], write=True, default_factory=list)

    def __init__(self, definition):
        super().__init__(definition)

        self.on_attribute_change.add(self.nb_outputs_changed, "nb_outputs")

    def nb_outputs_changed(self):
        if len(self.output) != self.nb_outputs:
            self.output = [''] * self.nb_outputs
            if self.pipeline:
                self.pipeline.dispatch_value(self, 'output', self.output)

    def execute(self, context=None):
        pass


class DummyProcess2(Process):
    """ Dummy Test Process
    """
    input: field(type_=list[File], default_factory=list)
    output: field(type_=list[File], write=True, default_factory=list)

    def __init__(self, definition):
        super().__init__(definition)

        self.on_attribute_change.add(self.inputs_changed, "input")

    def inputs_changed(self):
        if len(self.output) != len(self.input):
            self.output = [''] * len(self.input)
            if self.pipeline:
                self.pipeline.dispatch_value(self, 'output', self.output)

    def execute(self, context=None):
        for in_filename, out_filename in zip(self.input, self.output):
            with open(out_filename, 'w') as f:
                f.write(in_filename + '\n')


class DummyProcess3(Process):
    """ Dummy Test Process
    """
    input: field(type_=list[File], default_factory=list)
    output: field(type_=File, write=True)

    def __init__(self, definition):
        super().__init__(definition)

    def execute(self, context=None):
        with open(self.output, 'w') as f:
            for in_filename in self.input:
                with open(in_filename) as g:
                    f.write(g.read())


class DummyPipeline(Pipeline):

    def pipeline_definition(self):
        # Create processes
        self.add_process(
            "node1",
            'capsul.pipeline.test.test_temporary.DummyProcess1')
        self.add_process(
            "node2",
            'capsul.pipeline.test.test_temporary.DummyProcess2')
        self.add_process(
            "node3",
            'capsul.pipeline.test.test_temporary.DummyProcess3')
        # Links
        self.add_link("node1.output->node2.input")
        self.add_link("node2.output->node3.input")

        # find_temporary_to_generate(self)
        # self.nodes["node1"].on_attribute_change.add(self.nb_outputs_changed, "nb_outputs")

        # Outputs
        #self.export_parameter("node1", "output",
                              #pipeline_parameter="output1",
                              #is_optional=True)
        #self.export_parameter("node2", "output",
                              #pipeline_parameter="output2",
                              #is_optional=True)
        #self.export_parameter("node2", "input",
                              #pipeline_parameter="input2",
                              #is_optional=True)
        #self.export_parameter("node3", "input",
                              #pipeline_parameter="input3",
                              #is_optional=True)

        self.node_position = {
            'inputs': (54.0, 298.0),
            'node1': (173.0, 168.0),
            'node2': (259.0, 320.0),
            'node3': (405.0, 142.0),
            'outputs': (518.0, 278.0)}


def setUpModule():
    global old_home
    global temp_home_dir
    # Run tests with a temporary HOME directory so that they are isolated from
    # the user's environment
    old_home = os.environ.get('HOME')
    try:
        temp_home_dir = tempfile.mkdtemp('', prefix='capsul_tmp_')
        os.environ['HOME'] = temp_home_dir
    except BaseException:  # clean up in case of interruption
        if old_home is None:
            del os.environ['HOME']
        else:
            os.environ['HOME'] = old_home
        if temp_home_dir:
            shutil.rmtree(temp_home_dir)
        raise


def tearDownModule():
    if old_home is None:
        del os.environ['HOME']
    else:
        os.environ['HOME'] = old_home
    shutil.rmtree(temp_home_dir)


class TestTemporary(unittest.TestCase):

    def setUp(self):
        self.pipeline = Capsul.executable(DummyPipeline)

        tmpout = tempfile.mkstemp('.txt', prefix='capsul_test_')
        os.close(tmpout[0])
        os.unlink(tmpout[1])

        self.output = tmpout[1]
        self.pipeline.input = '/tmp/file_in.nii'
        self.pipeline.output = self.output

        # Create Capsul instance
        self.capsul = Capsul()
        self.capsul.config.databases['builtin']['path'] \
            = osp.join(os.environ['HOME'], 'capsul_engine_database.rdb')
        # study_config = StudyConfig(modules=['SomaWorkflowConfig'])
        # study_config.input_directory = '/tmp'
        # study_config.somaworkflow_computing_resource = 'localhost'
        # study_config.somaworkflow_computing_resources_config.localhost = {
        #     'transfer_paths': [],
        # }
        # self.study_config = study_config

    def tearDown(self):
        if '--keep-tmp' not in sys.argv[1:]:
            if os.path.exists(self.output):
                os.unlink(self.output)

    def test_direct_run_temporary(self):
        self.pipeline.nb_outputs = 3
        with self.capsul.engine() as ce:
            ce.run(self.pipeline, timeout=5)
        with open(self.pipeline.output) as f:
            res_out = f.readlines()
        self.assertEqual(len(res_out), 3)


if __name__ == "__main__":
    from soma.qt_gui import qt_backend
    qt_backend.set_qt_backend(compatible_qt5=True)
    from soma.qt_gui.qt_backend import QtGui
    from capsul.qt_gui.widgets import PipelineDeveloperView

    app = QtGui.QApplication(sys.argv)
    pipeline = Capsul.executable(DummyPipeline)
    pipeline.input = '/tmp/file_in.nii'
    pipeline.output = '/tmp/file_out3.nii'
    pipeline.nb_outputs = 3
    view1 = PipelineDeveloperView(pipeline, show_sub_pipelines=True,
                                  allow_open_controller=True)
    view1.show()
    app.exec_()
    del view1
