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
import logging

# Capsul import
from capsul.pipeline import Pipeline
from capsul.process.loader import get_process_instance
from capsul.study_config.run import scheduler
from capsul.study_config import StudyConfig


class TestLoadFromDescription(unittest.TestCase):
    """ Class to test scheduler mechanism.
    """
    def setUp(self):
        self.nb_cpus = 4
        self.verbose = 1

    def test_scheduled_pipeline(self):
        """ Method to test the scheduler on a simple pipelines.
        """
        print

        pipeline = get_process_instance("capsul.demo.pipeline.xml")
        self.assertTrue(isinstance(pipeline, Pipeline))
        for node_name in ["", "p1", "p2"]:
            self.assertTrue(node_name in pipeline.nodes)
        pipeline.input1 = [2.5]
        scheduler(pipeline, cpus=self.nb_cpus, verbose=self.verbose)
        self.assertEqual(pipeline.output1, 12.5)
        self.assertEqual(pipeline.output2, 31.25)
        self.assertEqual(pipeline.output3, "done")

        pipeline = get_process_instance("capsul.demo.switch_pipeline.xml")
        self.assertTrue(isinstance(pipeline, Pipeline))
        for node_name in ["", "p1", "p2", "p3", "p4", "p5"]:
            self.assertTrue(node_name in pipeline.nodes)
        pipeline.input1 = [2.5]
        pipeline.switch = "path1"
        scheduler(pipeline, cpus=self.nb_cpus, verbose=self.verbose)
        if pipeline.switch == "path2":
            self.assertEqual(pipeline.output, 78.125)
        else:
            self.assertEqual(pipeline.output, 195.3125)

        graph, inlinkreps, outlinkreps = pipeline._create_graph(
            pipeline, filter_inactive=True)
        ordered_boxes = [item[0] for item in graph.topological_sort()]
        if pipeline.switch == "path2":
            self.assertEqual(ordered_boxes, ["p1", "p4", "p5"])
        else:
            self.assertEqual(ordered_boxes, ["p1", "p2", "p3", "p5"])
           
        if 0:
            from PySide import QtGui
            import sys
            from capsul.qt_gui.widgets import PipelineDevelopperView

            app = QtGui.QApplication(sys.argv)
            view1 = PipelineDevelopperView(pipeline)
            view1.show()
            app.exec_()

    def test_scheduled_sub_pipeline(self):
        """ Method to test the scheduler on recursive pipeline.
        """
        print

        pipeline = get_process_instance("capsul.demo.sub_pipeline.xml")
        self.assertTrue(isinstance(pipeline, Pipeline))
        for node_name in ["", "p1", "p2", "p3"]:
            self.assertTrue(node_name in pipeline.nodes)

        pipeline.input1 = [2.5]
        pipeline.switch = "path2"
        scheduler(pipeline, cpus=self.nb_cpus, verbose=self.verbose)
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

    def test_scheduled_iprocess(self):
        """ Method to test the scheduler on iterative process.
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
        pipeline.input3 = 2

        # Test execution
        scheduler(pipeline, cpus=self.nb_cpus, verbose=self.verbose)
        self.assertEqual(pipeline.output1, 62.5)
        self.assertEqual(pipeline.output2, [31.25, 11.25])

        if 0:
            from PySide import QtGui
            import sys
            from capsul.qt_gui.widgets import PipelineDevelopperView

            app = QtGui.QApplication(sys.argv)
            view1 = PipelineDevelopperView(pipeline)
            view1.show()
            app.exec_()

    def test_scheduled_studyconfig(self):
        """ Method to test the scheduler on a study config.
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
        pipeline.input3 = 2

        # Test execution
        study_config = StudyConfig(
            output_directory="/volatile/nsap/v2/test_iprocess/",
            number_of_cpus=self.nb_cpus,
            generate_logging=True,
            use_scheduler=True)
        study_config.run(pipeline, verbose=self.verbose)
        self.assertEqual(pipeline.output1, 62.5)
        self.assertEqual(pipeline.output2, [31.25, 11.25])

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
