# -*- coding: utf-8 -*-
# System import
from __future__ import print_function
from __future__ import absolute_import

import sys
import os
import os.path as osp
import unittest
from tempfile import NamedTemporaryFile
import struct

# Trait import
from traits.api import String, Int, List, File

# Capsul import
from capsul.api import Process
from capsul.api import Pipeline
from capsul.pipeline.process_iteration import ProcessIteration
import six
from six.moves import range


class WriteOutput(Process):
    input_image = File()
    output_image = File(output=True)
    
    def _run_process(self):
        # Copy input_image in output_image
        with open(self.input_image,'rb') as i:
            with open(self.output_image,'wb') as o:
                o.write(i.read())


class ProcessSlice(Process):
    input_image = File()
    slice_number = Int()
    output_image_dependency = File()
    output_image = File(output=True)
    
    def _run_process(self):
        file_size = os.stat(self.output_image).st_size
        if self.slice_number >= int(file_size/2):
            raise ValueError('Due to output file size, slice_number cannot '
                'be more than %d but %d was given' % (int(file_size/2), 
                self.slice_number))
        with open(self.output_image, 'r+b') as f:
            f.seek(self.slice_number*2, 0)
            f.write(struct.pack('H', self.slice_number))

class MyPipeline(Pipeline):
    """ Simple Pipeline to test the iterative Node
    """
    
    def __init__(self):
        super(MyPipeline, self).__init__()
        self.on_trait_change(self.input_image_changed, 'input_image')
        
    def input_image_changed(self):
        if isinstance(self.input_image, six.string_types) and \
                osp.exists(self.input_image):
            self.slices = list(range(int(os.stat(self.input_image).st_size/2)))
        else:
            self.slices = []
        
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
        self.add_link('write_output.output_image->process_slices.output_image_dependency')
        self.add_link('input_image->process_slices.input_image')
        self.add_link('process_slices.output_image->output_image')
        
        self.node_position = {'inputs': (-166.0, 78.18130000000002),
                              'outputs': (440.07785249999995, 23.68130000000002),
                              'process_slices': (193.47765249999998, 78.86126000000002),
                              'write_output': (3.4776524999999765, -1.0)}

class TestPipeline(unittest.TestCase):
    """ Class to test a pipeline with an iterative node
    """
    def setUp(self):
        """ In the setup construct the pipeline and set some input parameters.
        """
        # Construct the pipelHine
        self.pipeline = MyPipeline()

        # Set some input parameters
        self.parallel_processes = 10
        self.input_file = NamedTemporaryFile(delete = False)
        self.input_file.write(('\x00\x00' * self.parallel_processes).encode())
        self.input_file.flush()
        self.input_file.close()
        self.pipeline.input_image = self.input_file.name
        self.output_file = NamedTemporaryFile()
        self.output_file.close()
        self.pipeline.output_image = self.output_file.name

    def test_iterative_pipeline_connection(self):
        """ Method to test if an iterative node and built in iterative
        process are correctly connected.
        """

        # Test the output connection
        self.pipeline()
        with open(self.pipeline.output_image,'rb') as f:
            result = f.read()
        numbers = struct.unpack_from('H' * self.parallel_processes, result)
        self.assertEqual(numbers, tuple(range(self.parallel_processes)))


def test():
    """ Function to execute unitest
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPipeline)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    test()
    from soma.qt_gui.qt_backend import QtGui
    from capsul.qt_gui.widgets import PipelineDeveloperView

    app = QtGui.QApplication.instance()
    if not app:
        app = QtGui.QApplication(sys.argv)
    pipeline = MyPipeline()
    pipeline.input_image = '/tmp/x'
    pipeline.output_image = '/tmp/y'

    view1 = PipelineDeveloperView(pipeline, show_sub_pipelines=True,
                                   allow_open_controller=True)

    view1.show()
    app.exec_()
    del view1
    print('---')
