# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import absolute_import

import unittest
import os
import sys
import tempfile
from traits.api import File, List, Int, Undefined
from capsul.api import Process
from capsul.api import Pipeline, PipelineNode
from capsul.pipeline import pipeline_workflow
from capsul.study_config.study_config import StudyConfig
from soma_workflow import configuration as swconfig
import socket
import shutil
from six.moves import zip

class DummyProcess1(Process):
    """ Dummy Test Process
    """
    def __init__(self):
        super(DummyProcess1, self).__init__()

        # inputs
        self.add_trait("input", File(optional=False))
        self.add_trait("nb_outputs", Int())

        # outputs
        self.add_trait("output", List(File(output=True), output=True))

        self.on_trait_change(self.nb_outputs_changed, "nb_outputs")

    def nb_outputs_changed(self):
        if len(self.output) != self.nb_outputs:
            if len(self.output) > self.nb_outputs:
                self.output = self.output[:self.nb_outputs]
            else:
                self.output \
                    = self.output + [""] * (self.nb_outputs - len(self.output))

    def _run_process(self):
        pass

class DummyProcess2(Process):
    """ Dummy Test Process
    """
    def __init__(self):
        super(DummyProcess2, self).__init__()

        # inputs
        self.add_trait("input", List(File(optional=False)))

        # outputs
        self.add_trait("output", List(File(output=True), output=True))

        self.on_trait_change(self.inputs_changed, "input")

    def inputs_changed(self):
        nout = len(self.output)
        nin = len(self.input)
        if nout != nin:
            if nout > nin:
                self.output = self.output[:nin]
            else:
                self.output = self.output + [""] * (nin - nout)

    def _run_process(self):
        for in_filename, out_filename in zip(self.input, self.output):
            with open(out_filename, 'w') as f:
                f.write(in_filename + '\n')

class DummyProcess3(Process):
    """ Dummy Test Process
    """
    def __init__(self):
        super(DummyProcess3, self).__init__()

        # inputs
        self.add_trait("input", List(File(optional=False)))

        # outputs
        self.add_trait("output", File(output=True))

    def _run_process(self):
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

        self.node_position = {'inputs': (54.0, 298.0),
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
        temp_home_dir = tempfile.mkdtemp('', prefix='soma_workflow')
        os.environ['HOME'] = temp_home_dir
        swconfig.change_soma_workflow_directory(temp_home_dir)
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
        self.pipeline = DummyPipeline()

        tmpout = tempfile.mkstemp('.txt', prefix='capsul_test_')
        os.close(tmpout[0])
        os.unlink(tmpout[1])

        self.output = tmpout[1]
        self.pipeline.input = '/tmp/file_in.nii'
        self.pipeline.output = self.output
        study_config = StudyConfig(modules=['SomaWorkflowConfig'])
        study_config.input_directory = '/tmp'
        study_config.somaworkflow_computing_resource = 'localhost'
        study_config.somaworkflow_computing_resources_config.localhost = {
            'transfer_paths': [],
        }
        self.study_config = study_config

    def tearDown(self):
        swm = self.study_config.modules['SomaWorkflowConfig']
        swc = swm.get_workflow_controller()
        if swc is not None:
            # stop workflow controller and wait for thread termination
            swc.stop_engine()
        if '--keep-tmp' not in sys.argv[1:]:
            if os.path.exists(self.output):
              os.unlink(self.output)


    def test_structure(self):
        self.pipeline.nb_outputs = 3
        self.assertEqual(self.pipeline.nodes["node2"].process.input,
                         ["", "", ""])
        self.assertEqual(self.pipeline.nodes["node2"].process.output,
                         ["", "", ""])

    def test_direct_run(self):
        self.study_config.use_soma_workflow = False
        self.pipeline.nb_outputs = 3
        self.pipeline()
        self.assertEqual(self.pipeline.nodes["node2"].process.input,
                         ["", "", ""])
        self.assertEqual(self.pipeline.nodes["node2"].process.output,
                         ["", "", ""])
        with open(self.pipeline.output) as f:
            res_out = f.readlines()
        self.assertEqual(len(res_out), 3)

    def test_full_wf(self):
        self.study_config.use_soma_workflow = True
        self.pipeline.nb_outputs = 3
        result = self.study_config.run(self.pipeline, verbose=True)
        self.assertEqual(result, None)
        self.assertEqual(self.pipeline.nodes["node2"].process.input,
                         ["", "", ""])
        self.assertEqual(self.pipeline.nodes["node2"].process.output,
                         ["", "", ""])
        with open(self.pipeline.output) as f:
            res_out = f.readlines()
        self.assertEqual(len(res_out), 3)


def test():
    """ Function to execute unitest
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestTemporary)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    verbose = False
    if len(sys.argv) >= 2 and sys.argv[1] in ('-v', '--verbose'):
        verbose = True

    print("RETURNCODE: ", test())

    if verbose:
        import sys
        from soma.qt_gui import qt_backend
        qt_backend.set_qt_backend(compatible_qt5=True)
        from soma.qt_gui.qt_backend import QtGui
        from capsul.qt_gui.widgets import PipelineDeveloperView

        app = QtGui.QApplication(sys.argv)
        pipeline = DummyPipeline()
        pipeline.input = '/tmp/file_in.nii'
        pipeline.output = '/tmp/file_out3.nii'
        pipeline.nb_outputs = 3
        view1 = PipelineDeveloperView(pipeline, show_sub_pipelines=True,
                                       allow_open_controller=True)
        view1.show()
        app.exec_()
        del view1
