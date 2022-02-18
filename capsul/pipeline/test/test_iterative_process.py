# -*- coding: utf-8 -*-
# System import
from __future__ import print_function
from __future__ import absolute_import

import sys
import unittest
import re
import os
import tempfile
import shutil

# Trait import
from traits.api import String, Float, Undefined, List, File

# Capsul import
from capsul.api import Process
from capsul.api import Pipeline
from capsul.api import StudyConfig
from capsul.pipeline import pipeline_workflow
from soma.controller import Controller
from soma_workflow import configuration as swconfig
from six.moves import zip

debug = False

def setUpModule():
    global old_home
    global temp_home_dir
    # Run tests with a temporary HOME directory so that they are isolated from
    # the user's environment
    temp_home_dir = None
    old_home = os.environ.get('HOME')
    try:
        temp_home_dir = tempfile.mkdtemp('', prefix='soma_workflow')
        os.environ['HOME'] = temp_home_dir
        swconfig.change_soma_workflow_directory(temp_home_dir)
    except BaseException:  # clean up in case of interruption
        if old_home is None:
            del os.environ['HOME']
        else:
            os.environ['HOME'] = old_home
        if temp_home_dir:
            shutil.rmtree(temp_home_dir)
        raise


def tearDownModule():
    if old_home is None:
        del os.environ['HOME']
    else:
        os.environ['HOME'] = old_home
    shutil.rmtree(temp_home_dir)


class DummyProcess(Process):
    """ Dummy Test Process
    """
    def __init__(self):
        """Initialize the DummyProcess.
        """
        # Inheritance
        super(DummyProcess, self).__init__()

        # Inputs
        self.add_trait("input_image", File(optional=False, output=False))
        self.add_trait("other_input", Float(optional=False, output=False))
        self.add_trait("dynamic_parameter",
                       Float(optional=False, output=False))

        # Outputs
        self.add_trait("output_image", File(optional=False, output=True,
                                            input_filename=False))
        self.add_trait("other_output", Float(optional=False, output=True))

        # Set default parameter
        self.other_input = 6

    def _run_process(self):
        """ Execute the process.
        """
        print('run: %s -> %s' % (self.input_image, str(self.output_image)))
        if self.output_image in (None, Undefined, ''):
            # Just join the input values
            value = "{0}-{1}-{2}".format(
                self.input_image, self.other_input, self.dynamic_parameter)
            self.output_image = value
            print('    define output_image: %s' % value)

        with open(self.output_image, 'w') as f_out:
            with open(self.input_image) as f_in:
                f_out.write(f_in.read())
        self.other_output = self.other_input


class CreateFilesProcess(Process):
    def __init__(self):
        super(CreateFilesProcess, self).__init__()
        self.add_trait("output_file", List(File(output=True), output=True))

    def _run_process(self):
        print('create: %s' % self.output_file)
        for fname in self.output_file:
            open(fname, "w").write("file: %s\n" % fname)


class CheckFilesProcess(Process):
    def __init__(self):
        super(CheckFilesProcess, self).__init__()
        self.add_trait("input_files", List(File(output=False)))

    def _run_process(self):
        for f in self.input_files:
            open(f)

class MyPipeline(Pipeline):
    """ Simple Pipeline to test the iterative Node
    """
    def pipeline_definition(self):
        """ Define the pipeline.
        """
        # Create an iterative process
        self.add_iterative_process(
            "iterative",
            "capsul.pipeline.test.test_iterative_process.DummyProcess",
            iterative_plugs=[
                "input_image", "output_image", "dynamic_parameter",
                "other_output"])

        # Set the pipeline view scale factor
        self.scene_scale_factor = 1.0

        self.node_position = {
            'inputs': (0.0, 35.5),
            'iterative': (194.11260000000001, 0.0),
            'outputs': (841.5382, 117.55362)}


class MySmallPipeline(Pipeline):
    """ Simple Pipeline to test the iterative Node, with dependencies
    """
    def pipeline_definition(self):
        """ Define the pipeline.
        """
        self.add_process(
            "init",
            "capsul.pipeline.test.test_iterative_process.CreateFilesProcess")
        # Create an iterative process
        self.add_iterative_process(
            "iterative",
            "capsul.pipeline.test.test_iterative_process.DummyProcess",
            iterative_plugs=[
                "input_image", "output_image", "dynamic_parameter",
                "other_output"])
        self.add_process(
            "end",
            "capsul.pipeline.test.test_iterative_process.CheckFilesProcess")
        self.export_parameter("init", "output_file", "files_to_create")
        self.export_parameter("iterative", "output_image")
        self.add_link("init.output_file->iterative.input_image")
        self.add_link("iterative.output_image->end.input_files")

        # Set the pipeline view scale factor
        self.scene_scale_factor = 1.0

        self.node_position = {
            'inputs': (0.0, 35.5),
            'init': (28.5, 133.96983999999998),
            'end': (855.5382, 46.5),
            'iterative': (194.11260000000001, 0.0),
            'outputs': (841.5382, 117.55362)}

class MyBigPipeline(Pipeline):
    '''bigger pipeline with several levels'''
    def pipeline_definition(self):
        self.add_iterative_process(
            "main_level",
            "capsul.pipeline.test.test_iterative_process.MySmallPipeline",
            iterative_plugs=[
                "files_to_create", "output_image", "dynamic_parameter",
                "other_output"])


class TestPipeline(unittest.TestCase):
    """ Class to test a pipeline with an iterative node
    """
    def setUp(self):
        """ In the setup construct the pipeline and set some input parameters.
        """
        self.directory = tempfile.mkdtemp(prefix="capsul_test")

        self.study_config = StudyConfig()

        # Construct the pipeline
        self.pipeline = self.study_config.get_process_instance(MyPipeline)

        # Set some input parameters
        self.pipeline.input_image = [os.path.join(self.directory, "toto"),
                                     os.path.join(self.directory, "tutu")]
        self.pipeline.dynamic_parameter = [3, 1]
        self.pipeline.other_input = 5

        # build a pipeline with dependencies
        self.small_pipeline \
            = self.study_config.get_process_instance(MySmallPipeline)
        self.small_pipeline.files_to_create = [
            os.path.join(self.directory, "toto"),
            os.path.join(self.directory, "tutu")]
        self.small_pipeline.dynamic_parameter = [3, 1]
        self.small_pipeline.other_input = 5

        # build a bigger pipeline with several levels
        self.big_pipeline \
            = self.study_config.get_process_instance(MyBigPipeline)

    def tearDown(self):
        swm = self.study_config.modules['SomaWorkflowConfig']
        swc = swm.get_workflow_controller()
        if swc is not None:
            # stop workflow controller and wait for thread termination
            swc.stop_engine()
        if debug:
            print('directory %s not removed.' % self.directory)
        else:
            shutil.rmtree(self.directory)

    def test_iterative_pipeline_connection(self):
        """ Test if an iterative process works correctly
        """

        # create inputs
        for f in self.pipeline.input_image:
            with open(f, "w") as fobj:
                fobj.write("input: %s\n" % f)

        # Test the output connection
        self.pipeline()

        if sys.version_info >= (2, 7):
            self.assertIn("toto-5.0-3.0",
                          [os.path.basename(f)
                           for f in self.pipeline.output_image])
            self.assertIn("tutu-5.0-1.0",
                          [os.path.basename(f)
                           for f in self.pipeline.output_image])
        else:
            self.assertTrue("toto-5.0-3.0" in
                [os.path.basename(f) for f in self.pipeline.output_image])
            self.assertTrue("tutu-5.0-1.0" in
                [os.path.basename(f) for f in self.pipeline.output_image])
        self.assertEqual(self.pipeline.other_output, 
                         [self.pipeline.other_input,
                          self.pipeline.other_input])

    def test_iterative_pipeline_workflow(self):
        self.small_pipeline.output_image = [
            os.path.join(self.directory, 'toto_out'),
            os.path.join(self.directory, 'tutu_out')]
        self.small_pipeline.other_output = [1., 2.]
        workflow = pipeline_workflow.workflow_from_pipeline(
            self.small_pipeline)
        #expect 2 + 2 (iter) + 2 (barriers) jobs
        self.assertEqual(len(workflow.jobs), 6)
        # expect 6 dependencies:
        # init -> iterative input barrier
        # iterative output barrier -> end
        # iterative input barrier -> iterative jobs (2)
        # iterative jobs -> iterative output barrier (2)
        self.assertEqual(len(workflow.dependencies), 6)

    def test_iterative_big_pipeline_workflow(self):
        self.big_pipeline.files_to_create = [["toto", "tutu"],
                                         ["tata", "titi", "tete"]]
        self.big_pipeline.dynamic_parameter = [[1, 2], [3, 4, 5]]
        self.big_pipeline.other_input = 5
        self.big_pipeline.output_image = [
            [os.path.join(self.directory, 'toto_out'),
             os.path.join(self.directory, 'tutu_out')],
            [os.path.join(self.directory, 'tata_out'),
             os.path.join(self.directory, 'titi_out'),
             os.path.join(self.directory, 'tete_out')]]
        self.big_pipeline.other_output = [[1.1, 2.1], [3.1, 4.1, 5.1]]
        workflow = pipeline_workflow.workflow_from_pipeline(self.big_pipeline)
        # expect 6 + 7 + 2 jobs
        self.assertEqual(len(workflow.jobs), 15)
        subjects = set()
        for job in workflow.jobs:
            if not job.name.startswith('DummyProcess') or '_map' in job.name \
                    or '_reduce' in job.name:
                continue
            param_dict = job.param_dict
            self.assertEqual(param_dict["other_input"], 5)
            subject = param_dict['input_image']
            subjects.add(subject)
            if sys.version_info >= (2, 7):
                self.assertIn(subject,
                              ["toto", "tutu", "tata", "titi", "tete"])
            else:
                self.assertTrue(subject in
                                ["toto", "tutu", "tata", "titi", "tete"])
        self.assertEqual(subjects,
                         set(["toto", "tutu", "tata", "titi", "tete"]))

    def test_iterative_pipeline_workflow_run(self):
        import soma_workflow.constants as swconstants
        import soma_workflow.client as swclient

        self.small_pipeline.output_image = [
            os.path.join(self.directory, 'toto_out'),
            os.path.join(self.directory, 'tutu_out')]
        self.small_pipeline.other_output = [1., 2.]
        workflow = pipeline_workflow.workflow_from_pipeline(
            self.small_pipeline)
        swclient.Helper.serialize(
            os.path.join(self.directory, 'smallpipeline.workflow'), workflow)

        self.study_config.use_soma_workflow = True

        #controller = swclient.WorkflowController(config=config)
        #try:

        #wf_id = controller.submit_workflow(workflow)
        print('* running pipeline...')
        #swclient.Helper.wait_workflow(wf_id, controller)
        self.study_config.run(self.small_pipeline)
        print('* finished.')
        #workflow_status = controller.workflow_status(wf_id)
        #elements_status = controller.workflow_elements_status(wf_id)
        #failed_jobs = [element for element in elements_status[0] \
            #if element[1] != swconstants.DONE \
                #or element[3][0] != swconstants.FINISHED_REGULARLY]
        #if not debug:
            #controller.delete_workflow(wf_id)
        #self.assertTrue(workflow_status == swconstants.WORKFLOW_DONE,
            #'Workflow did not finish regularly: %s' % workflow_status)
        #self.assertTrue(len(failed_jobs) == 0, 'Jobs failed: %s'
                        #% failed_jobs)
        # check output files contents
        for ifname, fname in zip(self.small_pipeline.files_to_create,
                                  self.small_pipeline.output_image):
            with open(fname) as f:
                content = f.read()
            self.assertEqual(content, "file: %s\n" % ifname)

        #finally:
            # remove the temporary database
            #del controller
            #del config

def test():
    """ Function to execute unitest
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPipeline)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    if '-d' in sys.argv[1:] or '--debug' in sys.argv[1:]:
        debug = True

    test()

    if '-v' in sys.argv[1:] or '--verbose' in sys.argv[1:]:
        from soma.qt_gui.qt_backend import QtGui
        from capsul.qt_gui.widgets import PipelineDeveloperView

        app = QtGui.QApplication.instance()
        if not app:
            app = QtGui.QApplication(sys.argv)
        pipeline = MySmallPipeline()
        pipeline.files_to_create = ["toto", "tutu", "titi"]
        pipeline.output_image = ['toto_out', 'tutu_out', 'tata_out']
        pipeline.dynamic_parameter = [3, 1, 4]
        pipeline.other_output = [0, 0, 0]
        pipeline.other_input = 0
        pipeline2 = pipeline.nodes["iterative"].process
        pipeline2.scene_scale_factor = 0.5

        view1 = PipelineDeveloperView(pipeline, show_sub_pipelines=True,
                                       allow_open_controller=True)
        view1.add_embedded_subpipeline('iterative')
        view1.auto_dot_node_positions()
        view1.show()

        pipeline2 = MyBigPipeline()
        view2 = PipelineDeveloperView(pipeline2, show_sub_pipelines=True,
                                       allow_open_controller=True)
        view2.add_embedded_subpipeline('iterative')
        view2.auto_dot_node_positions()
        view2.show()

        app.exec_()
        del view1
