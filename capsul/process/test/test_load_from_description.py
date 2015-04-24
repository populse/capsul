#! /usr/bin/env python
##########################################################################
# Capsul - Copyright (C) CEA, 2014
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import unittest

# Capsul import
from capsul.process import Process
from capsul.process.loader import get_process_instance
from capsul.pipeline import Pipeline


def to_warp_func(parameter1, parameter2, parameter3):
    """ Test function.

    <process>
        <return name="output1" type="Float" desc="an output."/>
        <return name="output2" type="String" desc="an output."/>
        <input name="parameter1" type="Float" desc="a parameter."/>
        <input name="parameter2" type="String" desc="a parameter."/>
        <input name="parameter3" type="Int" desc="a parameter."/>
    </process>
    """
    output1 = 1
    output2 = "done"
    return output1, output2


class TestLoadFromDescription(unittest.TestCase):
    """ Class to test function to process loading mechanism.
    """
    def test_process_warpping(self):
        """ Method to test the function to process on the fly warpping.
        """
        process = get_process_instance(
            "capsul.process.test.test_load_from_description.to_warp_func")
        self.assertTrue(isinstance(process, Process))
        for input_name in ["parameter1", "parameter2", "parameter3"]:
            self.assertTrue(input_name in process.traits(output=False))
        for output_name in ["output1", "output2"]:
            self.assertTrue(output_name in process.traits(output=True))
        process()
        self.assertEqual(process.output1, 1)
        self.assertEqual(process.output2, "done")

    def test_pipeline_warpping(self):
        """ Method to test the xml description to pipeline on the fly warpping.
        """
        pipeline = get_process_instance("capsul.utils.test.xml_pipeline.xml")
        self.assertTrue(isinstance(pipeline, Pipeline))
        for node_name in ["", "p1", "p2"]:
            self.assertTrue(node_name in pipeline.nodes)


def test():
    """ Function to execute unitest
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(
        TestLoadFromDescription)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    test()
