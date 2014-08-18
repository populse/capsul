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
import logging

# Trait import
from traits.api import *

# Qt import
from PySide.QtGui import QApplication

# Capsul import
from capsul.qt_gui.controller_widget import (
    ControllerWidget, ScrollControllerWidget)

# Soma import
from soma.controller import Controller


class Point(Controller):
    x = Float()
    y = Float()


class TestControls(Controller):
    """ A dummy class to test all available controls.
    """

    # Global parameters
    # Traits we want to parametrized thanks to control widgets
    enum = Enum("1", "2", "3")
    i = Int()
    s = Str()
    f = Float()
    b = Bool()
    fp = File()
    dp = Directory()
    l = List(Float())
    ll = List(List(Float()))
    lll = List(List(List(Str())))

    def __init__(self):
        """" Initialize the TestControls class.
        """
        # Inheritance
        super(TestControls, self).__init__()

        # Set some default values
        self.l = [3.2, 0.5]
        self.ll = [[3.2, 0.5],  [1.1, 0.9]]
        self.lll = [[["a", "b", ""]], [["aa", "", "ff"]], [["s"]]]


# Set the logging level
logging.basicConfig(level=logging.INFO)

# Create a qt applicaction
app = QApplication(sys.argv)

# Create the controller we want to parametrized
controller = TestControls()

# Set some values to the controller parameters
controller.s = ""
controller.f = 10.2

# Create to controller widget that are synchronized on the fly
widget1 = ScrollControllerWidget(controller, live=True)
widget2 = ControllerWidget(controller, live=True)
widget1.show()
widget2.show()

# Check if the controller widget is valid before edition
print "Controller widget valid before edition: ",
print widget1.controller_widget.is_valid()

# Start the qt loop
app.exec_()

# Check if the controller widget is valid after edition
print "Controller widget valid after edition: ",
print widget1.controller_widget.is_valid()
