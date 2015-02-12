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
import os
from PySide import QtGui

# CAPSUL import
from capsul.utils.xml_to_pipeline import parse_pipeline_description
from capsul.utils.test.pipeline import XmlPipeline
from capsul.utils.test.pipeline import XmlIterativePipeline
from capsul.qt_gui.widgets import PipelineDevelopperView


if __name__ == "__main__":
    pipeline = XmlPipeline()
    iterative_pipeline = XmlIterativePipeline()

    app = QtGui.QApplication(sys.argv)
    view1 = PipelineDevelopperView(pipeline)
    view1.show()
    view2 = PipelineDevelopperView(iterative_pipeline)
    view2.show()
    app.exec_()
    del view1
    del view2

