#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

"""This module enables to create automatic links between an object and a
traits based controller."""

try:
    from traits.api import HasTraits, Event
except ImportError:
    from enthought.traits.api import HasTraits, Event

from weakref import WeakKeyDictionary
from capsul.utils.functiontools import partial
#from capsul.utils.sorted_dictionary import SortedDictionary
from collections import OrderedDict

from capsul.controller.factory import Factories

global_compt_order=0


class ControllerFactories( Factories ):
    """Holds association between an object and its controller"""
    def __init__( self ):
        super( ControllerFactories, self ).__init__()
        self._controllers = WeakKeyDictionary()

    def get_controller( self, instance ):
        """Returns the Controller class associated to an object."""
        controller = self._controllers.get( instance )
        if controller is None:
            factory = self.get_factory( instance )
            if factory is not None:
                controller = factory( instance )
                self._controllers[ instance ] = controller
        return controller

ControllerFactories.register_global_factory( HasTraits, lambda instance: instance )



class MetaController( HasTraits.__metaclass__ ):
    """This metaclass allows for automatic registration of a Controller derived
    class for ControllerFactories (if the new class defines register_class_controller)
    and WidgetFactories (if the new class defines create_widget_from_ui)"""
    def __new__( mcs, name, bases, dictionary ):
        cls = super( MetaController, mcs ).__new__( mcs, name, bases, dictionary )

#        controlled_class = dictionary.get( 'register_class_controller' )
#        if controlled_class is not None:
#            ControllerFactories.register_global_factory( controlled_class, cls )
#
#        gui = dictionary.get('create_widget_from_ui')
#        if gui is not None:
#            from soma.gui.widget_factory import WidgetFactories, create_widget_from_ui
#            WidgetFactories.register_global_factory( cls, partial( create_widget_from_ui, gui ) )

        return cls


class Controller(HasTraits):
    """
    A Controller is a HasTraits that is connected to ControllerFactories and
    widgetFactories, it also provides some methods to inspect user defined traits
    and to raise an event if its traits have changed.
    """
    __metaclass__ = MetaController

    """
    This event is necessary because there is no event when a trait is removed
    with remove_trait and because it is sometimes better to send a single event
    when several traits changes are done (especially when GUI is updated on real
    time). This event have to be triggered explicitely to take into account
    changes due to call(s) to add_trait or remove_trait.
    """
    user_traits_changed = Event

    def __init__(self, *args, **kwargs):
        super(Controller, self).__init__(*args, **kwargs)
        self._ordered_traits = OrderedDict()

    def user_traits(self):
        """
        Returns a dictionnary containing class traits and instance traits
        defined by user (i.e.  the traits that are not automatically
        defined by HasTraits or Controller).
        Returned values are sorted according to the "order" trait
        meta-attribute.
        """
        traits = OrderedDict()
        for name, trait in self._ordered_traits.iteritems():
            if self.is_user_trait(trait):
                traits[name] = trait
        class_traits = self.class_traits()
        sorted_keys = [t[1]
            for t in sorted((getattr(trait, 'order', ''), name)
            for name, trait in class_traits.iteritems() if self.is_user_trait(trait) and name not in traits)]
        for name in sorted_keys:
            traits[name] = class_traits[name]
        return traits

        #traits = dict((i, j) for i, j in self.class_traits().iteritems()
                              #if not i.startswith('trait_'))
        #traits.update(self._instance_traits())
        ##for name in ["selection_changed", "user_traits_changed"]:
            ##if name in traits.keys():
                ##del traits[name]
        #for name in traits.keys():
            #trait = traits[name]
            #if not self.is_user_trait(trait):
                #del traits[name]
        #sorted_keys = [t[1]
            #for t in sorted((getattr(trait, 'order', ''), name)
            #for name, trait in traits.iteritems())]
        #return SortedDictionary(*[(name, traits[name])
                                        #for name in sorted_keys])

    def is_user_trait(self, trait):
        '''
        Test if a trait is a valid user trait (i.e. not an Event).
        '''
        return not isinstance(trait.handler, Event)

    def add_trait(self, name, *trait):   
       #global global_compt_order

       super(Controller, self).add_trait(name, *trait)
       #global_compt_order = global_compt_order+1
       trait_instance = self.trait(name)
       #if trait_instance.order is None:
          #print 'add_trait, name: %s, order: %d' % (name, global_compt_order)
          #trait_instance.order = global_compt_order
       trait_instance.defaultvalue = trait_instance.default
       self.get(name)
       self._ordered_traits[name] = trait_instance

    def remove_trait(self,name):
        super(Controller, self).remove_trait(name)
        del self._ordered_traits[name]

