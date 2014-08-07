#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################


# System import
import sys
import unittest

# Trait import
from traits.api import String, Float

# Capsul import
from capsul.process import Process
from capsul.pipeline import Pipeline


class DummyProcess(Process):
    """ Dummy Test Process
    """
    def __init__(self):
        """Initialize the DummyProcess.
        """
        # Inheritance
        super(DummyProcess, self).__init__()

        # Inputs
        self.add_trait("input_image", String(optional=False, output=False))
        self.add_trait("other_input", Float(optional=False, output=False))
        self.add_trait("dynamic_parameter", Float(optional=False, output=False))
        
        # Outputs
        self.add_trait("output_image", String(optional=False, output=True))

        # Set default parameter
        self.other_input = 5

    def _run_process(self):
        """ Execute the process.
        """
        # Just join the input values
        value = "{0}:{1}:{2}".format(
            self.input_image, self.other_input, self.dynamic_parameter)
        self.output_image = value


class MyPipeline(Pipeline):
    """ Simple Pipeline to test the iterative Node
    """
    def pipeline_definition(self):
        """ Define the pipeline.
        """
        # Create an iterative processe
        self.add_iterative_process(
            "iterative", "capsul.pipeline.test.test_iterative_process.DummyProcess",
            iterative_plugs=["input_image", "output_image", "dynamic_parameter"])

        # Set the pipeline view scale factor
        self.scene_scale_factor = 1.0


class TestPipeline(unittest.TestCase):
    """ Class to test a pipeline with an iterative node
    """
    def setUp(self):
        """ In the setup construct the pipeline and set some input parameters.
        """
        # Construct the pipeline
        self.pipeline = MyPipeline()

        # Set some input parameters
        # self.pipeline.other_input = 5
        self.pipeline.input_image = ["toto", "tutu"]
        self.pipeline.dynamic_parameter = [3, 1]

    def test_iterative_pipeline_connection(self):
        """ Method to test if an iterative node and built in iterative
        process are correctly connected.
        """

        # Test the input connection
        iterative_node = self.pipeline.nodes["iterative"]
        iterative_pipeline = iterative_node.process
        pipeline_node = iterative_pipeline.nodes[""]
        for trait_name in iterative_node.input_iterative_traits:
            self.assertEqual(getattr(pipeline_node.process, trait_name),
                             getattr(self.pipeline, trait_name))
        for trait_name in iterative_node.input_traits:
            self.assertEqual(getattr(pipeline_node.process, trait_name),
                             getattr(self.pipeline, trait_name))

        # Test the output connection
        self.pipeline()
        if sys.version_info >= (2, 7):
            self.assertIn("toto:5.0:3.0", iterative_pipeline.output_image)
            self.assertIn("tutu:5.0:1.0", iterative_pipeline.output_image)
        else:
            self.assertTrue("toto:5.0:3.0" in iterative_pipeline.output_image)
            self.assertTrue("tutu:5.0:1.0" in iterative_pipeline.output_image)
        self.assertEqual(
            self.pipeline.output_image,iterative_pipeline.output_image)


def test():
    """ Function to execute unitest
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPipeline)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    test()

    from PySide import QtGui
    from capsul.apps_qt.base.pipeline_widgets import PipelineDevelopperView

    app = QtGui.QApplication(sys.argv)
    pipeline = MyPipeline()
    pipeline.input_image = ["toto", "tutu", "titi"]
    pipeline.dynamic_parameter = [3, 1, 4]
    pipeline.other_input = 0
    pipeline = pipeline.nodes["iterative"].process
    pipeline.scene_scale_factor = 0.4
    view1 = PipelineDevelopperView(pipeline)
    view1.show()
    app.exec_()
    del view1
