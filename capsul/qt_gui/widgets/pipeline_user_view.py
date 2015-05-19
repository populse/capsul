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
import tempfile
from subprocess import check_call

# Soma import
from soma.qt_gui.qt_backend import QtGui


class PipelineUserView(QtGui.QWidget):
    """ A widget to visualize a pipeline as a simple workflow.

    Uses Graphviz `dot` tool.
    """
    def __init__(self, pipeline):
        """ Initialize the WorkflowViewer class
        """
        # Inheritance
        super(PipelineUserView, self).__init__()

        # Class attributets
        self.pipeline = pipeline

        # Initialize the widget
        layout = QtGui.QVBoxLayout(self)
        self.label = QtGui.QLabel()
        layout.addWidget(self.label)
        #self.setLayout(layout)

        self.update()

    def update(self):
        image = tempfile.NamedTemporaryFile(suffix=".png")
        dot = tempfile.NamedTemporaryFile(suffix=".png")
        self.write(dot)
        dot.flush()
        check_call(["dot", "-Tpng", "-o", image.name, dot.name])
        self.pixmap = QtGui.QPixmap(image.name)  # .scaledToHeight(600)
        self.label.setPixmap(self.pixmap)

    def write(self, out=sys.stdout):
        graph = self.pipeline.workflow_graph()
        print >> out, 'digraph workflow {'
        ids = {}
        for n in graph._nodes:
            id = str(len(ids))
            ids[n] = id
            print >> out, '  %s [label="%s"];' % (id, n)
        for n, v in graph._links:
            print >> out, '  %s -> %s;' % (ids[n], ids[v])
        print >> out, '}'
