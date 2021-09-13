# -*- coding: utf-8 -*-
'''
Classes
=======
:class:`PipelineViewerApp`
--------------------------
'''

# System import
from __future__ import absolute_import
import os
import logging

# Define the logger
logger = logging.getLogger(__name__)

# Capsul import
from capsul.qt_apps.utils.application import Application
from capsul.qt_apps.main_window import CapsulMainWindow
from capsul.qt_apps.utils.find_pipelines import find_pipelines_from_description
import capsul.qt_apps.resources as resources
from capsul.plugins import PLUGS


class PipelineViewerApp(Application):
    """ CAPSULVIEW Application.
    """

    # Load some meta information
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
        # First set some meta information
        self.setApplicationName(self._application_name)
        self.setOrganizationName(self._organisation_name)
        self.setApplicationVersion(self._version)

        # Get the user interface description from capsul resources
        ui_file = os.path.join(resources.__path__[0], "capsul.ui")

        # List capsul declared plugins (set of pipelines).
        if self.options.test:
            pipeline_menu = {
                "capsul": {
                    "utils": {
                        "test": {
                            "pipeline": {
                                "XmlPipeline": [""]
                            }
                        }
                    }
                }
            }
        else:
            pipeline_menu = {}
        for module_name, doc_url in PLUGS:
            pipeline_menu.update(
                find_pipelines_from_description(module_name, doc_url)[0])

        # Create and show the main window
        self.window = CapsulMainWindow(pipeline_menu, ui_file)
        self.window.show()

        return True
