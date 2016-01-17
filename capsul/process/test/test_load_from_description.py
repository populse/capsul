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
from capsul.api import Process
from capsul.api import get_process_instance
from capsul.api import Pipeline


def a_function_to_wrap(fname, directory, value, enum, list_of_str):
    """ A dummy fucntion that just print all its parameters.

    <process>
        <return name="string" type="string" doc="test" />
        <input name="fname" type="file" doc="test" />
        <input name="directory" type="directory" doc="test" />
        <input name="value" type="float" doc="test" />
        <input name="enum" type="string" doc="test" />
        <input name="list_of_str" type="list_string" doc="test" />
    </process>
    """
    string = "ALL FUNCTION PARAMETERS::\n\n"
    for input_parameter in (fname, directory, value, enum, list_of_str):
        string += str(input_parameter)
    return string

def to_warp_func(parameter1, parameter2, parameter3):
    """ Test function.

    <process>
        <input name="parameter1" type="float" desc="a parameter."/>
        <input name="parameter2" type="string" desc="a parameter."/>
        <input name="parameter3" type="int" desc="a parameter."/>
        <return>
            <output name="output1" type="float" desc="an output."/>
            <output name="output2" type="string" desc="an output."/>
        </return>
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
        pipeline = get_process_instance("capsul.process.test.xml_pipeline")
        self.assertTrue(isinstance(pipeline, Pipeline))
        for node_name in ["", "p1", "p2"]:
            self.assertTrue(node_name in pipeline.nodes)

class TestProcessWrap(unittest.TestCase):
    """ Class to test the function used to wrap a function to a process
    """
    def setUp(self):
        """ In the setup construct set some process input parameters.
        """
        # Get the wraped test process process
        self.process = get_process_instance(
            "capsul.process.test.test_load_from_description.a_function_to_warp")

        # Set some input parameters
        self.process.fname = "fname"
        self.process.directory = "directory"
        self.process.value = 1.2
        self.process.enum = "choice1"
        self.process.list_of_str = ["a_string"]

    def test_process_wrap(self):
        """ Method to test if the process has been wraped properly.
        """
        # Execute the process
        self.process()
        self.assertEqual(
            getattr(self.process, "string"),
            "ALL FUNCTION PARAMETERS::\n\nfnamedirectory1.2choice1['a_string']")

def test():
    """ Function to execute unitest
    """
    suite1 = unittest.TestLoader().loadTestsFromTestCase(
        TestLoadFromDescription)
    runtime1 = unittest.TextTestRunner(verbosity=2).run(suite1)
    suite2 = unittest.TestLoader().loadTestsFromTestCase(TestProcessWrap)
    runtime2 = unittest.TextTestRunner(verbosity=2).run(suite2)
    return runtime1.wasSuccessful() and runtime2.wasSuccessful()


if __name__ == "__main__":
    test()
