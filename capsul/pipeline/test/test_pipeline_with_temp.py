# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import absolute_import

import unittest
import tempfile
import os
import sys
from traits.api import File, Float, List
from capsul.api import Process, Pipeline


class DummyProcess(Process):
    """ Dummy Test Process
    """
    def __init__(self):
        super(DummyProcess, self).__init__()

        # inputs
        self.add_trait("input_image", File(optional=False))

        # outputs
        self.add_trait("output_image", File(optional=False, output=True))

    def _run_process(self):
        # copy input contents to output
        print(self.name, ':', self.input_image, '->', self.output_image)
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
    def __init__(self):
        super(CatFiles, self).__init__()

        # inputs
        self.add_trait("inputs", List(File(optional=False)))

        # outputs
        self.add_trait("output", File(optional=False, output=True))

    def _run_process(self):
        print('cat', self.inputs, 'to:', self.output)
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
        self.pipeline = MyPipeline()
        self.iter_pipeline = MyIterativePipeline()

    def test_pipeline_with_temp(self):
        input_f = tempfile.mkstemp(suffix='capsul_input.txt')
        os.close(input_f[0])
        input_name = input_f[1]
        with open(input_name, 'w') as f:
            f.write('this is my input data\n')
        output_f = tempfile.mkstemp(suffix='capsul_output.txt')
        os.close(output_f[0])
        output_name = output_f[1]
        #os.unlink(output_name)

        try:
            self.pipeline.input_image = input_name
            self.pipeline.output_image = output_name

            # run sequentially
            self.pipeline()

            # test
            self.assertTrue(os.path.exists(output_name))
            with open(input_name) as f:
                with open(output_name) as g:
                    self.assertEqual(f.read(), g.read())

        finally:
            try:
                os.unlink(input_name)
            except OSError: pass
            try:
                os.unlink(output_name)
            except OSError: pass

    def test_iterative_pipeline_with_temp(self):
        input_f = tempfile.mkstemp(suffix='capsul_input.txt')
        os.close(input_f[0])
        input_name = input_f[1]
        with open(input_name, 'w') as f:
            f.write('this is my input data\n')
        output_f = tempfile.mkstemp(suffix='capsul_output.txt')
        os.close(output_f[0])
        output_name = output_f[1]
        #os.unlink(output_name)

        try:
            self.iter_pipeline.input_images = [input_name, input_name,
                                               input_name]
            self.iter_pipeline.output = output_name

            # run sequentially
            self.iter_pipeline()

            # test
            self.assertTrue(os.path.exists(output_name))
            with open(input_name) as f:
                with open(output_name) as g:
                    self.assertEqual(f.read() * 3, g.read())
            # check intermediate filenames are empty
            self.assertEqual(
                self.iter_pipeline.nodes['node1'].process.output_image,
                ['', '', ''])

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
    print("RETURNCODE: ", test())

    if '-v' in sys.argv[1:] or '--verbose' in sys.argv[1:]:
        import sys
        from soma.qt_gui.qt_backend import QtGui
        from capsul.qt_gui.widgets import PipelineDeveloperView

        app = QtGui.QApplication.instance()
        if not app:
            app = QtGui.QApplication(sys.argv)
        pipeline = MyPipeline()
        pipeline.input_image = '/data/file.txt'
        pipeline.output_image = '/data/output_file.txt'
        view1 = PipelineDeveloperView(pipeline)
        view1.show()

        pipeline2 = MyIterativePipeline()
        pipeline2.input_images = ['/data/file.txt', '/data/file.txt',
                                  '/data/file.txt']
        pipeline2.output = '/data/output_file.txt'
        view2 = PipelineDeveloperView(pipeline2)
        view2.show()
        app.exec_()

        del view1, view2
