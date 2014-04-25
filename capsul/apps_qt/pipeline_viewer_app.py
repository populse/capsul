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
from capsul.apps_qt.base.application import Application
from capsul.apps_qt.main_window import CapsulMainWindow
from capsul.apps_qt.base.find_pipelines import find_pipelines
import capsul.apps_qt.resources as resources
from capsul.plugins import PLUGS


class PipelineViewerApp(Application):
    """ CAPSULVIEW Aplication.
    """

    # Load some meta informations
    from capsul.info import __version__ as _version
    from capsul.info import NAME as _application_name
    from capsul.info import ORGANISATION as _organisation_name

    def __init__(self, *args, **kwargs):
        """ Method to initialize the CAPSUL application.
        """
        # Init application
        self.window = None
        super(PipelineViewerApp, self).__init__(*args, **kwargs)
        self.initWindow()

    def initWindow(self):
        """ Method to initialize the main window
        """
        # First set some meta informations
        self.setApplicationName(self._application_name)
        self.setOrganizationName(self._version)
        self.setApplicationVersion(self._organisation_name)

        # Get the user interface description from capsul resources
        ui_file = os.path.join(resources.__path__[0],
                               "pipeline_viewer.ui")

        # List capsul declared plugins (set of pipelines).
        pipeline_names = []
        for module_name, doc_url in PLUGS:
            item = [(x, doc_url) for x in find_pipelines(module_name)]
            pipeline_names.extend(item)

        # Create the main window
        self.window = CapsulMainWindow(pipeline_names, ui_file)
        self.window.show()

        return True