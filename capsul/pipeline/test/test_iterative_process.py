# -*- coding: utf-8 -*-

import sys
import unittest
import os
from pathlib import Path
import tempfile
import shutil

from soma.controller import undefined, File, field

# Capsul import
from capsul.api import Process, Pipeline, Capsul
from capsul.execution_context import CapsulWorkflow

debug = False

def setUpModule():
    global old_home
    global temp_home_dir
    # Run tests with a temporary HOME directory so that they are isolated from
    # the user's environment
    temp_home_dir = None
    old_home = os.environ.get('HOME')
    try:
        app_name = 'test_iterative_process'
        temp_home_dir = Path(tempfile.mkdtemp(prefix=f'capsul_{app_name}_'))
        os.environ['HOME'] = str(temp_home_dir)
        Capsul(app_name)    
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
    Capsul.delete_singleton()


class DummyProcess(Process):
    """ Dummy Test Process
    """
    # Inputs
    input_image: field(type_=File, optional=False)
    other_input: field(type_=float, optional=False)
    dynamic_parameter: field(type_=float, optional=False)
    # Outputs
    output_image: field(type_=File, write=True, optional=False, output=True)
    other_output: field(type_=float, optional=False, output=True, default=6)

    def execute(self, context):
        """ Execute the process.
        """
        if not getattr(self, 'output_image', None):
            # Just join the input values
            value = f'{self.input_image}-{self.other_input}-{self.dynamic_parameter}'
            self.output_image = value

        with open(self.output_image, 'w') as f_out:
            with open(self.input_image) as f_in:
                f_out.write(f_in.read())
        self.other_output = self.other_input


class CreateFilesProcess(Process):
    output_file: field(type_=list[File], write=True)

    def execute(self, context):
        # print('create: %s' % self.output_file)
        for fname in self.output_file:
            open(fname, "w").write("file: %s\n" % fname)


class CheckFilesProcess(Process):
    input_files: list[File]

    def execute(self, context):
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

        self.capsul = Capsul()

        # Construct the pipeline
        self.pipeline = self.capsul.executable(MyPipeline)

        # Set some input parameters
        self.pipeline.input_image = [os.path.join(self.directory, "toto"),
                                     os.path.join(self.directory, "tutu")]
        self.pipeline.dynamic_parameter = [3, 1]
        self.pipeline.other_input = 5

        # build a pipeline with dependencies
        self.small_pipeline \
            = self.capsul.executable(MySmallPipeline)
        self.small_pipeline.files_to_create = [
            os.path.join(self.directory, "toto"),
            os.path.join(self.directory, "tutu")]
        self.small_pipeline.dynamic_parameter = [3, 1]
        self.small_pipeline.other_input = 5

        # build a bigger pipeline with several levels
        self.big_pipeline \
            = self.capsul.executable(MyBigPipeline)

    def tearDown(self):
        if debug:
            print('directory %s not removed.' % self.directory)
        else:
            shutil.rmtree(self.directory)
        Capsul.delete_singleton()
        self.capsul = None
        
    def test_iterative_pipeline_connection(self):
        """ Test if an iterative process works correctly
        """
        # create inputs
        for f in self.pipeline.input_image:
            with open(f, "w") as fobj:
                fobj.write("input: %s\n" % f)

        # Test the output connection
        with Capsul().engine() as engine:
            engine.run(self.pipeline, timeout=5)

        self.assertIn("toto-5.0-3.0",
                        [os.path.basename(f)
                        for f in self.pipeline.output_image])
        self.assertIn("tutu-5.0-1.0",
                        [os.path.basename(f)
                        for f in self.pipeline.output_image])
        self.assertEqual(self.pipeline.other_output, 
                         [self.pipeline.other_input,
                          self.pipeline.other_input])

    def test_iterative_pipeline_workflow(self):
        self.small_pipeline.output_image = [
            os.path.join(self.directory, 'toto_out'),
            os.path.join(self.directory, 'tutu_out')]
        self.small_pipeline.other_output = [1., 2.]
        workflow = CapsulWorkflow(self.small_pipeline)
        #expect 2 + 2 (iter)  jobs
        self.assertEqual(len(workflow.jobs), 4)
        # expect 4 dependencies:
        # init -> iterative jobs (2)
        # iterative jobs -> end (2)
        self.assertEqual(sum(len(job['wait_for']) for job in workflow.jobs.values()), 4)

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
        workflow = CapsulWorkflow(self.big_pipeline)
        # expect:
        #  outer iteration 1: init + 2 iterative jobs + end
        #  outer iteration 2: init + 3 iterative jobs + end
        self.assertEqual(len(workflow.jobs), 9)

        subjects = set()
        for job in workflow.jobs.values():
            if not job['process']['definition'].endswith('.DummyProcess'):
                continue
            param_dict = workflow.parameters_dict
            for i in job['parameters_location']:
                if i.isnumeric():
                    i = int(i)
                param_dict = param_dict[i]
            proxy = param_dict["other_input"]
            value = workflow.parameters_values[proxy[1]]
            self.assertEqual(value, 5)
            proxy = param_dict['input_image']
            subject = workflow.parameters_values[proxy[1]]
            subjects.add(subject)
            self.assertIn(subject,
                            ["toto", "tutu", "tata", "titi", "tete"])
        self.assertEqual(subjects,
                         set(["toto", "tutu", "tata", "titi", "tete"]))

    def test_iterative_pipeline_workflow_run(self):

        self.small_pipeline.output_image = [
            os.path.join(self.directory, 'toto_out'),
            os.path.join(self.directory, 'tutu_out')]
        self.small_pipeline.other_output = [1., 2.]

        with self.capsul.engine() as c:
            c.run(self.small_pipeline, timeout=5)
        for ifname, fname in zip(self.small_pipeline.files_to_create,
                                  self.small_pipeline.output_image):
            with open(fname) as f:
                content = f.read()
            self.assertEqual(content, "file: %s\n" % ifname)


if __name__ == "__main__":
    from soma.qt_gui.qt_backend import QtGui
    from capsul.qt_gui.widgets import PipelineDeveloperView

    app = QtGui.QApplication.instance()
    if not app:
        app = QtGui.QApplication(sys.argv)
    pipeline = Capsul.executable(MySmallPipeline)
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

    pipeline2 = Capsul.executable(MyBigPipeline)
    view2 = PipelineDeveloperView(pipeline2, show_sub_pipelines=True,
                                    allow_open_controller=True)
    view2.add_embedded_subpipeline('iterative')
    view2.auto_dot_node_positions()
    view2.show()

    app.exec_()
    del view1
