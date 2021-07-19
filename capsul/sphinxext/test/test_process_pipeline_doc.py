# -*- coding: utf-8 -*-
##########################################################################
# Capsul - Copyright (C) CEA, 2014
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
from __future__ import absolute_import
import unittest

# Capsul import
from capsul.api import Process
from capsul.api import Pipeline
from capsul.sphinxext.pipelinedocgen import PipelineHelpWriter

# Trait import
from traits.api import Float, File


class MyProcess(Process):
    """ My dummy process.
    """
    # Some inputs
    input_image = File(optional=False, desc="an image.")
    input_float = Float(optional=True, desc="a float.")

    # Some outputs
    output_image = File(optional=False, output=True, desc="an output image.")
    output_float = Float(optional=True, output=True, desc=None)


class MyPipeline(Pipeline):
    """ My dummy pipeline with a switch.
    """
    def pipeline_definition(self):
        """ Create a simple pipeline with a switch and some of its output plugs
        exported to the pipeline output.
        """
        # Create processes
        self.add_process(
            "way1",
            "capsul.sphinxext.test.test_process_pipeline_doc.MyProcess")
        self.add_process(
            "way2",
            "capsul.sphinxext.test.test_process_pipeline_doc.MyProcess")
        self.add_process(
            "node",
            "capsul.sphinxext.test.test_process_pipeline_doc.MyProcess")

        # Create Switch
        self.add_switch("switch", ["one", "two"],
                        ["image", "float", ])

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
        self.export_parameter("node", "output_image",
                              pipeline_parameter="node_image")
        self.export_parameter("node", "output_float",
                              pipeline_parameter="node_float")
        self.export_parameter("switch", "float",
                              pipeline_parameter="switch_float")
        self.export_parameter("way1", "output_image",
                              pipeline_parameter="way1_image")


class TestSphinxExt(unittest.TestCase):
    """ Class to test that we can properly generate the process and pipeline
    rst documentation.
    """
    def setUp(self):
        """ In the setup construct a process and a pipeline
        """
        # Construct the processe and pipeline
        self.process_id = ("capsul.sphinxext.test.test_process_pipeline_doc."
                           "MyProcess")
        self.pipeline_id = ("capsul.sphinxext.test.test_process_pipeline_doc."
                            "MyPipeline")

    def test_process_doc(self):
        """ Method to test the process rst documentation.
        """
        # Generate the writer object
        docwriter = PipelineHelpWriter([self.process_id])
        rstdoc = docwriter.write_api_docs(returnrst=True)
        self.assertTrue(self.process_id in rstdoc)

    def test_pipeline_doc(self):
        """ Method to test the pipeline rst documentation.
        """
        # Generate the writer object
        docwriter = PipelineHelpWriter([self.pipeline_id])
        rstdoc = docwriter.write_api_docs(returnrst=True)
        self.assertTrue(self.pipeline_id in rstdoc)


def test():
    """ Function to execute unitest
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSphinxExt)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    test() 
