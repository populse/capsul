#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

import unittest
from traits.api import File, Float
from capsul.process import Process
from capsul.pipeline import Pipeline


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

    def __call__(self):
        pass


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
        self.export_parameter("node2", "output_image")
        self.export_parameter("node2", "other_output")


class TestPipeline(unittest.TestCase):

    def setUp(self):
        self.pipeline = MyPipeline()

    def test_constant(self):
        self.pipeline.workflow_ordered_nodes()
        self.assertEqual(self.pipeline.workflow_repr,
                         "constant->node1->node2")

    def test_enabled(self):
        setattr(self.pipeline.nodes_activation, "node2", False)
        self.pipeline.workflow_ordered_nodes()
        self.assertEqual(self.pipeline.workflow_repr, "")


def test():
    """ Function to execute unitest
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPipeline)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    print "RETURNCODE: ", test()

    import sys
    from PySide import QtGui
    from capsul.apps_qt.base.pipeline_widgets import PipelineDevelopperView

    app = QtGui.QApplication(sys.argv)
    pipeline = MyPipeline()
    setattr(pipeline.nodes_activation, "node2", False)
    view1 = PipelineDevelopperView(pipeline)
    view1.show()
    app.exec_()
    del view1
