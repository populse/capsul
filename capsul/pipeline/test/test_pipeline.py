##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from __future__ import print_function
import unittest
from traits.api import File, Float
from capsul.api import Process
from capsul.api import Pipeline
from capsul.api import get_process_instance
import tempfile
import os
import sys


class DummyProcess(Process):
    """ Dummy Test Process
    """
    def __init__(self):
        super(DummyProcess, self).__init__()

        # inputs
        self.add_trait("input_image", File(optional=False))
        self.add_trait("other_input", Float(optional=True))

        # outputs
        self.add_trait("output_image", File(optional=False, output=True))
        self.add_trait("other_output", Float(optional=True, output=True))

    def _run_process(self):
        open(self.output_image, 'w').write('dummy output.\n')
        self.other_output = 24.6


class MyPipeline(Pipeline):
    """ Simple Pipeline to test the Switch Node
    """
    def pipeline_definition(self):

        # Create processes
        self.add_process("constant",
            "capsul.pipeline.test.test_pipeline.DummyProcess",
            do_not_export=['input_image', 'other_input'],
            make_optional=['input_image', 'other_input'],)
        self.add_process("node1",
            "capsul.pipeline.test.test_pipeline.DummyProcess")
        self.add_process("node2",
            "capsul.pipeline.test.test_pipeline.DummyProcess")

        # Links
        self.add_link("node1.output_image->node2.input_image")
        self.add_link("node1.other_output->node2.other_input")
        self.add_link("constant.output_image->node2.input_image")

        # Outputs
        self.export_parameter("node1", "input_image")
        self.export_parameter("node1", "other_input")
        self.export_parameter("node2", "output_image", "output")
        self.export_parameter("node2", "other_output")

        self.nodes['constant'].process.name = 'MyPipeline.constant'
        self.nodes['node1'].process.name = 'MyPipeline.node1'
        self.nodes['node2'].process.name = 'MyPipeline.node2'

        # intial internal values
        self.nodes['constant'].process.other_input = 14.65
        self.nodes['constant'].process.input_image = 'blah'


class TestPipeline(unittest.TestCase):

    debug = False

    def setUp(self):
        self.pipeline = MyPipeline()
        self.temp_files = []

    def tearDown(self):
        if hasattr(self, 'temp_files'):
            for filename in self.temp_files:
                try:
                    os.unlink(filename)
                except:
                    pass
            self.temp_files = []

    def test_constant(self):
        graph = self.pipeline.workflow_graph()
        self.assertTrue(
            self.pipeline.nodes['constant'].process.trait(
                'input_image').optional)
        ordered_list = graph.topological_sort()
        self.pipeline.workflow_ordered_nodes()
        self.assertTrue(
            self.pipeline.workflow_repr in
                ("constant->node1->node2", "node1->constant->node2"),
            '%s not in ("constant->node1->node2", "node1->constant->node2")'
                % self.pipeline.workflow_repr)

    def test_enabled(self):
        setattr(self.pipeline.nodes_activation, "node2", False)
        self.pipeline.workflow_ordered_nodes()
        self.assertEqual(self.pipeline.workflow_repr, "")

    def test_run_pipeline(self):
        setattr(self.pipeline.nodes_activation, "node2", True)
        tmp = tempfile.mkstemp('', prefix='capsul_test_pipeline')
        ofile = tmp[1]
        os.close(tmp[0])
        os.unlink(tmp[1])
        try:
            self.pipeline(input_image='/tmp/bloup', output=ofile)
        finally:
            if os.path.exists(tmp[1]):
                os.unlink(tmp[1])

    def run_pipeline_io(self, filename):
        pipeline = MyPipeline()
        from capsul.pipeline import pipeline_tools
        pipeline_tools.save_pipeline(pipeline, filename)
        pipeline2 = get_process_instance(filename)
        pipeline2.workflow_ordered_nodes()

        if self.debug:
            from soma.qt_gui.qt_backend import QtGui
            from capsul.qt_gui.widgets import PipelineDevelopperView
            import sys
            app = QtGui.QApplication.instance()
            if not app:
                app = QtGui.QApplication(sys.argv)
            view1 = PipelineDevelopperView(
                pipeline, allow_open_controller=True, enable_edition=True,
                show_sub_pipelines=True)

            view2 = PipelineDevelopperView(
                pipeline2, allow_open_controller=True, enable_edition=True,
                show_sub_pipelines=True)
            view1.show()
            view2.show()
            app.exec_()

        self.assertTrue(
            pipeline2.workflow_repr in
                ("constant->node1->node2", "node1->constant->node2"),
            '%s not in ("constant->node1->node2", "node1->constant->node2")'
                % pipeline2.workflow_repr)
        d1 = pipeline_tools.dump_pipeline_state_as_dict(pipeline)
        d2 = pipeline_tools.dump_pipeline_state_as_dict(pipeline2)
        self.assertEqual(d1, d2)

    def test_pipeline_io_py(self):
        if self.debug:
            filename = '/tmp/pipeline.py'
        else:
            fd, filename = tempfile.mkstemp(prefix='test_pipeline',
                                            suffix='.py')
            os.close(fd)
            self.temp_files.append(filename)
        self.run_pipeline_io(filename)

    def test_pipeline_xml(self):
        if self.debug:
            filename = '/tmp/pipeline.xml'
        else:
            fd, filename = tempfile.mkstemp(prefix='test_pipeline',
                                            suffix='.xml')
            os.close(fd)
            self.temp_files.append(filename)
        self.run_pipeline_io(filename)

def test():
    """ Function to execute unitest
    """
    if '-d' in sys.argv[1:]:
        TestPipeline.debug = True
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPipeline)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    print("RETURNCODE: ", test())

    if '-v' in sys.argv[1:]:
        import sys
        from soma.qt_gui.qt_backend import QtGui
        from capsul.qt_gui.widgets import PipelineDevelopperView

        app = QtGui.QApplication.instance()
        if not app:
            app = QtGui.QApplication(sys.argv)
        pipeline = MyPipeline()
        #setattr(pipeline.nodes_activation, "node2", False)
        view1 = PipelineDevelopperView(pipeline)
        view1.show()
        app.exec_()
        del view1
