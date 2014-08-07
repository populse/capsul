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
import re

# Capsul import
from capsul.pipeline import Pipeline
from capsul.process import Process
from capsul.utils.trait_utils import clone_trait

# Soma import
from soma.controller import trait_ids
                                                                                                                

##############################################################
#               Iterative Manager Process
##############################################################

class IterativeManager(Process):
    """ Process to handle automatically the iterative input or output traits.
    """
    def __init__(self, process_name, iterative_traits, regular_traits,
                 is_input_traits=True, node=None):
        """ Initialize the IterativeManager class

        Parameters
        ----------
        process_name: str (mandatory)
            the name of the processing node
        iterative_traits: dict (mandatory)
            a dict with iterative trait name as keys that contains a 2-uplet
            with thetrait string description and the trait value.
        regular_traits: list of str (mandatory)
            a dict with regular trait name as keys that contains a 2-uplet 
            with the trait string description and the trait value.
        is_input_traits: bool (optional, default True)
            if True, the iterative traits are input traits
            otherwise, the iterative traits are output traits
        node: Node instance (optional)
            needed to synchronize the output manager outputs with the parent
            process
        """
        # Inheritance
        super(IterativeManager, self).__init__()

        # Class parameters
        self.links = []
        self.nodes = []
        self.iterative_traits = iterative_traits
        self.regular_traits = regular_traits
        self.is_input_traits = is_input_traits
        self.node = node

        # Go through all iterative traits
        for trait_name, trait_item in self.iterative_traits.iteritems():

            # Unpack trait item
            trait_description, trait_value = trait_item

            # Clone the iterative traits
            process_trait = clone_trait(trait_description)
            self.add_trait(trait_name, process_trait)
            self.trait(trait_name).optional = False
            self.trait(trait_name).output = not is_input_traits
            self.trait(trait_name).desc = "an iterative trait that need to be unpack"

            # Pass the input trait values to the iterative pipeline
            if is_input_traits:
                setattr(self, trait_name, trait_value)

            # Unpack the iterative traits
            trait_description = [
                re.sub("^List_*", "", x) for x in trait_description]
            for cnt, item in enumerate(trait_value):

                # Create one unpack trait
                unpack_trait_name = "{0}_{1}".format(trait_name, cnt + 1)
                process_trait = clone_trait(trait_description)
                self.add_trait(unpack_trait_name, process_trait)
                self.trait(unpack_trait_name).optional = False
                self.trait(unpack_trait_name).output = is_input_traits
                self.trait(unpack_trait_name).desc = "unpack iterative trait"

                # Processing node name
                node_name = "iterative_{0}_{1}".format(
                    process_name.lower(), cnt + 1)

                # Add the processing node attached with each unpack input
                if is_input_traits:
    
                    # Add the processing node
                    if not node_name in self.nodes:
                        self.nodes.append(node_name)

                    # Link the inputs
                    for reg_trait_name in self.regular_traits:
                        self.links.append(
                            "{0}->{1}.{0}".format(reg_trait_name, node_name))

                    # Link the input manager
                    self.links.append("input_manager.{0}->{1}.{2}".format(
                        unpack_trait_name, node_name, trait_name))

                # Link the output manager
                else:
                    self.links.append("{0}.{1}->output_manager.{2}".format(
                        node_name, trait_name, unpack_trait_name))

        # Update regular traits values
        if is_input_traits:
            for trait_name, trait_item in self.regular_traits.iteritems():

                # Unpack trait item
                trait_description, trait_value = trait_item

                # Pass the input trait values to the iterative pipeline
                setattr(self, trait_name, trait_value)
            
    def _run_process(self):
        """ Ececute this Process: connect the input and ouput traits by
        unpacking the iteative items
        """
        # Go through all iterative traits
        for trait_name, trait_item in self.iterative_traits.iteritems():

            # Unpack trait item
            trait_description, trait_value = trait_item

            # Unpack or pack the iterative traits depending on the manager type
            packed_value = []
            for cnt, item in enumerate(trait_value):

                # Connect manually input and output traits
                unpack_trait_name = "{0}_{1}".format(trait_name, cnt + 1)

                # Unpack
                if self.is_input_traits:
                    setattr(self, unpack_trait_name, trait_value[cnt])
                # Pack
                else:
                    packed_value.append(str(getattr(self, unpack_trait_name)))

            # Set the iterative output trait packed value
            if not self.is_input_traits:
                setattr(self, trait_name, packed_value)
                setattr(self.node, trait_name, packed_value)


    run = property(_run_process)


##############################################################
#                  Dynamic Iterative PIPELINE
##############################################################

class IterativePipeline(Pipeline):
    """ Dummy class to store an iterative pipeline
    """
    def pipeline_definition(self):
        """ IterativePipeline pipeline definition
        """
        pass
