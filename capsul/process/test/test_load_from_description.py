# -*- coding: utf-8 -*-
import unittest
import tempfile
import os
import sys
import shutil
from typing import List, Tuple

from soma.controller import file, directory, field

from capsul.api import Process
from capsul.api import get_process_instance
from capsul.api import Pipeline
from capsul.process.xml import xml_process
from capsul.pipeline.xml import save_xml_pipeline




def a_function_to_wrap(
    fname: file(doc='test'), 
    directory: directory(doc='test'), 
    value: field(type_=float, doc='test'), 
    enum: field(type_=str, doc='test'), 
    list_of_str: field(type_=List[str], doc='test')
) -> field(type_=str, doc='test'):
    """
    A dummy function that just print all its parameters.
    """
    string = "ALL FUNCTION PARAMETERS::\n\n"
    for input_parameter in (fname, directory, value, enum, list_of_str):
        string += str(input_parameter)
    return string


def to_warp_func(
    parameter1: field(type_=float, desc='a parameter'),
    parameter2:  field(type_=str, desc='a parameter'),
    parameter3:  field(type_=int, desc='a parameter'),
) -> Tuple[float, str]:
    """ Test function.
    """
    output1 = 1
    output2 = "done"
    return output1, output2


@xml_process('''
<process>
    <input name="input_image" type="file" doc="Path of a NIFTI-1 image file."/>
    <input name="method" type="enum" values="['gt', 'ge', 'lt', 'le']" 
     doc="Mehod for thresolding."/>
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
    def test_process_warpping(self):
        """ Method to test the function to process on the fly warpping.
        """
        process = get_process_instance(
            "capsul.process.test.test_load_from_description.to_warp_func")
        self.assertTrue(isinstance(process, Process))
        for input_name in ["parameter1", "parameter2", "parameter3"]:
            field = process.field(input_name)
            self.assertTrue(field is not None)
            self.assertFalse(field.metadata.get('output', False))
        for output_name in ["result"]:
            field = process.field(output_name)
            self.assertTrue(field is not None)
            self.assertTrue(field.metadata.get('output', False))
        process.parameter1 = 12.34
        process.parameter2 = 'toto'
        process.parameter3 = 4
        process()
        self.assertEqual(process.result, (1, 'done'))

    def test_pipeline_warpping(self):
        """ Method to test the xml description to pipeline on the fly warpping.
        """
        pipeline = get_process_instance("capsul.process.test.xml_pipeline")
        self.assertTrue(isinstance(pipeline, Pipeline))
        for node_name in ["", "p1", "p2"]:
            self.assertTrue(node_name in pipeline.nodes)

#     def test_pipeline_writing(self):
#         """ Method to test the xml description saving and reloading
#         """
#         # get a pipeline
#         pipeline1 = get_process_instance("capsul.process.test.xml_pipeline")
#         # save it in a temp directory
#         tmpdir = tempfile.mkdtemp()
#         pdir = os.path.join(tmpdir, "pipeline_mod")
#         os.mkdir(pdir)
#         save_xml_pipeline(pipeline1, os.path.join(pdir, "test_pipeline.xml"))
#         # make this dir become a python module
#         with open(os.path.join(pdir, "__init__.py"), "w"):
#             pass
#         # point the path to it
#         sys.path.append(tmpdir)
#         # reload the saved pipeline
#         pipeline2 = get_process_instance("pipeline_mod.test_pipeline")
#         self.assertEqual(sorted(pipeline1.nodes.keys()),
#                          sorted(pipeline2.nodes.keys()))
#         for node_name, node1 in six.iteritems(pipeline1.nodes):
#             node2 = pipeline2.nodes[node_name]
#             self.assertEqual(node1.enabled, node2.enabled)
#             self.assertEqual(node1.activated, node2.activated)
#             self.assertEqual(sorted(node1.plugs.keys()),
#                              sorted(node2.plugs.keys()))
#             for plug_name, plug1 in six.iteritems(node1.plugs):
#                 plug2 = node2.plugs[plug_name]
#                 self.assertEqual(len(plug1.links_from),
#                                  len(plug2.links_from))
#                 self.assertEqual(len(plug1.links_to),
#                                  len(plug2.links_to))
#                 links1 = [l[:2] + (l[4],)
#                           for l in sorted(plug1.links_from)
#                               + sorted(plug1.links_to)]
#                 links2 = [l[:2] + (l[4],)
#                           for l in sorted(plug2.links_from)
#                               + sorted(plug2.links_to)]
#                 self.assertEqual(links1, links2)
#         sys.path.pop(-1)
#         shutil.rmtree(tmpdir)

#     def test_return_string(self):
#         process = get_process_instance(
#             "capsul.process.test.test_load_from_description.cat")
#         process(value1="a", value2="b", value3="c")
#         self.assertEqual(process.values, "a_b_c")
#         process(value1="", value2="v", value3="")
#         self.assertEqual(process.values, "v")
        
#     def test_return_list(self):
#         process = get_process_instance(
#             "capsul.process.test.test_load_from_description.join")
#         process(value1="a", value2="b", value3="c")
#         self.assertEqual(process.values, ["a", "b", "c"])
#         process(value1="", value2="v", value3="")
#         self.assertEqual(process.values, ["v"])

#     def test_named_outputs(self):
#         process = get_process_instance(
#             "capsul.process.test.test_load_from_description.divide_dict")
#         print('!!!', process, type(process))
#         process(a=42, b=3)
#         self.assertEqual(process.quotient, 14)
#         self.assertEqual(process.remainder, 0)
#         process = get_process_instance(
#             "capsul.process.test.test_load_from_description.divide_list")
#         process(a=42, b=3)
#         self.assertEqual(process.quotient, 14)
#         self.assertEqual(process.remainder, 0)
        
#         a = list(range(40, 50))
#         b = list(range(10, 21))
#         quotients = [int(i / j) for i, j in zip(list(range(40, 50)), list(range(10, 21)))]
#         remainders = [i % j for i, j in zip(list(range(40, 50)), list(range(10, 21)))]
        
#         process = get_process_instance(
#             "capsul.process.test.test_load_from_description.divides_dict")
#         process(a=a, b=b)
#         self.assertEqual(process.quotients, quotients)
#         self.assertEqual(process.remainders, remainders)
#         process = get_process_instance(
#             "capsul.process.test.test_load_from_description.divides_list")
#         process(a=a, b=b)
#         self.assertEqual(process.quotients, quotients)
#         self.assertEqual(process.remainders, remainders)
        
#         process = get_process_instance(
#             "capsul.process.test.test_load_from_description.divides_single_dict")
#         process(a=a, b=b)
#         self.assertEqual(process.quotients, quotients)
#         process = get_process_instance(
#             "capsul.process.test.test_load_from_description.divides_single_list")
#         process(a=a, b=b)
#         self.assertEqual(process.quotients, quotients)
        
# class TestProcessWrap(unittest.TestCase):
#     """ Class to test the function used to wrap a function to a process
#     """
#     def setUp(self):
#         """ In the setup construct set some process input parameters.
#         """
#         # Get the wrapped test process process
#         self.process = get_process_instance(
#             "capsul.process.test.test_load_from_description.a_function_to_wrap")

#         # Set some input parameters
#         self.process.fname = "fname"
#         self.process.directory = "directory"
#         self.process.value = 1.2
#         self.process.enum = "choice1"
#         self.process.list_of_str = ["a_string"]

#     def test_process_wrap(self):
#         """ Method to test if the process has been wrapped properly.
#         """
#         # Execute the process
#         self.process()
#         self.assertEqual(
#             getattr(self.process, "string"),
#             "ALL FUNCTION PARAMETERS::\n\nfnamedirectory1.2choice1['a_string']")


if __name__ == "__main__":
    unittest.main()
