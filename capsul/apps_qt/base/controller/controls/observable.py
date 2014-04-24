#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################


class SignalObject(object):
    """ Dummy class for signals.
    """
    pass


class Observable(object):
    """ Base class for observable classes.
        This class defines a simple interface to add or remove observers
        on an object
    """

    def __init__(self, signals):
        self._allowed_signals = []
        self._observers = {}

        # Init allowed signals
        for signal in signals:
            self._allowed_signals.append(signal)
            self._observers[signal] = []

        # A locked option to avoid multiple observer notifications.
        self._locked = False

    def add_observer(self, signal, observer):
        """ Add an observer to the objec:
            return False if the observer exists,
            otherwise return True.
        """
        self._is_allowed_signal(signal)
        self._add_observer(signal, observer)

    def remove_observer(self, signal, observer):
        """ Remove an observer from the object:
            return False if the observer does not exist
            otherwise return True.
        """
        self._is_allowed_event(signal)
        self._remove_observer(signal, observer)

    def notify_observers(self, signal, *args, **kwargs):
        """ Notify observers of a given signal :
            return Fasle if we already proccess a signal
            otherwise return True.
        """
        # We are already processing a signal
        if self._locked:
            return False

        self._locked = True  # lock signal

        signal_info = SignalObject()
        setattr(signal_info, "object", self)
        setattr(signal_info, "signal", signal)
        for name, value in kwargs.items():
            setattr(signal_info, name, value)

        for observer in self._observers[signal]:
            observer(signal_info)

        self._locked = False  # unlock signal

    ##############
    # Properties #
    ##############

    def _get_allowed_signals(self):
        """ Events allowed for the current object.
        """
        return self._allowed_signals

    allowed_signals = property(_get_allowed_signals)

    #####################
    # Private interface #
    #####################

    def _is_allowed_signal(self, signal):
        if signal not in self._allowed_signals:
            raise Exception("Signal {0} is not allowed for"
                            "type {1} ".format(signal, str(type(self))))

    def _add_observer(self, signal, observer):
        if observer not in self._observers[signal]:
            self._observers[signal].append(observer)

    def _remove_observer(self, signal, observer):
        if observer in self._observers[signal]:
            index = self._observers[signal].index(observer)
            del self._observers[signal][index]

