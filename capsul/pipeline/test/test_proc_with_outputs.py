##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from __future__ import print_function

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
if sys.version_info[0] >= 3:
    import io as StringIO
else:
    import StringIO

class DummyProcess1(Process):
    """ Dummy Test Process
    """
    def __init__(self):
        super(DummyProcess1, self).__init__()

        # inputs
        self.add_trait("input", File(optional=False))

        # outputs
        self.add_trait("output", File(output=True, input_filename=False))

    def _run_process(self):
        iname = os.path.splitext(self.input)
        self.output = '%s_output%s' % iname
        with open(self.output, 'w') as f:
            f.write('This is an output file\n')

class DummyProcess2(Process):
    """ Dummy Test Process
    """
    def __init__(self):
        super(DummyProcess2, self).__init__()

        # inputs
        self.add_trait("input", File(optional=False))

        # outputs
        self.add_trait("outputs", List(File(output=True, input_filename=False),
                                       output=True, input_filename=False))

    def _run_process(self):
        new_output = '%s_bis%s' % os.path.splitext(self.input)
        self.outputs = [self.input, new_output]
        with open(new_output, 'w') as f:
            f.write(open(self.input).read() + 'And a second output file\n')

class DummyProcess2alt(Process):
    """ Dummy Test Process
    """
    def __init__(self):
        super(DummyProcess2alt, self).__init__()

        # inputs
        self.add_trait("input", File(optional=False))

        # outputs
        self.add_trait("outputs", List(File(output=True, input_filename=False),
                                       output=True, input_filename=False))

    def _run_process(self):
        new_output = '%s_ter%s' % os.path.splitext(self.input)
        self.outputs = [new_output]
        with open(new_output, 'w') as f:
            f.write(open(self.input).read() + 'And another output file\n')

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
                f.write(open(in_filename).read())

class DummyPipeline(Pipeline):

    def pipeline_definition(self):
        # Create processes
        self.add_process(
            "node1",
            'capsul.pipeline.test.test_proc_with_outputs.DummyProcess1')
        self.add_process(
            "node2",
            'capsul.pipeline.test.test_proc_with_outputs.DummyProcess2')
        self.add_process(
            "node2alt",
            'capsul.pipeline.test.test_proc_with_outputs.DummyProcess2alt')
        self.add_switch('node2_switch', ['node2', 'node2alt'], ['files'],
                        output_types=[List(File(output=True,
                                                input_filename=False),
                                           output=True, input_filename=False)])
        self.add_process(
            "node3",
            'capsul.pipeline.test.test_proc_with_outputs.DummyProcess3')
        # Links
        self.add_link("node1.output->node2.input")
        self.add_link("node1.output->node2alt.input")
        self.add_link("node2.outputs->node2_switch.node2_switch_files")
        self.add_link("node2alt.outputs->node2_switch.node2alt_switch_files")
        self.add_link("node2_switch.files->node3.input")

        #self.export_parameter('node2alt', 'outputs', 'node2alt_outputs')

        self.node_position = {
            'inputs': (0.0, 155.7061),
            'node1': (146.82718967435613, 124.69369999999998),
            'node2': (303.38348967435616, 0.0),
            'node2_switch': (467.2083896743562, 89.69369999999998),
            'node2alt': (303.38348967435616, 124.69369999999998),
            'node3': (709.7284896743562, 124.69369999999998),
            'outputs': (868.9687193487123, 128.69369999999998)}


class TestPipelineContainingProcessWithOutputs(unittest.TestCase):

    def setUp(self):
        self.pipeline = DummyPipeline()

        tmpout = tempfile.mkstemp('.txt', prefix='capsul_test_')
        os.close(tmpout[0])
        os.unlink(tmpout[1])

        # use a custom temporary soma-workflow dir to avoid concurrent
        # access problems
        tmpdb = tempfile.mkstemp('', prefix='soma_workflow')
        os.close(tmpdb[0])
        os.unlink(tmpdb[1])
        self.soma_workflow_temp_dir = tmpdb[1]
        os.mkdir(self.soma_workflow_temp_dir)
        swf_conf = '[%s]\nSOMA_WORKFLOW_DIR = %s\n' \
            % (socket.gethostname(), tmpdb[1])
        swconfig.Configuration.search_config_path \
            = staticmethod(lambda : StringIO.StringIO(swf_conf))

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
            # stop workflow controler and wait for thread termination
            swc.stop_engine()
        if '--keep-tmp' not in sys.argv[1:]:
            if os.path.exists(self.output):
              os.unlink(self.output)
            shutil.rmtree(self.soma_workflow_temp_dir)


    def test_direct_run(self):
        self.study_config.use_soma_workflow = False
        self.pipeline.node2_switch = 'node2'
        self.pipeline()
        self.assertEqual(self.pipeline.nodes["node1"].process.output,
                         '/tmp/file_in_output.nii')
        self.assertEqual(self.pipeline.nodes["node3"].process.input,
                         ['/tmp/file_in_output.nii', '/tmp/file_in_output_bis.nii'])
        res_out = open(self.pipeline.output).readlines()
        self.assertEqual(res_out,
                         ['This is an output file\n',
                          'This is an output file\n',
                          'And a second output file\n'])

    def test_direct_run_switch(self):
        self.study_config.use_soma_workflow = False
        # change switch and re-run
        self.pipeline.node2_switch = 'node2alt'
        self.pipeline()
        self.assertEqual(self.pipeline.nodes["node1"].process.output,
                         '/tmp/file_in_output.nii')
        self.assertEqual(self.pipeline.nodes["node3"].process.input,
                         ['/tmp/file_in_output_ter.nii'])
        res_out = open(self.pipeline.output).readlines()
        self.assertEqual(res_out,
                         ['This is an output file\n',
                          'And another output file\n'])

    def test_full_wf(self):
        self.study_config.use_soma_workflow = True
        self.pipeline.node2_switch = 'node2'

        #workflow = pipeline_workflow.workflow_from_pipeline(self.pipeline)
        #import soma_workflow.client as swc
        #swc.Helper.serialize('/tmp/workflow.workflow', workflow)

        result = self.study_config.run(self.pipeline, verbose=True)
        self.assertEqual(self.pipeline.nodes["node1"].process.output,
                         '/tmp/file_in_output.nii')
        self.assertEqual(self.pipeline.nodes["node3"].process.input,
                         ['/tmp/file_in_output.nii', '/tmp/file_in_output_bis.nii'])
        res_out = open(self.pipeline.output).readlines()
        self.assertEqual(res_out,
                         ['This is an output file\n',
                          'This is an output file\n',
                          'And a second output file\n'])

    def test_full_wf_switch(self):
        self.study_config.use_soma_workflow = True
        # change switch and re-run
        self.pipeline.node2_switch = 'node2alt'
        workflow = pipeline_workflow.workflow_from_pipeline(self.pipeline)
        import soma_workflow.client as swc
        swc.Helper.serialize('/tmp/workflow.workflow', workflow)

        result = self.study_config.run(self.pipeline, verbose=True)
        self.assertEqual(self.pipeline.nodes["node1"].process.output,
                         '/tmp/file_in_output.nii')
        self.assertEqual(self.pipeline.nodes["node3"].process.input,
                         ['/tmp/file_in_output_ter.nii'])
        res_out = open(self.pipeline.output).readlines()
        self.assertEqual(res_out,
                         ['This is an output file\n',
                          'And another output file\n'])


def test():
    """ Function to execute unitest
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(
        TestPipelineContainingProcessWithOutputs)
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
        from capsul.qt_gui.widgets import PipelineDevelopperView

        app = QtGui.QApplication(sys.argv)
        pipeline = DummyPipeline()
        pipeline.input = '/tmp/file_in.nii'
        pipeline.output = '/tmp/file_out3.nii'
        pipeline.node2_switch = 'node2alt'
        view1 = PipelineDevelopperView(pipeline, show_sub_pipelines=True,
                                       allow_open_controller=True)
        view1.show()
        app.exec_()
        del view1

