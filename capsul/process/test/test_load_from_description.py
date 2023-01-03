# -*- coding: utf-8 -*-
# System import
from __future__ import print_function
from __future__ import absolute_import

import unittest
import tempfile
import os
import sys
import shutil
import six

# Capsul import
from capsul.api import Process
from capsul.api import get_process_instance
from capsul.api import Pipeline
from capsul.process.xml import xml_process
from capsul.pipeline.xml import save_xml_pipeline
from six.moves import range
from six.moves import zip


def a_function_to_wrap(fname, directory, value, enum, list_of_str):
    """ A dummy function that just print all its parameters.

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


@xml_process('''
<process>
    <input name="input_image" type="file" doc="Path of a NIFTI-1 image file."/>
    <input name="method" type="enum" values="['gt', 'ge', 'lt', 'le']" 
     doc="Method for thresolding."/>
    <input name="threshold" type="float" doc="Threshold value."/>
    <return name="output_image" type="file" doc="Name of the output image."/>
</process>
''')
def threshold(input_image, output_image, method='gt', threshold=0):
     pass

@xml_process('''
<process>
    <input name="input_image" type="file" doc="Path of a NIFTI-1 image file."/>
    <input name="mask" type="file" doc="Path of mask binary image."/>
    <output name="output_image" type="file" doc="Output file name."/>
</process>
''')
def mask(input_image, mask, output_location=None):
     pass


@xml_process('''
<process>
    <input name="value1" type="string" doc="A string value."/>
    <input name="value2" type="string" doc="A string value."/>
    <input name="value3" type="string" doc="A string value."/>
    <return name="values" type="string" doc="Concatenation of non empty input values."/>
</process>
''')
def cat(value1, value2, value3):
     return '_'.join(i for i in (value1, value2, value3) if i)

@xml_process('''
<process>
    <input name="value1" type="string" doc="A string value."/>
    <input name="value2" type="string" doc="A string value."/>
    <input name="value3" type="string" doc="A string value."/>
    <return name="values" type="list_string" doc="List of non empty input values."/>
</process>
''')
def join(value1, value2, value3):
     return [i for i in (value1, value2, value3) if i]


@xml_process('''
<process capsul_xml="2.0">
    <input name="a" type="int" doc="An integer"/>
    <input name="b" type="int" doc="Another integer"/>
    <return>
        <output name="quotient" type="int" doc="Quotient of a / b"/>
        <output name="remainder" type="int" doc="Remainder of a / b"/>
    </return>
</process>
''')
def divide_dict(a, b):
     return {
        'quotient': int(a / b),
        'remainder': a % b,
    }

@xml_process('''
<process capsul_xml="2.0">
    <input name="a" type="int" doc="An integer"/>
    <input name="b" type="int" doc="Another integer"/>
    <return>
        <output name="quotient" type="int" doc="Quotient of a / b"/>
        <output name="remainder" type="int" doc="Remainder of a / b"/>
    </return>
</process>
''')
def divide_list(a, b):
     return [int(a / b), a % b]

@xml_process('''
<process capsul_xml="2.0">
    <input name="a" type="list_int" doc="An integers list"/>
    <input name="b" type="list_int" doc="Another integers list"/>
    <return>
        <output name="quotients" type="list_int" doc="Quotients of a / b"/>
        <output name="remainders" type="list_int" doc="Remainders of a / b"/>
    </return>
</process>
''')
def divides_dict(a, b):
     return {
        'quotients': [int(i / j) for i, j in zip(a, b)],
        'remainders': [i % j for i, j in zip(a, b)],
    }
 
@xml_process('''
<process capsul_xml="2.0">
    <input name="a" type="list_int" doc="An integers list"/>
    <input name="b" type="list_int" doc="Another integers list"/>
    <return>
        <output name="quotients" type="list_int" doc="Quotients of a / b"/>
        <output name="remainders" type="list_int" doc="Remainders of a / b"/>
    </return>
</process>
''')
def divides_list(a, b):
     return [[int(i / j) for i, j in zip(a, b)],
             [i % j for i, j in zip(a, b)]]
 
 
@xml_process('''
<process capsul_xml="2.0">
    <input name="a" type="list_int" doc="An integers list"/>
    <input name="b" type="list_int" doc="Another integers list"/>
    <return>
        <output name="quotients" type="list_int" doc="Quotients of a / b"/>
    </return>
</process>
''')
def divides_single_dict(a, b):
     return {
        'quotients': [int(i / j) for i, j in zip(a, b)],
    }

@xml_process('''
<process capsul_xml="2.0">
    <input name="a" type="list_int" doc="An integers list"/>
    <input name="b" type="list_int" doc="Another integers list"/>
    <return>
        <output name="quotients" type="list_int" doc="Quotients of a / b"/>
    </return>
</process>
''')
def divides_single_list(a, b):
     return [[int(i / j) for i, j in zip(a, b)]]


class TestLoadFromDescription(unittest.TestCase):
    """ Class to test function to process loading mechanism.
    """
    def test_process_warping(self):
        """ Method to test the function to process on the fly warping.
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

    def test_pipeline_warping(self):
        """ Method to test the xml description to pipeline on the fly warping.
        """
        pipeline = get_process_instance("capsul.process.test.xml_pipeline")
        self.assertTrue(isinstance(pipeline, Pipeline))
        for node_name in ["", "p1", "p2"]:
            self.assertTrue(node_name in pipeline.nodes)

    def test_pipeline_writing(self):
        """ Method to test the xml description saving and reloading
        """
        # get a pipeline
        pipeline1 = get_process_instance("capsul.process.test.xml_pipeline")
        # save it in a temp directory
        tmpdir = tempfile.mkdtemp()
        pdir = os.path.join(tmpdir, "pipeline_mod")
        os.mkdir(pdir)
        save_xml_pipeline(pipeline1, os.path.join(pdir, "test_pipeline.xml"))
        # make this dir become a python module
        with open(os.path.join(pdir, "__init__.py"), "w"):
            pass
        # point the path to it
        sys.path.append(tmpdir)
        # reload the saved pipeline
        pipeline2 = get_process_instance("pipeline_mod.test_pipeline")
        self.assertEqual(sorted(pipeline1.nodes.keys()),
                         sorted(pipeline2.nodes.keys()))
        for node_name, node1 in six.iteritems(pipeline1.nodes):
            node2 = pipeline2.nodes[node_name]
            self.assertEqual(node1.enabled, node2.enabled)
            self.assertEqual(node1.activated, node2.activated)
            self.assertEqual(sorted(node1.plugs.keys()),
                             sorted(node2.plugs.keys()))
            for plug_name, plug1 in six.iteritems(node1.plugs):
                plug2 = node2.plugs[plug_name]
                self.assertEqual(len(plug1.links_from),
                                 len(plug2.links_from))
                self.assertEqual(len(plug1.links_to),
                                 len(plug2.links_to))
                links1 = [l[:2] + (l[4],)
                          for l in sorted(plug1.links_from)
                              + sorted(plug1.links_to)]
                links2 = [l[:2] + (l[4],)
                          for l in sorted(plug2.links_from)
                              + sorted(plug2.links_to)]
                self.assertEqual(links1, links2)
        sys.path.pop(-1)
        shutil.rmtree(tmpdir)

    def test_return_string(self):
        process = get_process_instance(
            "capsul.process.test.test_load_from_description.cat")
        process(value1="a", value2="b", value3="c")
        self.assertEqual(process.values, "a_b_c")
        process(value1="", value2="v", value3="")
        self.assertEqual(process.values, "v")
        
    def test_return_list(self):
        process = get_process_instance(
            "capsul.process.test.test_load_from_description.join")
        process(value1="a", value2="b", value3="c")
        self.assertEqual(process.values, ["a", "b", "c"])
        process(value1="", value2="v", value3="")
        self.assertEqual(process.values, ["v"])

    def test_named_outputs(self):
        process = get_process_instance(
            "capsul.process.test.test_load_from_description.divide_dict")
        process(a=42, b=3)
        self.assertEqual(process.quotient, 14)
        self.assertEqual(process.remainder, 0)
        process = get_process_instance(
            "capsul.process.test.test_load_from_description.divide_list")
        process(a=42, b=3)
        self.assertEqual(process.quotient, 14)
        self.assertEqual(process.remainder, 0)
        
        a = list(range(40, 50))
        b = list(range(10, 21))
        quotients = [int(i / j) for i, j in zip(list(range(40, 50)), list(range(10, 21)))]
        remainders = [i % j for i, j in zip(list(range(40, 50)), list(range(10, 21)))]
        
        process = get_process_instance(
            "capsul.process.test.test_load_from_description.divides_dict")
        process(a=a, b=b)
        self.assertEqual(process.quotients, quotients)
        self.assertEqual(process.remainders, remainders)
        process = get_process_instance(
            "capsul.process.test.test_load_from_description.divides_list")
        process(a=a, b=b)
        self.assertEqual(process.quotients, quotients)
        self.assertEqual(process.remainders, remainders)
        
        process = get_process_instance(
            "capsul.process.test.test_load_from_description.divides_single_dict")
        process(a=a, b=b)
        self.assertEqual(process.quotients, quotients)
        process = get_process_instance(
            "capsul.process.test.test_load_from_description.divides_single_list")
        process(a=a, b=b)
        self.assertEqual(process.quotients, quotients)
        
class TestProcessWrap(unittest.TestCase):
    """ Class to test the function used to wrap a function to a process
    """
    def setUp(self):
        """ In the setup construct set some process input parameters.
        """
        # Get the wrapped test process process
        self.process = get_process_instance(
            "capsul.process.test.test_load_from_description.a_function_to_wrap")

        # Set some input parameters
        self.process.fname = "fname"
        self.process.directory = "directory"
        self.process.value = 1.2
        self.process.enum = "choice1"
        self.process.list_of_str = ["a_string"]

    def test_process_wrap(self):
        """ Method to test if the process has been wrapped properly.
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
    print("RETURNCODE: ", test())

    if True:
        from soma.qt_gui.qt_backend import QtGui
        from capsul.qt_gui.widgets import PipelineDeveloperView

        app = QtGui.QApplication(sys.argv)
        pipeline = get_process_instance('capsul.process.test.test_pipeline')
        view1 = PipelineDeveloperView(pipeline, show_sub_pipelines=True,
                                       allow_open_controller=True)
        view1.show()
        app.exec_()
        del view1
