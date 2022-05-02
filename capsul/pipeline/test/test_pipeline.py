# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import absolute_import

import unittest
from capsul.api import Capsul
from capsul.api import executable
from capsul.api import Process
from capsul.api import Pipeline
from soma.controller import File
import tempfile
import os
import os.path as osp
import sys


class DummyProcess(Process):
    """ Dummy Test Process
    """
    def __init__(self, definition=None):
        if definition is None:
            definition = 'capsul.pipeline.test.test_pipeline.DummyProcess'
        super(DummyProcess, self).__init__(definition)

        # inputs
        self.add_field("input_image", File, optional=False)
        self.add_field("other_input", float, optional=True)

        # outputs
        self.add_field("output_image", File, optional=False, output=True)
        self.add_field("other_output", float, optional=True, output=True)

    def execute(self):
        with open(self.output_image, 'w') as f:
            f.write('dummy output.\n')
        self.other_output = 24.6


class MyPipeline(Pipeline):
    """ Simple Pipeline to test the Switch Node
    """
    def pipeline_definition(self):

        if self.definition is None:
            self.definition = 'capsul.pipeline.test.test_pipeline.MyPipeline'

        # Create processes
        self.add_process("constant",
            "capsul.pipeline.test.test_pipeline.DummyProcess",
            do_not_export=['input_image', 'other_input', 'other_output'],
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

        self.nodes['constant'].name = 'MyPipeline.constant'
        self.nodes['node1'].name = 'MyPipeline.node1'
        self.nodes['node2'].name = 'MyPipeline.node2'

        # initial internal values
        self.nodes['constant'].other_input = 14.65
        self.nodes['constant'].input_image = 'blah'


class TestPipeline(unittest.TestCase):

    debug = False

    def setUp(self):
        self.pipeline = executable(MyPipeline)
        self.temp_files = []

    def tearDown(self):
        if hasattr(self, 'temp_files'):
            for filename in self.temp_files:
                try:
                    os.unlink(filename)
                except OSError:
                    pass
            self.temp_files = []

    def add_py_tmpfile(self, pyfname):
        '''
        add the given .py file and the associated .pyc file to the list of temp
        files to remove after testing
        '''
        self.temp_files.append(pyfname)
        if sys.version_info[0] < 3:
            self.temp_files.append(pyfname + 'c')
        else:
            cache_dir = osp.join(osp.dirname(pyfname), '__pycache__')
            print('cache_dir:', cache_dir)
            cpver = 'cpython-%d%d.pyc' % sys.version_info[:2]
            pyfname_we = osp.basename(pyfname[:pyfname.rfind('.')])
            pycfname = osp.join(cache_dir, '%s.%s' % (pyfname_we, cpver))
            self.temp_files.append(pycfname)
            print('added py tmpfile:', pyfname, pycfname)

    def test_constant(self):
        graph = self.pipeline.workflow_graph()
        self.assertTrue(
            self.pipeline.nodes['constant'].field('input_image').metadata(
                'optional'))
        ordered_list = graph.topological_sort()
        workflow_repr = self.pipeline.workflow_ordered_nodes()
        workflow_repr = '->'.join(x.name.rsplit('.', 1)[-1]
                                  for x in workflow_repr)
        self.assertTrue(
            workflow_repr in
                ("constant->node1->node2", "node1->constant->node2"),
            '%s not in ("constant->node1->node2", "node1->constant->node2")'
                % workflow_repr)

    def test_enabled(self):
        self.pipeline.nodes_activation.node2 = False
        workflow_repr = self.pipeline.workflow_ordered_nodes()
        workflow_repr = '->'.join(x.name.rsplit('.', 1)[-1]
                                  for x in workflow_repr)
        self.assertEqual(workflow_repr, "")

    @unittest.skip('run() is not reimplemented yet.')
    def test_run_pipeline(self):
        setattr(self.pipeline.nodes_activation, "node2", True)
        tmp = tempfile.mkstemp('', prefix='capsul_test_pipeline')
        ofile = tmp[1]
        os.close(tmp[0])
        os.unlink(tmp[1])
        capsul = Capsul()
        try:
            with capsul.engine() as engine:
                engine.run(self.pipeline, input_image='/tmp/bloup',
                           output=ofile)
        finally:
            if os.path.exists(tmp[1]):
                os.unlink(tmp[1])
        Capsul.delete_singleton()

    @unittest.skip('reimplementation expected for capsul v3')
    def run_pipeline_io(self, filename):
        pipeline = executable(MyPipeline)
        from capsul.pipeline import pipeline_tools
        pipeline_tools.save_pipeline(pipeline, filename)
        pipeline2 = executable(filename)
        workflow_repr = pipeline2.workflow_ordered_nodes()

        if self.debug:
            from soma.qt_gui.qt_backend import QtGui
            from capsul.qt_gui.widgets import PipelineDeveloperView
            import sys
            app = QtGui.QApplication.instance()
            if not app:
                app = QtGui.QApplication(sys.argv)
            view1 = PipelineDeveloperView(
                pipeline, allow_open_controller=True, enable_edition=True,
                show_sub_pipelines=True)

            view2 = PipelineDeveloperView(
                pipeline2, allow_open_controller=True, enable_edition=True,
                show_sub_pipelines=True)
            view1.show()
            view2.show()
            app.exec_()

        workflow_repr = '->'.join(x.name.rsplit('.', 1)[-1]
                                  for x in workflow_repr)
        self.assertTrue(
            workflow_repr in
                ("constant->node1->node2", "node1->constant->node2"),
            '%s not in ("constant->node1->node2", "node1->constant->node2")'
                % workflow_repr)
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
            self.add_py_tmpfile(filename)
        self.run_pipeline_io(filename)

    @unittest.skip('XML is no longer supported')
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
        from soma.qt_gui.qt_backend import Qt
        from capsul.qt_gui.widgets import PipelineDeveloperView

        app = Qt.QApplication.instance()
        if not app:
            app = Qt.QApplication(sys.argv)

        pipeline = executable(MyPipeline)
        #setattr(pipeline.nodes_activation, "node2", False)
        view1 = PipelineDeveloperView(pipeline, allow_open_controller=True)
        view1.show()
        app.exec_()
        del view1
