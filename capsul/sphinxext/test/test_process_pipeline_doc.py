# -*- coding: utf-8 -*-
import unittest

# Capsul import
from capsul.api import Process
from capsul.api import Pipeline

# @unittest.skip('reimplementation expected for capsul v3')
# from capsul.sphinxext.pipelinedocgen import PipelineHelpWriter

from soma.controller import File, field


class MyProcess(Process):
    """My dummy process."""

    # Some inputs
    input_image = field(type_=File, optional=False, desc="an image.")
    input_float = field(type_=float, optional=True, desc="a float.")

    # Some outputs
    output_image = field(
        type_=File, optional=False, write=True, desc="an output image."
    )
    output_float = field(type_=float, optional=True, output=True, desc=None)


class MyPipeline(Pipeline):
    """My dummy pipeline with a switch."""

    def pipeline_definition(self):
        """Create a simple pipeline with a switch and some of its output plugs
        exported to the pipeline output.
        """
        # Create processes
        self.add_process(
            "way1", "capsul.sphinxext.test.test_process_pipeline_doc.MyProcess"
        )
        self.add_process(
            "way2", "capsul.sphinxext.test.test_process_pipeline_doc.MyProcess"
        )
        self.add_process(
            "node", "capsul.sphinxext.test.test_process_pipeline_doc.MyProcess"
        )

        # Create Switch
        self.add_switch(
            "switch",
            ["one", "two"],
            [
                "image",
                "float",
            ],
        )

        # Link input
        self.export_parameter("way1", "input_image")
        self.export_parameter("way1", "input_float")

        # Link way1
        self.add_link("way1.output_image->switch.one_switch_image")
        self.add_link("way1.output_float->switch.one_switch_float")

        # Link way2
        self.add_link("input_image->way2.input_image")
        self.add_link("input_float->way2.input_float")
        self.add_link("way2.output_image->switch.two_switch_image")
        self.add_link("way2.output_float->switch.two_switch_float")

        # Link node
        self.add_link("switch.image->node.input_image")
        self.add_link("switch.float->node.input_float")

        # Outputs
        self.export_parameter("node", "output_image", pipeline_parameter="node_image")
        self.export_parameter("node", "output_float", pipeline_parameter="node_float")
        self.export_parameter("switch", "float", pipeline_parameter="switch_float")
        self.export_parameter("way1", "output_image", pipeline_parameter="way1_image")


class TestSphinxExt(unittest.TestCase):
    """Class to test that we can properly generate the process and pipeline
    rst documentation.
    """

    def setUp(self):
        """In the setup construct a process and a pipeline"""
        # Construct the processe and pipeline
        self.process_id = "capsul.sphinxext.test.test_process_pipeline_doc." "MyProcess"
        self.pipeline_id = (
            "capsul.sphinxext.test.test_process_pipeline_doc." "MyPipeline"
        )

    @unittest.skip("reimplementation expected for capsul v3")
    def test_process_doc(self):
        """Method to test the process rst documentation."""
        # Generate the writer object
        docwriter = PipelineHelpWriter([self.process_id])
        rstdoc = docwriter.write_api_docs(returnrst=True)
        self.assertTrue(self.process_id in rstdoc)

    @unittest.skip("reimplementation expected for capsul v3")
    def test_pipeline_doc(self):
        """Method to test the pipeline rst documentation."""
        # Generate the writer object
        docwriter = PipelineHelpWriter([self.pipeline_id])
        rstdoc = docwriter.write_api_docs(returnrst=True)
        self.assertTrue(self.pipeline_id in rstdoc)
