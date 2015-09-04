#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import unittest
import os
import numpy

# Casper import
from capsul.process import IProcess
from capsul.pipeline import Pipeline
from capsul.process.loader import get_process_instance

# Trait import
from traits.api import List


class TestIProcess(unittest.TestCase):
    """ Test the iterative box creation.
    """

    def setUp(self):
        """ Initialize the TestObservable class.
        """
        self.myfuncdesc = "capsul.process.test.test_load_from_description.to_warp_func"
        self.mypipedesc = "capsul.utils.test.pipeline.xml"

    def test_iprocess(self):
        """ Method to test if an iprocess is properly created.
        """
        # Return to new line
        print

        # Create a bbox
        process = get_process_instance(self.myfuncdesc)

        # Test raises
        self.assertRaises(ValueError, IProcess, process, iterinputs=["bad"])
        self.assertRaises(ValueError, IProcess, process, iteroutputs=["bad"])

        # Create the box
        self.myiprocess = IProcess(process, iterinputs=["parameter2"],
                                   iteroutputs=["output1"])
        iterprefix = self.myiprocess.iterprefix

        # Test parameters
        self.assertEqual(
            sorted(self.myiprocess.traits(output=False).keys()), sorted([
                iterprefix + name
                for name in self.myiprocess.iterbox.traits(output=False)
                if name in self.myiprocess.iterinputs] + [
                name for name in self.myiprocess.iterbox.traits(output=False)
                if name not in self.myiprocess.iterinputs]))
        self.assertEqual(
            sorted(self.myiprocess.traits(output=True).keys()), sorted([
                iterprefix + name
                for name in self.myiprocess.iterbox.traits(output=True)
                if name in self.myiprocess.iteroutputs] + [
                name for name in self.myiprocess.iterbox.traits(output=True)
                if name not in self.myiprocess.iteroutputs]))
        self.assertTrue(
            numpy.asarray([
                isinstance(self.myiprocess.trait(name), List)
                for name in self.myiprocess.traits(output=False)
                if name in self.myiprocess.iterinputs]).all())
        self.assertTrue(
            numpy.asarray([
                isinstance(self.myiprocess.trait(name), List)
                for name in self.myiprocess.traits(output=True)
                if name in self.myiprocess.iteroutputs]).all())

        # Set parameters
        self.myiprocess.iterparameter2 = ["a", "b"]
        self.myiprocess.parameter1 = [2.5]
        self.assertEqual(self.myiprocess.iterparameter2, ["a", "b"])
        self.assertEqual(self.myiprocess.parameter1, [2.5])

        # Get iterative execution graph
        itergraphs = self.myiprocess.itergraphs()
        for cnt, value in enumerate(self.myiprocess.iterparameter2):
            key = IProcess.itersep + str(cnt)
            graph, process = itergraphs[key]
            self.assertEqual(process.parameter1, [2.5])
            self.assertEqual(process.parameter2, value)
            self.assertEqual(process.parameter3, 5)

        if 0:
            from PySide import QtGui
            import sys
            from capsul.qt_gui.widgets import PipelineDevelopperView

            app = QtGui.QApplication(sys.argv)
            view1 = PipelineDevelopperView(self.myiprocess)
            view1.show()
            app.exec_()

    def test_xml_iprocess(self):
        """ Method to test the xml description to pipeline on the fly warpping.
        """
        # Return to new line
        print

        # Test iterative pipeline creation
        pipeline = get_process_instance("capsul.demo.iter_pipeline.xml")
        self.assertTrue(isinstance(pipeline, Pipeline))
        for node_name in ["", "p1", "p2", "p3"]:
            self.assertTrue(node_name in pipeline.nodes)

        # Parametrize
        pipeline.input1 = [[2.5], [1.5]]
        pipeline.input2 = ["a", "b"]
        pipeline.constant = 2

        # Test graph structure
        graph, inlinkreps, outlinkreps = pipeline._create_graph(
            pipeline, filter_inactive=True)
        ordered_boxes = [item[0] for item in graph.topological_sort()]
        ordered_boxes.pop(ordered_boxes.index("p3"))
        self.assertEqual(ordered_boxes, ["p1", "p2"])

        # Test contained iterative graph structures
        configured_iterbox = graph.find_node("p1").meta
        itergraphs = configured_iterbox.itergraphs(prefix="p1")
        iterkeys = ["p1" + IProcess.itersep + "0", "p1" + IProcess.itersep + "1"]
        self.assertEqual(sorted(itergraphs.keys()), iterkeys)
        for index, value in enumerate(pipeline.input1):
            self.assertEqual(itergraphs[iterkeys[index]][1].parameter1, value)
            ordered_nodes = [item[0]
                for item in itergraphs[iterkeys[index]][0].topological_sort()]
            self.assertEqual(ordered_nodes, [iterkeys[index]])

        # Test contained iterative graph structures
        configured_iterbox = graph.find_node("p3").meta
        itergraphs = configured_iterbox.itergraphs(prefix="p3")
        iterkeys = ["p3" + IProcess.itersep + "0", "p3" + IProcess.itersep + "1"]
        self.assertEqual(sorted(itergraphs.keys()), iterkeys)
        for index, value in enumerate(pipeline.input1):
            self.assertEqual(itergraphs[iterkeys[index]][1].input1, value)
            ordered_nodes = [item[0]
                for item in itergraphs[iterkeys[index]][0].topological_sort()]
            self.assertEqual(
                ordered_nodes, [iterkeys[index] + ".p1", iterkeys[index] + ".p2"])

        # Test execution
        pipeline()
        self.assertTrue(pipeline.output1 in [15, 25])
        self.assertTrue(set(pipeline.output2).issubset([31.25, 11.25]))

        if 0:
            from PySide import QtGui
            import sys
            from capsul.qt_gui.widgets import PipelineDevelopperView

            app = QtGui.QApplication(sys.argv)
            view1 = PipelineDevelopperView(pipeline)
            view1.show()
            app.exec_()


def test():
    """ Function to execute unitests.
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestIProcess)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    test()
