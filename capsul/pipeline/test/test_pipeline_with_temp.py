##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from __future__ import print_function

import unittest
import tempfile
import os
from traits.api import File, Float
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
        open(self.output_image, 'w').write(open(self.input_image).read())


class MyPipeline(Pipeline):
    """ Simple Pipeline to test the Switch Node
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


class TestPipelineWithTemp(unittest.TestCase):

    def setUp(self):
        self.pipeline = MyPipeline()

    def test_pipeline_with_temp(self):
        input_f = tempfile.mkstemp(suffix='capsul_input.txt')
        os.close(input_f[0])
        input_name = input_f[1]
        open(input_name, 'w').write('this is my input data\n')
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
            self.assertEqual(open(input_name).read(), open(output_name).read())

        finally:
            try:
                os.unlink(input_name)
            except: pass
            try:
                os.unlink(output_name)
            except: pass


def test():
    """ Function to execute unitest
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPipelineWithTemp)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    print("RETURNCODE: ", test())

    if 1:
        import sys
        from soma.qt_gui.qt_backend import QtGui
        from capsul.qt_gui.widgets import PipelineDevelopperView

        app = QtGui.QApplication.instance()
        if not app:
            app = QtGui.QApplication(sys.argv)
        pipeline = MyPipeline()
        pipeline.input_image = '/data/file.txt'
        pipeline.output_image = '/data/output_file.txt'
        view1 = PipelineDevelopperView(pipeline)
        view1.show()
        app.exec_()
        del view1
