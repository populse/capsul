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
from capsul.utils.trait_utils import is_trait_value_defined


def to_warp_func(parameter1, parameter2, parameter3=5):
    """ Test function.

    <unit>
        <input name="parameter2" type="String" description="a parameter."/>
        <output name="output1" type="Float" description="an output."/>
        <input name="parameter1" type="List" content="Float" description="a parameter."/>
        <input name="parameter3" type="Float" description="a parameter."/>
        <output name="output2" type="String" description="an output."/>
    </unit>
    """
    output1 = parameter1[0] * parameter3
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
        process.parameter1 = [2.5]
        process.parameter2 = "test"
        self.assertEqual(process.parameter3, 5)
        process()
        self.assertEqual(process.output1, 12.5)
        self.assertEqual(process.output2, "done")

    def test_pipeline_warpping(self):
        """ Method to test the xml description to pipeline on the fly warpping.
        """
        print

        pipeline = get_process_instance("capsul.demo.pipeline.xml")
        self.assertTrue(isinstance(pipeline, Pipeline))
        for node_name in ["", "p1", "p2"]:
            self.assertTrue(node_name in pipeline.nodes)
        pipeline.input1 = [2.5]
        pipeline()
        self.assertEqual(pipeline.output1, 12.5)
        self.assertEqual(pipeline.output2, 31.25)
        self.assertEqual(pipeline.output3, "done")

        pipeline = get_process_instance("capsul.demo.switch_pipeline.xml")
        self.assertTrue(isinstance(pipeline, Pipeline))
        for node_name in ["", "p1", "p2", "p3", "p4", "p5"]:
            self.assertTrue(node_name in pipeline.nodes)
        pipeline.input1 = [2.5]
        pipeline.switch = "path2"
        pipeline()
        if pipeline.switch == "path3":
            self.assertEqual(pipeline.output, 31.25)
        elif pipeline.switch == "path2":
            self.assertEqual(pipeline.output, 78.125)
        elif pipeline.switch == "path1":
            self.assertEqual(pipeline.output, 195.3125)
        if pipeline.switch == "path3":
            self.assertFalse(is_trait_value_defined(pipeline.output2))
        else:
            self.assertEqual(pipeline.output2, "done")

        graph, inlinkreps, outlinkreps = pipeline._create_graph(
            pipeline, filter_inactive=True)
        ordered_boxes = [item[0] for item in graph.topological_sort()]
        if pipeline.switch == "path3":
            self.assertEqual(ordered_boxes, ["p1", "p5"])
        elif pipeline.switch == "path2":
            self.assertEqual(ordered_boxes, ["p1", "p4", "p5"])
        elif pipeline.switch == "path1":
            self.assertEqual(ordered_boxes, ["p1", "p2", "p3", "p5"])
            
        if 0:
            from PySide import QtGui
            import sys
            from capsul.qt_gui.widgets import PipelineDevelopperView

            app = QtGui.QApplication(sys.argv)
            view1 = PipelineDevelopperView(pipeline)
            view1.show()
            app.exec_()

    def test_sub_pipeline_warpping(self):
        """ Method to test the xml description to pipeline on the fly warpping.
        """
        print

        pipeline = get_process_instance("capsul.demo.sub_pipeline.xml")
        self.assertTrue(isinstance(pipeline, Pipeline))
        for node_name in ["", "p1", "p2", "p3"]:
            self.assertTrue(node_name in pipeline.nodes)

        pipeline.input1 = [2.5]
        pipeline.switch = "path2"
        pipeline()
        if pipeline.switch == "path2":
            self.assertEqual(pipeline.output, 195.3125)
        else:
            self.assertEqual(pipeline.output, 488.28125)

        graph, inlinkreps, outlinkreps = pipeline._create_graph(
            pipeline, filter_inactive=True)
        ordered_boxes = [item[0] for item in graph.topological_sort()]
        if pipeline.switch == "path2":
            self.assertEqual(ordered_boxes,
                             ["p1", "p2.p1", "p2.p4", "p2.p5", "p3"])
        else:
            self.assertEqual(ordered_boxes,
                             ["p1", "p2.p1", "p2.p2", "p2.p3", "p2.p5", "p3"])

        if 0:
            from PySide import QtGui
            import sys
            from capsul.qt_gui.widgets import PipelineDevelopperView

            app = QtGui.QApplication(sys.argv)
            view1 = PipelineDevelopperView(pipeline)
            view1.show()
            app.exec_()
            



def test():
    """ Function to execute unitest
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(
        TestLoadFromDescription)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    test()
