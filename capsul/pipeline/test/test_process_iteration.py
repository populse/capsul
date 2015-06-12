#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import sys
import unittest

# Trait import
from traits.api import String, Int, List, File

# Capsul import
from capsul.process import Process
from capsul.pipeline import Pipeline
from capsul.pipeline.process_iteration import ProcessIteration


class WriteOutput(Process):
    input_image = File()
    output_image = File(output=True)
    
    def _run_process(self):
        print 'Run WriteOutput(%s, %s)' % (repr(self.input_image), repr(self.output_image))


class ProcessSlice(Process):
    input_image = File()
    slice_number = Int()
    output_image = File(output=True)
    
    def _run_process(self):
        print 'Run ProcessSlice(%s, %d, %s)' % (repr(self.input_image), self.slice_number, repr(self.output_image))


class MyPipeline(Pipeline):
    """ Simple Pipeline to test the iterative Node
    """
    
    def __init__(self):
        super(MyPipeline, self).__init__()
        self.on_trait_change(self.input_image_changed, 'input_image')
        
    def input_image_changed(self):
        self.slices = range(len(self.input_image))
    
    def pipeline_definition(self):
        """ Define the pipeline.
        """
        self.add_process('write_output', WriteOutput)
        self.export_parameter('write_output', 'input_image')
        self.export_parameter('write_output', 'output_image')
        
        # Create an iterative processe
        self.add_process(
            'process_slices', ProcessIteration( ProcessSlice,
                iterative_parameters = ['slice_number']))
        
        self.export_parameter('process_slices', 'slice_number', 'slices')
        self.add_link('input_image->process_slices.input_image')
        self.add_link('process_slices.output_image->output_image')
        
        self.node_position = {'inputs': (-30.0, 41.18130000000002),
            'outputs': (340.07785249999995, 57.68130000000002),
            'process_slices': (154.47765249999998, 90.86126),
            'write_output': (154.47765249999998, 0.0)}

#class TestPipeline(unittest.TestCase):
    #""" Class to test a pipeline with an iterative node
    #"""
    #def setUp(self):
        #""" In the setup construct the pipeline and set some input parameters.
        #"""
        ## Construct the pipeline
        #self.pipeline = MyPipeline()

        ## Set some input parameters
        #self.pipeline.input_image = ["toto", "tutu"]
        #self.pipeline.dynamic_parameter = [3, 1]
        #self.pipeline.other_input = 5

    #def test_iterative_pipeline_connection(self):
        #""" Method to test if an iterative node and built in iterative
        #process are correctly connected.
        #"""

        ## Test the input connection
        #iterative_node = self.pipeline.nodes["iterative"]
        #iterative_pipeline = iterative_node.process
        #pipeline_node = iterative_pipeline.nodes[""]
        #for trait_name in iterative_node.input_iterative_traits:
            #self.assertEqual(getattr(pipeline_node.process, trait_name),
                             #getattr(self.pipeline, trait_name))
        #for trait_name in iterative_node.input_traits:
            #self.assertEqual(getattr(pipeline_node.process, trait_name),
                             #getattr(self.pipeline, trait_name))

        ## Test the output connection
        #self.pipeline()
        #if sys.version_info >= (2, 7):
            #self.assertIn("toto:5.0:3.0", iterative_pipeline.output_image)
            #self.assertIn("tutu:5.0:1.0", iterative_pipeline.output_image)
        #else:
            #self.assertTrue("toto:5.0:3.0" in iterative_pipeline.output_image)
            #self.assertTrue("tutu:5.0:1.0" in iterative_pipeline.output_image)
        #self.assertEqual(
            #self.pipeline.output_image, iterative_pipeline.output_image)
        #self.assertEqual(self.pipeline.other_output, 
                         #[self.pipeline.other_input, self.pipeline.other_input])


#def test():
    #""" Function to execute unitest
    #"""
    #suite = unittest.TestLoader().loadTestsFromTestCase(TestPipeline)
    #runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    #return runtime.wasSuccessful()


if __name__ == "__main__":
    #test()
    from PySide import QtGui
    from capsul.qt_gui.widgets import PipelineDevelopperView

    app = QtGui.QApplication(sys.argv)
    pipeline = MyPipeline()
    pipeline.input_image = '/tmp/x'
    pipeline.output_image = '/tmp/y'

    view1 = PipelineDevelopperView(pipeline, show_sub_pipelines=True,
                                    allow_open_controller=True)
#    view1.add_embedded_subpipeline('process_slices')

    view1.show()
    app.exec_()
    del view1
    print '---'
    
    pipeline()
    
