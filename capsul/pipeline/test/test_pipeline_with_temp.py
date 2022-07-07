# -*- coding: utf-8 -*-
import unittest
import tempfile
import os
import sys

from soma.controller import File

from capsul.api import Capsul, Process, Pipeline


class DummyProcess(Process):
    """ Dummy Test Process
    """
    def __init__(self, definition):
        super().__init__(definition)

        # inputs
        self.add_field("input_image", File)

        # outputs
        self.add_field("output_image", File, write=True)

    def execute(self, context):
        # copy input contents to output
        with open(self.output_image, 'w') as f:
            with open(self.input_image) as g:
                f.write(g.read())


class MyPipeline(Pipeline):
    """ Simple Pipeline
    """
    def pipeline_definition(self):

        # Create processes
        self.add_process("node1",
            "capsul.pipeline.test.test_pipeline_with_temp.DummyProcess")
        self.add_process("node2",
            "capsul.pipeline.test.test_pipeline_with_temp.DummyProcess")

        # Links
        self.add_link("node1.output_image->node2.input_image")

        # Outputs
        self.export_parameter("node1", "input_image")
        self.export_parameter("node2", "output_image")


class CatFiles(Process):
    def __init__(self, definition):
        super().__init__(definition)

        # inputs
        self.add_field("inputs", list[File])

        # outputs
        self.add_field("output", File, write=True)

    def execute(self, context):
        with open(self.output, 'w') as f:
            for in_file in self.inputs:
                with open(in_file) as g:
                    f.write(g.read())


class MyIterativePipeline(Pipeline):
    """ Simple Pipeline with iteration and temporary output
    """
    def pipeline_definition(self):

        # Create processes
        self.add_iterative_process("node1",
            "capsul.pipeline.test.test_pipeline_with_temp.DummyProcess",
            iterative_plugs=['input_image', 'output_image'])
        self.add_process("node2",
            "capsul.pipeline.test.test_pipeline_with_temp.CatFiles")

        # Links
        self.add_link("node1.output_image->node2.inputs")

        # Outputs
        self.export_parameter("node1", "input_image", "input_images")
        self.export_parameter("node2", "output")


class TestPipelineWithTemp(unittest.TestCase):

    def setUp(self):
        self.pipeline = Capsul.executable(MyPipeline)
        self.iter_pipeline = Capsul.executable(MyIterativePipeline)

    def tearDown(self):
        Capsul.delete_singleton()

    def test_pipeline_with_temp(self):
        input_f = tempfile.mkstemp(suffix='capsul_input.txt')
        output_f = tempfile.mkstemp(suffix='capsul_output.txt')
        try:
            os.close(input_f[0])
            input_name = input_f[1]
            with open(input_name, 'w') as f:
                f.write('this is my input data\n')
            os.close(output_f[0])
            output_name = output_f[1]

            self.pipeline.input_image = input_name
            self.pipeline.output_image = output_name

            # run sequentially
            with Capsul().engine() as ce:
                ce.run(self.pipeline, timeout=5)

            # test
            self.assertTrue(os.path.exists(output_name))
            with open(input_name) as f:
                with open(output_name) as g:
                    self.assertEqual(f.read(), g.read())

        finally:
            try:
                os.unlink(input_name)
            except OSError:
                pass
            try:
                os.unlink(output_name)
            except OSError:
                pass

    def test_iterative_pipeline_with_temp(self):
        input_f = tempfile.mkstemp(suffix='capsul_input.txt')
        os.close(input_f[0])
        input_name = input_f[1]
        with open(input_name, 'w') as f:
            f.write('this is my input data\n')
        output_f = tempfile.mkstemp(suffix='capsul_output.txt')
        os.close(output_f[0])
        output_name = output_f[1]

        try:
            self.iter_pipeline.input_images = [input_name, input_name,
                                               input_name]
            self.iter_pipeline.output = output_name

            # run sequentially
            with Capsul().engine() as ce:
                ce.run(self.iter_pipeline, timeout=5)

            # test
            self.assertTrue(os.path.exists(output_name))
            with open(input_name) as f:
                with open(output_name) as g:
                    r = g.read()
                    self.assertEqual(f.read() * 3, r)
            # check temporary filenames
            o = self.iter_pipeline.nodes['node1'].output_image
            self.assertEqual(len(o), 3)
            for f in o:
                self.assertTrue(f.startswith('!{dataset.tmp.path}/node1.DummyProcess.output_image_'))

        finally:
            try:
                os.unlink(input_name)
            except OSError: pass
            try:
                os.unlink(output_name)
            except OSError: pass


def test():
    """ Function to execute unitest
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPipelineWithTemp)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    import sys
    from soma.qt_gui.qt_backend import QtGui
    from capsul.qt_gui.widgets import PipelineDeveloperView

    app = QtGui.QApplication.instance()
    if not app:
        app = QtGui.QApplication(sys.argv)
    pipeline = Capsul.executable(MyPipeline)
    pipeline.input_image = '/data/file.txt'
    pipeline.output_image = '/data/output_file.txt'
    view1 = PipelineDeveloperView(pipeline)
    view1.show()

    pipeline2 = Capsul.executable(MyIterativePipeline)
    pipeline2.input_images = ['/data/file.txt', '/data/file.txt',
                                '/data/file.txt']
    pipeline2.output = '/data/output_file.txt'
    view2 = PipelineDeveloperView(pipeline2)
    view2.show()
    app.exec_()

    del view1, view2
