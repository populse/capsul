#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import logging
import json
import collections

# Trait import
try:
    from traits.trait_base import _Undefined
    from traits.api import HasTraits, Str, Enum, Directory, File, Bool
except ImportError:
    import enthought.traits.api as traits
    from enthought.traits.api import (HasTraits, Str ,Enum, Directory,
                                      File, Bool)
# Capsul import
from soma.controller import Controller
from config_utils import find_spm, environment
from soma.sorted_dictionary import SortedDictionary
from capsul.pipeline import Pipeline
from capsul.process import Process



class StudyConfig(Controller):
    """ Class to store study parameters and processing options.

    This in turn is used to evaluate a Process instance or a Pipeline
    """

    class InternalData(object):
        pass

    def __init__(self, init_config=None):
        """ Initilize the StudyConfig class

        Parameters
        ----------
        init_config: ordered dict (default None)
            the structure that contain the default study configuration.
            Keys are in attributes.
        """

        self.internal_data = StudyConfig.InternalData()

        # Update configuration
        init_config = init_config or {}

        # Inheritance
        super(StudyConfig, self).__init__()
        self.add_trait("input_directory", Directory(
            _Undefined(),
            desc="Parameter to set the study input directory"))
        self.add_trait("output_directory", Directory(
            _Undefined(),
            desc="Parameter to set the study output directory",
            exists=True))
        self.add_trait("shared_directory", Directory(
            _Undefined(),
            desc="Parameter to set the study shared directory",
            exists=True))
        self.add_trait("spm_directory", Directory(
            _Undefined(),
            desc="Parameter to set the SPM directory",
            exists=True))
        self.add_trait("input_fom", Directory(
            _Undefined(),
            desc="study input FOM"))
        self.add_trait("output_fom", Directory(
            _Undefined(),
            desc="study output FOM"))
        self.add_trait("format_image", Str(
            desc="preferred format for images written"))
        self.add_trait("format_mesh", Str(
            desc="preferred format for meshes written"))

        # Set configuration
        for trait_name, trait_default_value in init_config.items():
            try:
                setattr(self, trait_name, trait_default_value)
            except:
                logging.warn('could not set value for config variable %s: %s' \
                    % (trait_name, repr(trait_default_value)))


    def save(self, json_filename):
        """ Save study config as json file """
        dico = collections.OrderedDict([
            ('input_directory', self.input_directory),
            ('input_fom', self.input_fom),
            ('output_directory', self.output_directory),
            ('output_fom', self.output_fom),
            ('shared_directory', self.shared_directory),
            ('spm_directory', self.spm_directory),
            ('format_image', self.format_image),
            ('format_mesh', self.format_mesh),
        ])
        json_string = json.dumps(dico, indent=4, separators=(',', ': '))
        with open(json_filename, 'w') as f:
            f.write(unicode(json_string))

    def load(self, json_filename):
        """ Load study config from json file """
        with open(json_filename, 'r') as json_data:
            loaded_dict = json.load(
                json_data, object_pairs_hook=collections.OrderedDict)
        for element, value in loaded_dict.iteritems():
            setattr(self, element, value)

