# -*- coding: utf-8 -*-
'''
A tool to debug and inspect nodes activation / deactivation in a pipeline.

Classes
=======
:class:`ActivationInspectorApp`
-------------------------------
:class:`ActivationInspector`
----------------------------
'''

# System import
from __future__ import print_function
from __future__ import absolute_import
import os
import re
import logging
import tempfile
import six

# Define the logger
logger = logging.getLogger(__name__)

# Soma import
from soma.qt_gui import qt_backend
from soma.qt_gui.qt_backend import QtGui
from soma.qt_gui.controller_widget import ScrollControllerWidget

# Capsul import
from capsul.qt_apps.utils.application import Application
import capsul.qt_apps.resources as resources
from capsul.api import get_process_instance
from capsul.qt_gui.widgets import PipelineDeveloperView
from capsul.pipeline.pipeline_nodes import PipelineNode


class ActivationInspectorApp(Application):
    """ ActivationInspector Application.
    While developing a pipeline, nodes are connected through links. Nodes will be automatically activated or disabled depending on their connections (a mandatory link to a disabled node will disable the current one).
    You will often wonder why a node will not be activated. This tool helps to determine when and why by "playing" activation rules sequences step-by-step and displaying nodes which activate or deactivate at each step.
    """
    # Load some meta information
    from capsul.info import __version__ as _version
    from capsul.info import NAME as _application_name
    from capsul.info import ORGANISATION as _organisation_name

    def __init__(self, pipeline_path, record_file=None, *args, **kwargs):
        """ Method to initialize the ActivationInspectorApp class.

        Parameters
        ----------
        pipeline_path: str (mandatory)
            the name of the pipeline we want to load.
        record_file: str (optional)
            a file where the pipeline activation steps are stored.
        """
        # Inhetritance
        super(ActivationInspectorApp, self).__init__(*args, **kwargs)

        # Load the pipeline
        self.pipeline = get_process_instance(pipeline_path)

        # Initialize the application
        self.record_file = record_file
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
        ui_file = os.path.join(
            os.path.dirname(__file__), "activation_inspector.ui")
        #ui_file = os.path.join(resources.__path__[0], "activation_inspector.ui")

        # Create and show the activation/pipeline/controller windows
        self.pipeline_window = PipelineDeveloperView(self.pipeline, show_sub_pipelines=True)
        self.controller_window = ScrollControllerWidget(self.pipeline,live=True)
        self.activation_window = ActivationInspector(
            self.pipeline, ui_file, self.record_file,
            developper_view=self.pipeline_window)
        self.pipeline_window.show()
        self.activation_window.show()
        self.controller_window.show()

        return True

class ActivationInspector(QtGui.QWidget):
    """ A Widget to display the pipeline activation process step by step.
    """
    def __init__(self, pipeline, ui_file=None, record_file=None,
                 developper_view=None, parent=None):
        """ Initialize the ActivationInspector class.

        Parameters
        ----------
        pipeline: capsul.Pipeline (mandatory)
            the pipeline we want to inspect.
        ui_file: str (optional)
            the path to the qt user interface description file.
            If not specified, it will find its standard one.
        record_file: str (optional)
            a file path where the activation steps are recorded.
            If not specified (None), it will create a temporary file.
        developper_view: PipelineDeveloperView (optional)
            if specified it is possible to click on a plug to set a filter
            pattern and to update the pipeline activation accordingly.
        """
        # Inheritance: create the application
        QtGui.QWidget.__init__(self, parent)

        # load the user interface window
        if ui_file is None:
            ui_file = os.path.join(
                os.path.dirname(__file__), "activation_inspector.ui")

        self.ui = qt_backend.loadUi(ui_file)

        # Define dynamic controls
        self.controls = {
            QtGui.QListWidget: ["events"],
            QtGui.QPushButton: ["btnUpdate", "next", "previous"],
            QtGui.QLineEdit: ["pattern"]
        }

        if record_file is None:
            record_file_s = tempfile.mkstemp()
            record_file = record_file_s[1]
            os.close(record_file_s[0])
            print('temporary record file:', record_file)
            class AutoDeleteFile(object):
                def __init__(self, record_file):
                    self.record_file = record_file
                def __del__(self):
                    try:
                        os.unlink(self.record_file)
                    except OSError:
                        pass
            self._autodelete_record_file = AutoDeleteFile(record_file)

        # Add ui class parameter with the dynamic controls and initialize
        # default values
        self.add_controls_to_ui()

        # Store class parameters
        self.pipeline = pipeline
        self.record_file = record_file
        self.developper_view = developper_view

        # Set the pipeline record file if folder exists
        if os.path.isdir(os.path.dirname(self.record_file)):
            self.pipeline._debug_activations = self.record_file
        else:
            raise ValueError(
                "The record file '{0}' can't be created since the "
                "base directory does not exists.".format(self.record_file))

        # Execute the pipeline activation method
        self.pipeline.update_nodes_and_plugs_activation()

        # Refresh the pipeline activation displayed list
        self.refresh_activation_from_record()

        # Signals for window interface
        self.ui.events.currentRowChanged.connect(
            self.update_pipeline_activation)
        self.ui.btnUpdate.clicked.connect(
            self.refresh_activation_from_record)
        self.ui.next.clicked.connect(self.find_next)
        self.ui.previous.clicked.connect(self.find_previous)

        # Dynamically select a filter rule by clicking on the pipeline view
        # plugs
        if developper_view is not None:
          developper_view.plug_clicked.connect(self.set_filter_pattern)

    def show(self):
        """ Shows the widget and its child widgets.
        """
        self.ui.show()

    def add_controls_to_ui(self):
        """ Method to find dynamic controls
        """
        # Error message template
        error_message = "{0} has no attribute '{1}'"

        # Got through the class dynamic controls
        for control_type, control_item in six.iteritems(self.controls):

            # Get the dynamic control name
            for control_name in control_item:

                # Try to set the control value to the ui class parameter
                try:
                    value = self.ui.findChild(control_type, control_name)
                    if value is None:
                        logger.error(error_message.format(
                            type(self.ui), control_name))
                    setattr(self.ui, control_name, value)
                except Exception:
                    logger.error(error_message.format(
                        type(self.ui), control_name))

    ###########################################################################
    # Slots   
    ###########################################################################

    def refresh_activation_from_record(self):
        """ Method to display pipeline activation steps from the recorded file.
        """
        # Open the last recorded activation file
        with open(self.record_file) as openrecord:

            # Get the header of the file that contains the pipeline identifier
            # of the recorded activation
            record_pipeline_id = openrecord.readline().strip()
            if record_pipeline_id != self.pipeline.id:
                raise ValueError(
                    "'{0}' recorded activations for pipeline '{1}' but not for "
                    "'{2}'".format(self.record_file, record_pipeline_id, 
                                   self.pipeline.id))

            # Clear the list where the recorded activation is displayed
            self.ui.events.clear()

            # Parse the recorded activation file

            # > Store the activation stack step by step to dynamically replay
            # the activation
            self.activations = []
            current_activations = {}

            # > Go through all the activation steps
            parser = re.compile(r"(\d+)([+-=])([^:]*)(:([a-zA-Z_0-9]+))?")
            for activation_step in openrecord.readlines():

                # > Parse the line
                iteration, activation, node, x, plug = parser.match(
                    activation_step.strip()).groups()
                plug = plug or ""

                # > Store the current activation stack
                if activation == "+":
                    current_activations["{0}:{1}".format(node, plug)] = True
                else:
                    del current_activations["{0}:{1}".format(node, plug)]
                self.activations.append(current_activations.copy())

                # > Add a line to the activation display
                self.ui.events.addItem("{0}{1} {2}:{3}".format(
                    iteration, activation, node, plug))

            # Select the last activation step so the pipeline will be
            # in his final configuration
            self.ui.events.setCurrentRow(self.ui.events.count() - 1)

    def update_pipeline_activation(self, index):
        """ Method that is used to replay the activation step by step.

        When a specific activation step is selected, the pipeline will reflect
        the selected activation status
        """
        # Get the activation associated to the 'index' stack level
        activations = self.activations[index]

        # Update the pipeline activation to meet the current selection
        for node in self.pipeline.all_nodes():

            # Restore the plugs and nodes activations
            node_name = node.full_name
            for plug_name, plug in six.iteritems(node.plugs):
                plug.activated = activations.get(
                    "{0}:{1}".format(node_name, plug_name), False)
            node.activated = activations.get("{0}:".format(node_name), False)

        # Refresh views relying on plugs and nodes selection
        for node in self.pipeline.all_nodes():
            if isinstance(node, PipelineNode):
                node.process.selection_changed = True

    def find_next(self):
        """ Forward search for a pattern in the activation list.

        Returns
        -------
        is_found: int
            1 if a match has been found, 0 otherwise.
        """
        # Build the search pattern
        pattern = re.compile(self.ui.pattern.text())

        # Forward search
        # > Get the next (n+1) activation row
        next_activation_row = self.ui.events.currentRow() + 1
        # > Search recursively until a match is found
        while next_activation_row < self.ui.events.count():
            if pattern.search(self.ui.events.item(next_activation_row).text()):
                self.ui.events.setCurrentRow(next_activation_row)
                return 1
            next_activation_row += 1

        return 0
        
    def find_previous(self):
        """ Backward search for a pattern in the activation list.

        Returns
        -------
        is_found: bool
            True if a match has been found, False otherwise.
        """
        # Build the search pattern
        pattern = re.compile(self.ui.pattern.text())

        # Backward search
        # > Get the previous (n-1) activation row
        previous_activation_row = self.ui.events.currentRow() - 1
        # > Search recursively until a match is found
        while previous_activation_row > 0:
            if pattern.search(self.ui.events.item(previous_activation_row).text()):
                self.ui.events.setCurrentRow(previous_activation_row)
                return 1
            previous_activation_row -= 1

        return 0

    def set_filter_pattern(self, filter_pattern):
        """ Method that set a filter pattern.

        Try a forward search followed by a backward one.

        Parameters
        ----------
        filter_pattern: str (mandatory)
            the filter pattern we want to set.
        """
        # Display the filter pattern
        self.ui.pattern.setText(filter_pattern)

        # Try to select an item corresponding to the filter pattern
        if not self.find_next():
            self.find_previous()


if __name__ == "__main__":
    """ Command example:
    >>> python activation_inspector.py -p funtk.connectivity.conn.Conn 
        -r ~/tmp/conn_activation.txt
    """
    # Create a tool we can control easily
    import sys
    from optparse import OptionParser

    # Define activation inspector options
    parser = OptionParser()
    parser.add_option("-p", "--pipeline",
                      dest="pipeline_path",
                      help=("the pipeline path we want to investigate: "
                            "module1.module2.Pipeline."))
    parser.add_option("-r", "--record",
                      dest="record_file",
                      help="the file where the activation steps are recorded.")
    (options, args) = parser.parse_args()
    sys.argv = []

    # Start the application
    if QtGui.QApplication.instance() is None:
        app = ActivationInspectorApp(options.pipeline_path, options.record_file)
        sys.exit(app.exec_())
