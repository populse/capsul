#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import os

# Capsul import
from capsul.qt_apps.utils.application import Application
from capsul.qt_apps.main_window import CapsulMainWindow
from capsul.qt_apps.utils.find_pipelines import find_pipelines
import capsul.qt_apps.resources as resources
from capsul.plugins import PLUGS


class PipelineViewerApp(Application):
    """ CAPSULVIEW Application.
    """

    # Load some meta informations
    from capsul.info import __version__ as _version
    from capsul.info import NAME as _application_name
    from capsul.info import ORGANISATION as _organisation_name

    def __init__(self, *args, **kwargs):
        """ Method to initialize the PipelineViewerApp class.
        """
        # Inhetritance
        super(PipelineViewerApp, self).__init__(*args, **kwargs)

        # Initialize the application
        self.window = None
        self.init_window()

    def init_window(self):
        """ Method to initialize the main window.
        """
        # First set some meta informations
        self.setApplicationName(self._application_name)
        self.setOrganizationName(self._organisation_name)
        self.setApplicationVersion(self._version)

        # Get the user interface description from capsul resources
        ui_file = os.path.join(resources.__path__[0], "capsul.ui")

        # List capsul declared plugins (set of pipelines).
        pipeline_menu = {}
        for module_name, doc_url in PLUGS:
            pipeline_menu.update(find_pipelines(module_name, doc_url)[0])

        # Create and show the main window
        self.window = CapsulMainWindow(pipeline_menu, ui_file)
        self.window.show()

        return True
