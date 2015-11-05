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
import re

# Trait import
from traits.api import String, Float

# Capsul import
from capsul.process import Process
from capsul.pipeline import Pipeline
from capsul.pipeline import pipeline_workflow


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
        self.add_trait("dynamic_parameter",
                       Float(optional=False, output=False))

        # Outputs
        self.add_trait("output_image", String(optional=False, output=True))
        self.add_trait("other_output", Float(optional=False, output=True))

        # Set default parameter
        self.other_input = 6

    def _run_process(self):
        """ Execute the process.
        """
        # Just join the input values
        value = "{0}:{1}:{2}".format(
            self.input_image, self.other_input, self.dynamic_parameter)
        self.output_image = value
        self.other_output = self.other_input


class MyPipeline(Pipeline):
    """ Simple Pipeline to test the iterative Node
    """
    def pipeline_definition(self):
        """ Define the pipeline.
        """
        # Create an iterative processe
        self.add_iterative_process(
            "iterative",
            "capsul.pipeline.test.test_iterative_process.DummyProcess",
            iterative_plugs=[
                "input_image", "output_image", "dynamic_parameter",
                "other_output"])

        # Set the pipeline view scale factor
        self.scene_scale_factor = 1.0


class MyBigPipeline(Pipeline):
    '''bigger pipeline with several levels'''
    def pipeline_definition(self):
        self.add_iterative_process(
            "main_level",
            "capsul.pipeline.test.test_iterative_process.MyPipeline",
            iterative_plugs=[
                "input_image", "output_image", "dynamic_parameter",
                "other_output"])


class TestPipeline(unittest.TestCase):
    """ Class to test a pipeline with an iterative node
    """
    def setUp(self):
        """ In the setup construct the pipeline and set some input parameters.
        """
        # Construct the pipeline
        self.pipeline = MyPipeline()

        # Set some input parameters
        self.pipeline.input_image = ["toto", "tutu"]
        self.pipeline.dynamic_parameter = [3, 1]
        self.pipeline.other_input = 5

        # build a bigger pipeline with several levels
        self.big_pipeline = MyBigPipeline()

    def test_iterative_pipeline_connection(self):
        """ Method to test if an iterative process work correctly
        """

        # Test the output connection
        self.pipeline()
        
        if sys.version_info >= (2, 7):
            self.assertIn("toto:5.0:3.0", self.pipeline.output_image)
            self.assertIn("tutu:5.0:1.0", self.pipeline.output_image)
        else:
            self.assertTrue("toto:5.0:3.0" in self.pipeline.output_image)
            self.assertTrue("tutu:5.0:1.0" in self.pipeline.output_image)
        self.assertEqual(self.pipeline.other_output, 
                         [self.pipeline.other_input,
                          self.pipeline.other_input])

    def test_iterative_pipeline_workflow(self):
        self.pipeline.output_image = ['/tmp/toto_out', '/tmp/tutu_out']
        self.pipeline.other_output = [1., 2.]
        workflow = pipeline_workflow.workflow_from_pipeline(self.pipeline)
        self.assertTrue(len(workflow.jobs) == 2)

    def test_iterative_big_pipeline_workflow(self):
        self.big_pipeline.input_image = [["toto", "tutu"],
                                         ["tata", "titi", "tete"]]
        self.big_pipeline.dynamic_parameter = [[1, 2], [3, 4, 5]]
        self.big_pipeline.other_input = 5
        self.big_pipeline.output_image = [['/tmp/toto_out', '/tmp/tutu_out'],
                                          ['/tmp/tata_out', '/tmp/titi_out',
                                           '/tmp/tete_out']]
        self.big_pipeline.other_output = [[1.1, 2.1], [3.1, 4.1, 5.1]]
        workflow = pipeline_workflow.workflow_from_pipeline(self.big_pipeline)
        self.assertTrue(len(workflow.jobs) == 5)
        subjects = set()
        for job in workflow.jobs:
            kwargs = eval(re.match('^.*kwargs=({.*}); kwargs.update.*$',
                                   job.command[2]).group(1))
            self.assertEqual(kwargs["other_input"], 5)
            subjects.add(kwargs["input_image"])
            if sys.version_info >= (2, 7):
                self.assertIn(kwargs["input_image"],
                              ["toto", "tutu", "tata", "titi", "tete"])
            else:
                self.assertTrue(kwargs["input_image"] in
                                ["toto", "tutu", "tata", "titi", "tete"])
        self.assertEqual(subjects,
                         set(["toto", "tutu", "tata", "titi", "tete"]))


def test():
    """ Function to execute unitest
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPipeline)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    test()

    if 1:
        from soma.qt_gui.qt_backend import QtGui
        from capsul.qt_gui.widgets import PipelineDevelopperView

        app = QtGui.QApplication(sys.argv)
        pipeline = MyPipeline()
        pipeline.input_image = ["toto", "tutu", "titi"]
        pipeline.dynamic_parameter = [3, 1, 4]
        pipeline.other_input = 0
        pipeline2 = pipeline.nodes["iterative"].process
        pipeline2.scene_scale_factor = 0.5
        pipeline.node_position = {'inputs': (50.0, 50.0),
                                  'iterative': (267.0, 56.0),
                                  'outputs': (1124.0, 96.0)}

        view1 = PipelineDevelopperView(pipeline, show_sub_pipelines=True,
                                       allow_open_controller=True)
        view1.add_embedded_subpipeline('iterative')

        view1.show()
        app.exec_()
        del view1
