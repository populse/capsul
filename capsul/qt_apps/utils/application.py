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
import optparse
import logging
import warnings

# Soma import
from soma.qt_gui.qt_backend import QtGui, QtCore


class Application(QtGui.QApplication):
    """ Base Aplication class.

    Used to set some user options
    """

    def __init__(self, extra_options=None):
        """ Method to initialize the Application class.

        The capsulview application can be executed with command
        line options (that can also be passed to the class constructor
        as extra_options). From the command line, we can set the
        debug level with the -d option:
        * debug
        * info
        * warning
        * error
        * critical

        For exemple:
        >>> capsulview -d debug

        The default mode is error.

        From the command line we can also redirect all messages
        to a graphical message box with the -r option:
        >>> capsulview -r

        Parameters
        ----------
        extra_options: list (optional)
            some additional options that are not passed through the command
            line.
        """
        # Inheritance
        QtGui.QApplication.__init__(self, [])

        # Extra application options
        extra_options = extra_options or []

        # Define a mapping to the logging level
        levels = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL
        }

        # Parse command line and internal options
        parser = optparse.OptionParser()
        parser.add_option("-d", "--debug", dest="debug",
                          help="Set the logging level "
                               "(debug, info, warning, error, or critical",
                          metavar="LEVEL")
        parser.add_option("-r", "--redirect-to-messagebox", dest="redirect",
                          action="store_true", default=False,
                          help="Redirect all messages to the console")
        for args, kwargs in extra_options:
            parser.add_option(*args, **kwargs)
        self.options, self.arguments = parser.parse_args()

        # Logging format
        logging_format = ("[%(asctime)s] "
                          "{%(pathname)s:%(lineno)d} "
                          "%(levelname)s - %(message)s")
        date_format = "%Y-%m-%d %H:%M:%S"

        # If the logging level is specified
        if self.options.debug is not None:

            # Get the real logging level from the mapping
            level = levels.get(self.options.debug, None)

            # If a no valid logging level is found raise an Exception
            if level is None:
                raise Exception("Warning : unknown logging level "
                                "{0}".format(self.options.debug))

            # Configure the logging module
            logging.basicConfig(level=level, format=logging_format,
                                datefmt=date_format)

            # Disable deprecation warnings if we are not in the debug mode
            if level != logging.DEBUG:
                warnings.simplefilter("ignore", DeprecationWarning)

        # Set the default logging level
        else:
            logging.basicConfig(level=logging.ERROR, format=logging_format,
                                datefmt=date_format)

            # Disable deprecation warnings
            warnings.simplefilter("ignore", DeprecationWarning)

        # Check if the redirection option is found: redirecect stdout and
        # stderr to a message box
        if self.options.redirect:

            # Create a message box
            self.message_box = QtGui.QTextEdit()

            # Redirect stdout and stderr
            sys.stdout = EmittingStream()
            sys.stderr = EmittingStream()

            # Connect with text written signal
            self.connect(sys.stdout,
                         QtCore.SIGNAL('textWritten(QString)'),
                         self._on_text_print)
            self.connect(sys.stderr,
                         QtCore.SIGNAL('textWritten(QString)'),
                         self._on_text_print)

            # Update root logger handler
            root_logger = logging.getLogger()
            h = root_logger.handlers[0]
            h.stream = sys.stdout

    def _on_text_print(self, text):
        """Append text to the QTextEdit.

        Parameters
        ----------
        text: str (mandatory)
            the text to write
        """
        self.message_box.append(text)
        self.message_box.show()


class EmittingStream(QtCore.QObject):
    """ Logging emitting string basic handler.
    """
    def write(self, text):
        self.textWritten.emit(str(text))
