#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

import unittest
import os
import json
from traits.api import Str
from capsul.process import Process
from capsul.pipeline import Pipeline, PipelineNode


class DummyProcess(Process):
    """ Dummy Test Process
    """
    def __init__(self):
        super(DummyProcess, self).__init__()

        # inputs
        self.add_trait("input_image", Str(optional=False))
        self.add_trait("other_input", Str(optional=True))

        # outputs
        self.add_trait("output_image", Str(optional=False, output=True))
        self.add_trait("other_output", Str(optional=False, output=True))

    def _run_process(self):
        self.output_image = self.input_image
        self.other_output = self.other_input


class DummyProcess1_1(Process):
    """ Dummy Test Process with 1 input and one output
    """
    def __init__(self):
        super(DummyProcess1_1, self).__init__()

        # inputs
        self.add_trait("input", Str(optional=False))

        # outputs
        self.add_trait("output", Str(optional=False, output=True))

    def _run_process(self):
        self.output = self.input

class DummyProcess2_1(Process):
    """ Dummy Test Process with 2 inputs and one output
    """
    def __init__(self):
        super(DummyProcess2_1, self).__init__()

        # inputs
        self.add_trait("input1", Str(optional=False))
        self.add_trait("input2", Str(optional=False))

        # outputs
        self.add_trait("output", Str(optional=False, output=True))

    def _run_process(self):
        self.output = '_'.join((self.input1, self.input2))


class DummyProcess4_1(Process):
    """ Dummy Test Process with 4 inputs and one output
    """
    def __init__(self):
        super(DummyProcess4_1, self).__init__()

        # inputs
        self.add_trait("input1", Str(optional=False))
        self.add_trait("input2", Str(optional=False))
        self.add_trait("input3", Str(optional=False))
        self.add_trait("input4", Str(optional=False))

        # outputs
        self.add_trait("output", Str(optional=False, output=True))

    def _run_process(self):
        self.output = '_'.join((self.input1, self.input2, self.input3, 
                                self.input4))

class SwitchPipeline(Pipeline):
    """ Simple Pipeline to test the Switch Node
    """
    def pipeline_definition(self):

        # Create processes
        self.add_process("way1",
            DummyProcess)
        self.add_process("way2",
            DummyProcess)

        # Create Switch
        self.add_switch("switch", ["one", "two"],
                        ["switch_image", ])

        # Link input
        self.export_parameter("way1", "input_image")

        # Links
        self.add_link("way1.output_image->switch.one_switch_switch_image")

        self.add_link("input_image->way2.input_image")

        self.add_link("way2.output_image->switch.two_switch_switch_image")

        # Outputs
        self.export_parameter("way1", "other_output",
                              pipeline_parameter="weak_output_1",
                              weak_link=True, is_optional=True)
        self.export_parameter("way2", "other_output",
                              pipeline_parameter="weak_output_2",
                              weak_link=True, is_optional=True)
        self.export_parameter("switch", "switch_image",
                              pipeline_parameter="result_image")
        
        self.node_position = {'inputs': (40.0, 240.0),
                              'outputs': (605.0, 289.0),
                              'switch': (381.0, 255.0),
                              'way1': (211.0, 179.0),
                              'way2': (208.0, 338.0)}



class MultipleConnectionsPipeline(Pipeline):
    """ Simple Pipeline to test one input connected to several processes
    """
    def pipeline_definition(self):

        # Create processes
        self.add_process("process1",
            DummyProcess1_1)
        self.export_parameter('process1', 'input', 'input1')
        self.add_process("process2",
            DummyProcess1_1)
        self.add_link('input1->process2.input')
        self.add_process("process3",
            DummyProcess1_1)
        self.add_link('input1->process3.input')
        self.add_process("process4",
            DummyProcess4_1)
        self.add_link('process1.output->process4.input1')
        self.add_link('process2.output->process4.input2')
        self.add_link('process3.output->process4.input3')
        self.export_parameter('process4', 'input4', 'input2')

        self.node_position = {'inputs': (5.0, 87.0),
                              'outputs': (661.0, 239.0),
                              'switch_pipeline': (173.0, 112.0),
                              'way1_1': (377.0, 113.0),
                              'way1_2': (510.0, 163.0),
                              'way2_1': (376.0, 246.0),
                              'way2_2': (507.0, 296.0)}


class MainTestPipeline(Pipeline):
    def pipeline_definition(self):
        self.add_process('switch_pipeline',SwitchPipeline)
        # Export may be omited here but it is necessary to force parameters
        # order.
        self.export_parameter('switch_pipeline', 'input_image')
        self.export_parameter('switch_pipeline', 'switch', 'which_way')
        self.add_process('way1_1',MultipleConnectionsPipeline)
        self.add_process('way1_2',DummyProcess1_1)
        self.add_process('way2_1',MultipleConnectionsPipeline)
        self.add_process('way2_2',DummyProcess1_1)
        self.add_link('switch_pipeline.weak_output_1->way1_1.input1')
        self.add_link('switch_pipeline.result_image->way1_1.input2')
        self.add_link('way1_1.output->way1_2.input')
        self.export_parameter('way1_2', 'output')
        self.add_link('switch_pipeline.weak_output_2->way2_1.input1')
        self.add_link('switch_pipeline.result_image->way2_1.input2')
        self.add_link('way2_1.output->way2_2.input')
        self.add_link('way2_2.output->output')
        
        self.node_position = {'inputs': (5.0, 87.0),
                              'outputs': (661.0, 239.0),
                              'switch_pipeline': (173.0, 112.0),
                              'way1_1': (377.0, 113.0),
                              'way1_2': (510.0, 163.0),
                              'way2_1': (376.0, 246.0),
                              'way2_2': (507.0, 296.0)}

class TestSwitchPipeline(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None
        self.pipeline = MainTestPipeline()

    def load_state(self, file_name):
        file_name = os.path.join(os.path.dirname(__file__), file_name + '.json')
        return json.load(open(file_name))
    
    def test_self_state(self):
        # verify that the state of a pipeline does not generate differences
        # when compared to itself
        state = self.pipeline.pipeline_state()
        self.assertEqual(self.pipeline.compare_to_state(state),[])

    def test_switch_value(self):
        state_one = self.load_state('test_switch_subpipeline_one')    
        state_two = self.load_state('test_switch_subpipeline_two')
        self.pipeline.which_way = 'two'
        self.assertEqual(self.pipeline.compare_to_state(state_two),[])
        self.pipeline.which_way = 'one'
        self.assertEqual(self.pipeline.compare_to_state(state_one),[])


def test():
    """ Function to execute unitest
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSwitchPipeline)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()



if __name__ == "__main__":
    print "RETURNCODE: ", test()

    def write_state():
        state_file_name = '/tmp/state.json'
        json.dump(pipeline.pipeline_state(), open(state_file_name,'w'))
        print 'Wrote', state_file_name

    import sys
    #from PySide import QtGui
    from PyQt4 import QtGui
    from capsul.apps_qt.base.pipeline_widgets import PipelineDevelopperView
    from capsul.apps_qt.base.pipeline_widgets import PipelineUserView
    from capsul.process import get_process_instance

    app = QtGui.QApplication(sys.argv)
    pipeline = get_process_instance(MainTestPipeline)
    pipeline.on_trait_change(write_state,'selection_changed')
    view1 = PipelineDevelopperView(pipeline, show_sub_pipelines=True, allow_open_controller=True)
    view1.show()
    #view2 = PipelineUserView(pipeline)
    #view2.show()
    app.exec_()
    del view1
    #del view2

