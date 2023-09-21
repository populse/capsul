# -*- coding: utf-8 -*-

import os
import os.path as osp
import json
import shutil
import unittest
import tempfile
from datetime import time, datetime

from populse_db import json_encode

from capsul.api import Process, Capsul
from capsul.pipeline.pipeline_tools import (save_pipeline_parameters,
                                            load_pipeline_parameters)
from soma.controller import File


def load_pipeline_dictionary(filename):
    """
    Just a part of load_pipeline_parameters to check if the values stored
    in the dictionary are correct.
    :param filename: the json filename
    """
    if filename:
        with open(filename, 'r', encoding='utf8') as file:
            return json.load(file)


class TestInt(Process):
    __test__ = False

    def __init__(self, definition):
        super().__init__(definition)

        self.add_field("in_1", int, output=False)
        self.add_field("in_2", int, output=False)
        self.add_field("out", int, output=True)

    def execute(self, context):
        self.out = self.in_1 + self.in_2


class TestFloat(Process):
    __test__ = False

    def __init__(self, definition):
        super().__init__(definition)

        self.add_field("in_1", float, output=False)
        self.add_field("in_2", float, output=False)
        self.add_field("out", float, output=True)

    def execute(self, context):
        self.out = self.in_1 - self.in_2


class TestString(Process):
    __test__ = False

    def __init__(self, definition):
        super().__init__(definition)

        self.add_field("in_1", str, output=False)
        self.add_field("in_2", str, output=False)
        self.add_field("out", str, output=True)

    def execute(self, context):
        self.out = self.in_1 + self.in_2


class TestFile(Process):
    __test__ = False

    def __init__(self, definition):
        super().__init__(definition)

        self.add_field("in_1", File, output=False)
        self.add_field("in_2", File, output=False)
        self.add_field("out", list[File], output=True)

    def execute(self, context):
        self.out = [self.in_1, self.in_2]


class TestListInt(Process):
    __test__ = False

    def __init__(self, definition):
        super().__init__(definition)

        self.add_field("in_1", list[int], output=False)
        self.add_field("in_2", list[int], output=False)
        self.add_field("out", list[int], output=True)

    def execute(self, context):
        l = []
        for idx, i in enumerate(self.in_1):
            l.append(i + self.in_2[idx])
        self.out = l


class TestListFloat(Process):
    __test__ = False

    def __init__(self, definition):
        super().__init__(definition)

        self.add_field("in_1", list[float], output=False)
        self.add_field("in_2", list[float], output=False)
        self.add_field("out", list[float], output=True)

    def execute(self, context):
        l = []
        for idx, i in enumerate(self.in_1):
            l.append(i - self.in_2[idx])
        self.out = l


class TestListString(Process):
    __test__ = False

    def __init__(self, definition):
        super().__init__(definition)

        self.add_field("in_1", list[str], output=False)
        self.add_field("in_2", list[str], output=False)
        self.add_field("out", list[str], output=True)

    def execute(self, context):
        l = []
        for idx, i in enumerate(self.in_1):
            l.append(i + self.in_2[idx])
        self.out = l


class TestListFile(Process):
    __test__ = False

    def __init__(self, definition):
        super().__init__(definition)

        self.add_field("in_1", list[File], output=False)
        self.add_field("in_2", list[File], output=False)
        self.add_field("out", list[File], output=True)

    def execute(self, context):
        self.out = [self.in_1[0], self.in_2[0]]


class TestListList(Process):
    __test__ = False

    def __init__(self, definition):
        super().__init__(definition)

        self.add_field("in_1", list[list[int]], output=False)
        self.add_field("in_2", list[list[int]], output=False)
        self.add_field("out", list[int], output=True)

    def execute(self, context):
        l = []
        for idx, i in enumerate(self.in_1):
            l.append(i[0] + self.in_2[idx][0])
        self.out = l


class TestDateTime(Process):
    __test__ = False

    def __init__(self, definition):
        super().__init__(definition)

        self.add_field("in_1", datetime, output=False)
        self.add_field("in_2", time, output=False)
        self.add_field("out", list, output=True)

    def execute(self, context):
        self.out = [self.in_1, self.in_2]


class TestPipelineMethods(unittest.TestCase):
    """
    Class executing the unit tests of load_pipeline_parameters and save_pipeline_parameters
    """

    def setUp(self):
        """
        Called before every unit test
        Creates a temporary folder containing the json file that will be used for the test
        """

        self.temp_folder = tempfile.mkdtemp(
            prefix='capsul_test_pipeline_parameters_')
        self.path = os.path.join(self.temp_folder, "test.json")
        self.capsul = Capsul(database_path='')
        self.capsul.config.databases['builtin']['path'] \
            = osp.join(self.temp_folder, 'capsul_engine_database.rdb')

    def tearDown(self):
        """
        Called after every unit test
        Deletes the temporary folder created for the test
        """

        shutil.rmtree(self.temp_folder)

    def test_int(self):
        def create_pipeline():
            pipeline = Capsul.custom_pipeline()
            pipeline.add_process("node_1", TestInt)
            pipeline.export_parameter("node_1", "in_1", "in_1")
            pipeline.export_parameter("node_1", "in_2", "in_2")
            pipeline.export_parameter("node_1", "out", "out")
            return pipeline

        in_1 = 2
        in_2 = 4
        out = 6

        pipeline1 = create_pipeline()
        pipeline1.in_1 = in_1
        pipeline1.in_2 = in_2

        with self.capsul.engine() as ce:
            ce.run(pipeline1, timeout=5)
        save_pipeline_parameters(self.path, pipeline1)

        # Reinitializing pipeline and loading parameters
        pipeline1 = create_pipeline()
        load_pipeline_parameters(self.path, pipeline1)
        self.assertEqual(pipeline1.in_1, in_1)
        self.assertEqual(pipeline1.in_2, in_2)
        self.assertEqual(pipeline1.out, out)

        self.assertEqual(type(pipeline1.in_1), int)
        self.assertEqual(type(pipeline1.in_2), int)
        self.assertEqual(type(pipeline1.out), int)

        # Verifying the dictionary
        dic = load_pipeline_dictionary(self.path)
        self.assertEqual(dic["pipeline_parameters"]["in_1"], in_1)
        self.assertEqual(dic["pipeline_parameters"]["in_2"], in_2)
        self.assertEqual(dic["pipeline_parameters"]["out"], out)

        self.assertEqual(type(dic["pipeline_parameters"]["in_1"]), int)
        self.assertEqual(type(dic["pipeline_parameters"]["in_2"]), int)
        self.assertEqual(type(dic["pipeline_parameters"]["out"]), int)

    def test_float(self):
        def create_pipeline():
            pipeline = Capsul.custom_pipeline()
            pipeline.add_process("node_1", TestFloat)
            pipeline.export_parameter("node_1", "in_1", "in_1")
            pipeline.export_parameter("node_1", "in_2", "in_2")
            pipeline.export_parameter("node_1", "out", "out")
            return pipeline

        pipeline1 = create_pipeline()
        pipeline1.in_1 = 2.0
        pipeline1.in_2 = 4.0

        with self.capsul.engine() as ce:
            ce.run(pipeline1, timeout=5)

        in_1 = 2.0
        in_2 = 4.0
        out = -2.0

        pipeline1 = create_pipeline()
        pipeline1.in_1 = in_1
        pipeline1.in_2 = in_2

        with self.capsul.engine() as ce:
            ce.run(pipeline1, timeout=5)

        save_pipeline_parameters(self.path, pipeline1)

        # Reinitializing pipeline and loading parameters
        pipeline1 = create_pipeline()
        load_pipeline_parameters(self.path, pipeline1)
        self.assertEqual(pipeline1.in_1, in_1)
        self.assertEqual(pipeline1.in_2, in_2)
        self.assertEqual(pipeline1.out, out)

        self.assertEqual(type(pipeline1.in_1), float)
        self.assertEqual(type(pipeline1.in_2), float)
        self.assertEqual(type(pipeline1.out), float)

        # Verifying the dictionary
        dic = load_pipeline_dictionary(self.path)
        self.assertEqual(dic["pipeline_parameters"]["in_1"], in_1)
        self.assertEqual(dic["pipeline_parameters"]["in_2"], in_2)
        self.assertEqual(dic["pipeline_parameters"]["out"], out)

        self.assertEqual(type(dic["pipeline_parameters"]["in_1"]), float)
        self.assertEqual(type(dic["pipeline_parameters"]["in_2"]), float)
        self.assertEqual(type(dic["pipeline_parameters"]["out"]), float)

    def test_string(self):
        def create_pipeline():
            pipeline = Capsul.custom_pipeline()
            pipeline.add_process("node_1", TestString)
            pipeline.export_parameter("node_1", "in_1", "in_1")
            pipeline.export_parameter("node_1", "in_2", "in_2")
            pipeline.export_parameter("node_1", "out", "out")
            return pipeline

        in_1 = "This is "
        in_2 = "a test"
        out = "This is " + "a test"

        pipeline1 = create_pipeline()
        pipeline1.in_1 = in_1
        pipeline1.in_2 = in_2

        with self.capsul.engine() as ce:
            ce.run(pipeline1, timeout=5)

        save_pipeline_parameters(self.path, pipeline1)

        # Reinitializing pipeline and loading parameters
        pipeline1 = create_pipeline()
        load_pipeline_parameters(self.path, pipeline1)
        self.assertEqual(pipeline1.in_1, in_1)
        self.assertEqual(pipeline1.in_2, in_2)
        self.assertEqual(pipeline1.out, out)

        self.assertEqual(type(pipeline1.in_1), str)
        self.assertEqual(type(pipeline1.in_2), str)
        self.assertEqual(type(pipeline1.out), str)

        # Verifying the dictionary
        dic = load_pipeline_dictionary(self.path)
        self.assertEqual(dic["pipeline_parameters"]["in_1"], in_1)
        self.assertEqual(dic["pipeline_parameters"]["in_2"], in_2)
        self.assertEqual(dic["pipeline_parameters"]["out"], out)

        self.assertEqual(type(dic["pipeline_parameters"]["in_1"]), str)
        self.assertEqual(type(dic["pipeline_parameters"]["in_2"]), str)
        self.assertEqual(type(dic["pipeline_parameters"]["out"]), str)

    def test_file(self):
        def create_pipeline():
            pipeline = Capsul.custom_pipeline()
            pipeline.add_process("node_1", TestFile)
            pipeline.export_parameter("node_1", "in_1", "in_1")
            pipeline.export_parameter("node_1", "in_2", "in_2")
            pipeline.export_parameter("node_1", "out", "out")
            return pipeline

        in_1 = '/tmp/yolo.nii'
        in_2 = '/tmp/yolo2.nii'
        out = ['/tmp/yolo.nii', '/tmp/yolo2.nii']

        pipeline1 = create_pipeline()
        pipeline1.in_1 = in_1
        pipeline1.in_2 = in_2

        with self.capsul.engine() as ce:
            ce.run(pipeline1, timeout=5)

        save_pipeline_parameters(self.path, pipeline1)

        # Reinitializing pipeline and loading parameters
        pipeline1 = create_pipeline()
        load_pipeline_parameters(self.path, pipeline1)
        self.assertEqual(pipeline1.in_1, in_1)
        self.assertEqual(pipeline1.in_2, in_2)
        self.assertEqual(pipeline1.out, out)

        self.assertEqual(type(pipeline1.in_1), str)
        self.assertEqual(type(pipeline1.in_2), str)
        self.assertEqual(type(pipeline1.out), list)

        for idx, element in enumerate(pipeline1.out):
            self.assertEqual(element, out[idx])
            self.assertEqual(type(element), str)

        # Verifying the dictionary
        dic = load_pipeline_dictionary(self.path)
        self.assertEqual(dic["pipeline_parameters"]["in_1"], in_1)
        self.assertEqual(dic["pipeline_parameters"]["in_2"], in_2)
        self.assertEqual(dic["pipeline_parameters"]["out"], out)

        self.assertEqual(type(dic["pipeline_parameters"]["in_1"]), str)
        self.assertEqual(type(dic["pipeline_parameters"]["in_2"]), str)
        self.assertEqual(type(dic["pipeline_parameters"]["out"]), list)

    def test_list_int(self):
        def create_pipeline():
            pipeline = Capsul.custom_pipeline()
            pipeline.add_process("node_1", TestListInt)
            pipeline.export_parameter("node_1", "in_1", "in_1")
            pipeline.export_parameter("node_1", "in_2", "in_2")
            pipeline.export_parameter("node_1", "out", "out")
            return pipeline

        in_1 = [2, 4, 5]
        in_2 = [4, 8, 9]
        out = [6, 12, 14]

        pipeline1 = create_pipeline()
        pipeline1.in_1 = in_1
        pipeline1.in_2 = in_2

        with self.capsul.engine() as ce:
            ce.run(pipeline1, timeout=5)

        save_pipeline_parameters(self.path, pipeline1)

        # Reinitializing pipeline and loading parameters
        pipeline1 = create_pipeline()
        load_pipeline_parameters(self.path, pipeline1)
        self.assertEqual(pipeline1.in_1, in_1)
        self.assertEqual(pipeline1.in_2, in_2)
        self.assertEqual(pipeline1.out, out)

        self.assertEqual(type(pipeline1.in_1), list)
        self.assertEqual(type(pipeline1.in_2), list)
        self.assertEqual(type(pipeline1.out), list)

        for idx, element in enumerate(pipeline1.in_1):
            self.assertEqual(element, in_1[idx])
            self.assertEqual(type(element), int)

        for idx, element in enumerate(pipeline1.in_2):
            self.assertEqual(element, in_2[idx])
            self.assertEqual(type(element), int)

        for idx, element in enumerate(pipeline1.out):
            self.assertEqual(element, out[idx])
            self.assertEqual(type(element), int)

        # Verifying the dictionary
        dic = load_pipeline_dictionary(self.path)
        self.assertEqual(dic["pipeline_parameters"]["in_1"], in_1)
        self.assertEqual(dic["pipeline_parameters"]["in_2"], in_2)
        self.assertEqual(dic["pipeline_parameters"]["out"], out)

        self.assertEqual(type(dic["pipeline_parameters"]["in_1"]), list)
        self.assertEqual(type(dic["pipeline_parameters"]["in_2"]), list)
        self.assertEqual(type(dic["pipeline_parameters"]["out"]), list)

        for idx, element in enumerate(dic["pipeline_parameters"]["in_1"]):
            self.assertEqual(element, in_1[idx])
            self.assertEqual(type(element), int)

        for idx, element in enumerate(dic["pipeline_parameters"]["in_2"]):
            self.assertEqual(element, in_2[idx])
            self.assertEqual(type(element), int)

        for idx, element in enumerate(dic["pipeline_parameters"]["out"]):
            self.assertEqual(element, out[idx])
            self.assertEqual(type(element), int)

    def test_list_float(self):
        def create_pipeline():
            pipeline = Capsul.custom_pipeline()
            pipeline.add_process("node_1", TestListFloat)
            pipeline.export_parameter("node_1", "in_1", "in_1")
            pipeline.export_parameter("node_1", "in_2", "in_2")
            pipeline.export_parameter("node_1", "out", "out")
            return pipeline

        in_1 = [2.0, 4.0, 5.0]
        in_2 = [4.0, 8.0, 9.0]
        out = [-2.0, -4.0, -4.0]

        pipeline1 = create_pipeline()
        pipeline1.in_1 = in_1
        pipeline1.in_2 = in_2

        with self.capsul.engine() as ce:
            ce.run(pipeline1, timeout=5)

        save_pipeline_parameters(self.path, pipeline1)

        # Reinitializing pipeline and loading parameters
        pipeline1 = create_pipeline()
        load_pipeline_parameters(self.path, pipeline1)
        self.assertEqual(pipeline1.in_1, in_1)
        self.assertEqual(pipeline1.in_2, in_2)
        self.assertEqual(pipeline1.out, out)

        self.assertEqual(type(pipeline1.in_1), list)
        self.assertEqual(type(pipeline1.in_2), list)
        self.assertEqual(type(pipeline1.out), list)

        for idx, element in enumerate(pipeline1.in_1):
            self.assertEqual(element, in_1[idx])
            self.assertEqual(type(element), float)

        for idx, element in enumerate(pipeline1.in_2):
            self.assertEqual(element, in_2[idx])
            self.assertEqual(type(element), float)

        for idx, element in enumerate(pipeline1.out):
            self.assertEqual(element, out[idx])
            self.assertEqual(type(element), float)

        # Verifying the dictionary
        dic = load_pipeline_dictionary(self.path)
        self.assertEqual(dic["pipeline_parameters"]["in_1"], in_1)
        self.assertEqual(dic["pipeline_parameters"]["in_2"], in_2)
        self.assertEqual(dic["pipeline_parameters"]["out"], out)

        self.assertEqual(type(dic["pipeline_parameters"]["in_1"]), list)
        self.assertEqual(type(dic["pipeline_parameters"]["in_2"]), list)
        self.assertEqual(type(dic["pipeline_parameters"]["out"]), list)

        for idx, element in enumerate(dic["pipeline_parameters"]["in_1"]):
            self.assertEqual(element, in_1[idx])
            self.assertEqual(type(element), float)

        for idx, element in enumerate(dic["pipeline_parameters"]["in_2"]):
            self.assertEqual(element, in_2[idx])
            self.assertEqual(type(element), float)

        for idx, element in enumerate(dic["pipeline_parameters"]["out"]):
            self.assertEqual(element, out[idx])
            self.assertEqual(type(element), float)

    def test_list_string(self):
        def create_pipeline():
            pipeline = Capsul.custom_pipeline()
            pipeline.add_process("node_1", TestListString)
            pipeline.export_parameter("node_1", "in_1", "in_1")
            pipeline.export_parameter("node_1", "in_2", "in_2")
            pipeline.export_parameter("node_1", "out", "out")
            return pipeline

        in_1 = ["hello ", "hey "]
        in_2 = ["salut", "coucou"]
        out = ["hello salut", "hey coucou"]

        pipeline1 = create_pipeline()
        pipeline1.in_1 = in_1
        pipeline1.in_2 = in_2

        with self.capsul.engine() as ce:
            ce.run(pipeline1, timeout=5)

        save_pipeline_parameters(self.path, pipeline1)

        # Reinitializing pipeline and loading parameters
        pipeline1 = create_pipeline()
        load_pipeline_parameters(self.path, pipeline1)
        self.assertEqual(pipeline1.in_1, in_1)
        self.assertEqual(pipeline1.in_2, in_2)
        self.assertEqual(pipeline1.out, out)

        self.assertEqual(type(pipeline1.in_1), list)
        self.assertEqual(type(pipeline1.in_2), list)
        self.assertEqual(type(pipeline1.out), list)

        for idx, element in enumerate(pipeline1.in_1):
            self.assertEqual(element, in_1[idx])
            self.assertEqual(type(element), str)

        for idx, element in enumerate(pipeline1.in_2):
            self.assertEqual(element, in_2[idx])
            self.assertEqual(type(element), str)

        for idx, element in enumerate(pipeline1.out):
            self.assertEqual(element, out[idx])
            self.assertEqual(type(element), str)

        # Verifying the dictionary
        dic = load_pipeline_dictionary(self.path)
        self.assertEqual(dic["pipeline_parameters"]["in_1"], in_1)
        self.assertEqual(dic["pipeline_parameters"]["in_2"], in_2)
        self.assertEqual(dic["pipeline_parameters"]["out"], out)

        self.assertEqual(type(dic["pipeline_parameters"]["in_1"]), list)
        self.assertEqual(type(dic["pipeline_parameters"]["in_2"]), list)
        self.assertEqual(type(dic["pipeline_parameters"]["out"]), list)

        for idx, element in enumerate(dic["pipeline_parameters"]["in_1"]):
            self.assertEqual(element, in_1[idx])
            self.assertEqual(type(element), str)

        for idx, element in enumerate(dic["pipeline_parameters"]["in_2"]):
            self.assertEqual(element, in_2[idx])
            self.assertEqual(type(element), str)

        for idx, element in enumerate(dic["pipeline_parameters"]["out"]):
            self.assertEqual(element, out[idx])
            self.assertEqual(type(element), str)

    def test_list_file(self):
        def create_pipeline():
            pipeline = Capsul.custom_pipeline()
            pipeline.add_process("node_1", TestListFile)
            pipeline.export_parameter("node_1", "in_1", "in_1")
            pipeline.export_parameter("node_1", "in_2", "in_2")
            pipeline.export_parameter("node_1", "out", "out")
            return pipeline

        in_1 = ["/tmp/yolo.txt", "/tmp/yolo2.txt"]
        in_2 = ["/tmp/yolo.nii", "/tmp/yolo2.nii"]
        out = ["/tmp/yolo.txt", "/tmp/yolo.nii"]

        pipeline1 = create_pipeline()
        pipeline1.in_1 = in_1
        pipeline1.in_2 = in_2

        with self.capsul.engine() as ce:
            ce.run(pipeline1, timeout=5)

        save_pipeline_parameters(self.path, pipeline1)

        # Reinitializing pipeline and loading parameters
        pipeline1 = create_pipeline()
        load_pipeline_parameters(self.path, pipeline1)
        self.assertEqual(pipeline1.in_1, in_1)
        self.assertEqual(pipeline1.in_2, in_2)
        self.assertEqual(pipeline1.out, out)

        self.assertEqual(type(pipeline1.in_1), list)
        self.assertEqual(type(pipeline1.in_2), list)
        self.assertEqual(type(pipeline1.out), list)

        for idx, element in enumerate(pipeline1.in_1):
            self.assertEqual(element, in_1[idx])
            self.assertEqual(type(element), str)

        for idx, element in enumerate(pipeline1.in_2):
            self.assertEqual(element, in_2[idx])
            self.assertEqual(type(element), str)

        for idx, element in enumerate(pipeline1.out):
            self.assertEqual(element, out[idx])
            self.assertEqual(type(element), str)

        # Verifying the dictionary
        dic = load_pipeline_dictionary(self.path)
        self.assertEqual(dic["pipeline_parameters"]["in_1"], in_1)
        self.assertEqual(dic["pipeline_parameters"]["in_2"], in_2)
        self.assertEqual(dic["pipeline_parameters"]["out"], out)

        self.assertEqual(type(dic["pipeline_parameters"]["in_1"]), list)
        self.assertEqual(type(dic["pipeline_parameters"]["in_2"]), list)
        self.assertEqual(type(dic["pipeline_parameters"]["out"]), list)

        for idx, element in enumerate(dic["pipeline_parameters"]["in_1"]):
            self.assertEqual(element, in_1[idx])
            self.assertEqual(type(element), str)

        for idx, element in enumerate(dic["pipeline_parameters"]["in_2"]):
            self.assertEqual(element, in_2[idx])
            self.assertEqual(type(element), str)

        for idx, element in enumerate(dic["pipeline_parameters"]["out"]):
            self.assertEqual(element, out[idx])
            self.assertEqual(type(element), str)

    def test_list_list(self):
        def create_pipeline():
            pipeline = Capsul.custom_pipeline()
            pipeline.add_process("node_1", TestListList)
            pipeline.export_parameter("node_1", "in_1", "in_1")
            pipeline.export_parameter("node_1", "in_2", "in_2")
            pipeline.export_parameter("node_1", "out", "out")
            return pipeline

        in_1 = [[1, 1, 1], [2, 2, 2], [3, 3, 3]]
        in_2 = [[2, 2, 2], [3, 3, 3], [4, 4, 4]]
        out = [3, 5, 7]

        pipeline1 = create_pipeline()
        pipeline1.in_1 = in_1
        pipeline1.in_2 = in_2

        with self.capsul.engine() as ce:
            ce.run(pipeline1, timeout=5)

        save_pipeline_parameters(self.path, pipeline1)

        # Reinitializing pipeline and loading parameters
        pipeline1 = create_pipeline()
        load_pipeline_parameters(self.path, pipeline1)
        self.assertEqual(pipeline1.in_1, in_1)
        self.assertEqual(pipeline1.in_2, in_2)
        self.assertEqual(pipeline1.out, out)

        self.assertEqual(type(pipeline1.in_1), list)
        self.assertEqual(type(pipeline1.in_2), list)
        self.assertEqual(type(pipeline1.out), list)

        for idx, element in enumerate(pipeline1.in_1):
            self.assertEqual(element, in_1[idx])
            self.assertEqual(type(element), list)

        for idx, element in enumerate(pipeline1.in_2):
            self.assertEqual(element, in_2[idx])
            self.assertEqual(type(element), list)

        for idx, element in enumerate(pipeline1.out):
            self.assertEqual(element, out[idx])
            self.assertEqual(type(element), int)

        # Verifying the dictionary
        dic = load_pipeline_dictionary(self.path)
        self.assertEqual(dic["pipeline_parameters"]["in_1"], in_1)
        self.assertEqual(dic["pipeline_parameters"]["in_2"], in_2)
        self.assertEqual(dic["pipeline_parameters"]["out"], out)

        self.assertEqual(type(dic["pipeline_parameters"]["in_1"]), list)
        self.assertEqual(type(dic["pipeline_parameters"]["in_2"]), list)
        self.assertEqual(type(dic["pipeline_parameters"]["out"]), list)

        for idx, element in enumerate(dic["pipeline_parameters"]["in_1"]):
            self.assertEqual(element, in_1[idx])
            self.assertEqual(type(element), list)

        for idx, element in enumerate(dic["pipeline_parameters"]["in_2"]):
            self.assertEqual(element, in_2[idx])
            self.assertEqual(type(element), list)

        for idx, element in enumerate(dic["pipeline_parameters"]["out"]):
            self.assertEqual(element, out[idx])
            self.assertEqual(type(element), int)

    def test_date_time(self):
        def create_pipeline():
            pipeline = Capsul.custom_pipeline()
            pipeline.add_process("node_1", TestDateTime)
            pipeline.export_parameter("node_1", "in_1", "in_1")
            pipeline.export_parameter("node_1", "in_2", "in_2")
            pipeline.export_parameter("node_1", "out", "out")
            return pipeline

        in_1 = datetime(2008, 6, 5)
        in_2 = time(14, 4, 5)
        out = [in_1, in_2]

        pipeline1 = create_pipeline()
        pipeline1.in_1 = in_1
        pipeline1.in_2 = in_2

        with self.capsul.engine() as ce:
            ce.run(pipeline1, timeout=5)
        pipeline1.out

        save_pipeline_parameters(self.path, pipeline1)

        # Reinitializing pipeline and loading parameters
        pipeline1 = create_pipeline()
        load_pipeline_parameters(self.path, pipeline1)
        self.assertEqual(pipeline1.in_1, in_1)
        self.assertEqual(pipeline1.in_2, in_2)
        self.assertEqual(pipeline1.out, out)

        self.assertEqual(type(pipeline1.out), list)

        for idx, element in enumerate(pipeline1.out):
            self.assertEqual(element, out[idx])
            self.assertEqual(type(element), type(out[idx]))

        # Verifying the dictionary
        dic = load_pipeline_dictionary(self.path)
        self.assertEqual(dic["pipeline_parameters"]["in_1"], str(json_encode(in_1)))
        self.assertEqual(dic["pipeline_parameters"]["in_2"], str(json_encode(in_2)))
        self.assertEqual(dic["pipeline_parameters"]["out"], json_encode(out))

        self.assertEqual(type(dic["pipeline_parameters"]["in_1"]), str)
        self.assertEqual(type(dic["pipeline_parameters"]["in_2"]), str)
        self.assertEqual(type(dic["pipeline_parameters"]["out"]), list)

        for idx, element in enumerate(pipeline1.out):
            self.assertEqual(element, out[idx])
            self.assertEqual(type(element), type(out[idx]))
