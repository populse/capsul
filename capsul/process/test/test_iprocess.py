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

        if 1:
            from PySide import QtGui
            import sys
            from capsul.qt_gui.widgets import PipelineDevelopperView

            app = QtGui.QApplication(sys.argv)
            view1 = PipelineDevelopperView(self.myiprocess)
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
