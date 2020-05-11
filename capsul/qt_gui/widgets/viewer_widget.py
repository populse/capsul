# -*- coding: utf-8 -*-
'''
Result viewer

Classes
=======
:class:`ViewerWidget`
---------------------
'''

# System import
from __future__ import absolute_import
import logging
import os

import six

# Soma import
from soma.controller.trait_utils import trait_ids
import soma.subprocess
from soma.qt_gui.qt_backend import QtGui, QtCore

# Qt import
try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s


class ViewerWidget(QtGui.QWidget):
    """ View result class
    """

    def __init__(self, viewer_node_name, pipeline, study_config):
        """ Method to initialize a ViewerWidget class.

        Parameters
        ----------
        viewer_node_name: str
            the name of the node containing the viewer process
        pipeline: str
            the full pipeline in order to get the viewer input trait values
            since the viewer node is unactivated
        """
        # Inheritance
        super(ViewerWidget, self).__init__()

        # Default parameters
        self.viewer_node_name = viewer_node_name
        self.pipeline = pipeline
        self.study_config = study_config

        # Build control
        button = QtGui.QToolButton(self)
        button.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        button.setMinimumHeight(50)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(_fromUtf8(":/icones/view_result")),
                       QtGui.QIcon.Normal, QtGui.QIcon.Off)
        button.setIcon(icon)
        button.clicked.connect(self.onCreateViewerClicked)

    def onCreateViewerClicked(self):
        """ Event to create the viewer
        """
        # Get the viewer node and process
        viewer_node = self.pipeline.nodes[self.viewer_node_name]
        viewer_process = viewer_node.process

        # Propagate the parameters to the input viewer node
        # And check if the viewer is active (ie dependencies
        # are specified -> corresponding process have run)
        is_viewer_active = True
        for plug_name, plug in six.iteritems(viewer_node.plugs):

            if plug_name in ["nodes_activation", "selection_changed"]:
                continue

            # Since it is a viewer node we normally have only inputs
            for (source_node_name, source_plug_name, source_node,
                 source_plug, weak_link) in plug.links_from:

                # Get the source plug value and source trait
                source_plug_value = getattr(source_node.process,
                                            source_plug_name)
                source_trait = source_node.process.trait(source_plug_name)

                # Check if the viewer is active:
                # 1) the source_plug_value has been set
                if source_plug_value == source_trait.handler.default_value:
                    is_viewer_active = False
                    break
                # 2) if the plug is a file, the file exists
                str_description = trait_ids(source_trait)
                if (len(str_description) == 1 and
                   str_description[0] == "File" and
                   not os.path.isfile(source_plug_value)):

                    is_viewer_active = False
                    break

                # Update destination trait
                setattr(viewer_process, plug_name, source_plug_value)

            # Just stop the iterations if the status of the viewer
            # is alreadu known
            if not is_viewer_active:
                break

        # Execute the viewer process using the defined study configuration
        if is_viewer_active:
            soma.subprocess.Popen(viewer_process.get_commandline())
            # self.study_config.run(viewer_process)
        else:
            logging.error("The viewer is not active yet, maybe "
                          "because the processings steps have not run or are "
                          "not finished.")
