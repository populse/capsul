#! /usr/bin/env python
##########################################################################
# Caspul - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import logging

# Define the logger
logger = logging.getLogger(__name__)

# Trait import
from traits.api import HasTraits, Event, CTrait

# Soma import
from soma.sorted_dictionary import SortedDictionary


class ControllerMeta(HasTraits.__metaclass__):
    """ This metaclass allows for automatic registration of factories.
    """
    def __new__(mcs, name, bases, dictionary):
        """ Method that can be used to define factories.

        Parameters
        ----------
        mcls: meta class (mandatory)
            a meta class.
        name: str (mandatory)
            the controller class name.
        bases: tuple (mandatory)
            the direct base classes.
        attrs: dict (mandatory)
            a dictionnary with the class attributes.
        """
        return super(ControllerMeta, mcs).__new__(mcs, name, bases, dictionary)


class Controller(HasTraits):
    """ A Controller contains some traits: attributes typing and observer
    (callback) pattern.

    The class provides some methods to add/remove/inspect user defined traits.

    Attributes
    ----------
    `user_traits_changed` : Event
        single event that can be send when several traits changes. This event
        have to be triggered explicitely to take into account changes due to
        call(s) to add_trait or remove_trait.

    Methods
    -------
    user_traits
    is_user_trait
    add_trait
    remove_trait
    _clone_trait
    """
    # Meta class used to defined factories
    __metaclass__ = ControllerMeta

    # This event is necessary because there is no event when a trait is
    # removed with remove_trait and because it is sometimes better to send
    # a single event when several traits changes are done (especially
    # when GUI is updated on real time). This event have to be triggered
    # explicitely to take into account changes due to call(s) to
    # add_trait or remove_trait.
    user_traits_changed = Event

    def __init__(self, *args, **kwargs):
        """ Initilaize the Controller class.

        During the class initialization create a class attribute
        '_user_traits' that contains all the class traits and instance traits
        defined by user (i.e.  the traits that are not automatically
        defined by HasTraits or Controller). We can access this class
        parameter with the 'user_traits' method.

        If user trait parameters are defined directly on derived class, this
        procedure call the 'add_trait' method in order to not share
        user traits between instances.
        """
        # Inheritance
        super(Controller, self).__init__(*args, **kwargs)

        # Create a sorted dictionnary with user parameters
        # The dictionary order correspond to the definition order
        self._user_traits = SortedDictionary()

        # Get all the class traits
        class_traits = self.class_traits()

        # If some traits are defined on the controller, create a list
        # with definition ordered trait name. These names will correspond
        # to user trait sorted dictionary keys
        if class_traits:
            sorted_names = sorted(
                (getattr(trait, "order", ""), name)
                for name, trait in class_traits.iteritems()
                if self.is_user_trait(trait))
            sorted_names = [sorted_name[1] for sorted_name in sorted_names]

            # Go through all trait names that have been ordered
            for name in sorted_names:

                # If the trait is defined on the class, need to clone
                # the class trait and add the cloned trait to the instance.
                # This step avoids us to share trait objects between
                # instances.
                if name in self.__base_traits__:
                    logger.debug("Add class parameter '{0}'.".format(name))
                    trait = class_traits[name]
                    self.add_trait(name, self._clone_trait(trait))

                # If the trait is defined on the instance, just
                # add the user parameter to the '_user_traits' instance
                # parameter
                else:
                    logger.debug("Add instance parameter '{0}'.".format(name))
                    self._user_traits[name] = class_traits[name]

    ####################################################################
    # Private methods
    ####################################################################

    def _clone_trait(self, clone, metadata=None):
        """ Creates a clone of a specific trait (ie. the same trait
        type but different ids).

        Parameters
        ----------
        clone: CTrait (mandatory)
            the input trait to clone.
        metadata: dict (opional, default None)
            some metadata than can be added to the trait __dict__.

        Returns
        -------
        trait: CTrait
            the cloned input trait.
        """
        # Create an empty trait
        trait = CTrait(0)

        # Clone the input trait in the empty trait structure
        trait.clone(clone)

        # Set the input trait __dict__ elements to the cloned trait
        # __dict__
        if clone.__dict__ is not None:
            trait.__dict__ = clone.__dict__.copy()

        # Update the cloned trait __dict__ if necessary
        if metadata is not None:
            trait.__dict__.update(metadata)

        return trait

    ####################################################################
    # Public methods
    ####################################################################

    def user_traits(self):
        """ Methood to access the user parameters.

        Returns
        -------
        out: dict
            a dictionnary containing class traits and instance traits
            defined by user (i.e.  the traits that are not automatically
            defined by HasTraits or Controller). Returned values are
            sorted according to the 'order' trait meta-attribute.
        """
        return self._user_traits

    def is_user_trait(self, trait):
        """ Method that evaluate if a trait is a user parameter
        (i.e. not an Event).

        Returns
        -------
        out: bool
            True if the trait is a user trait,
            False otherwise.
        """
        return not isinstance(trait.handler, Event)

    def add_trait(self, name, *trait):
        """ Add a new trait.

        Parameters
        ----------
        name: str (mandatory)
            the trait name.
        trait: traits.api (mandatory)
            a valid trait.
        """
        # Debug message
        logger.debug("Adding trait '{0}'...".format(name))

        # Inheritance: create the instance trait attribute
        super(Controller, self).add_trait(name, *trait)

        # Get the trait instance and if it is a user trait load the traits
        # to get it direcly from the instance (as a property) and add it
        # to the class '_user_traits' attributes
        trait_instance = self.trait(name)
        if self.is_user_trait(trait_instance):
            trait_instance.defaultvalue = trait_instance.default
            self.get(name)
            self._user_traits[name] = trait_instance

    def remove_trait(self, name):
        """ Remove a trait from its name.

        Parameters
        ----------
        name: str (mandatory)
            the trait name to remove.
        """
        # Debug message
        logger.debug("Removing trait '{0}'...".format(name))

        # Call the Traits remove_trait method
        super(Controller, self).remove_trait(name)

        # Remove name from the '_user_traits' without error if it
        # is not present
        self._user_traits.pop(name, None)
