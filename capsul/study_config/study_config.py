#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

import os
from capsul.controller import Controller

try:
    from traits.api import HasTraits, Str, Enum, Directory, File, Bool
except ImportError:
    from enthought.traits.api import (HasTraits, Str ,Enum, Directory,
                                      File, Bool)

# nipype
import nipype.interfaces.matlab as matlab
from nipype.interfaces import spm

# traits
from traits.trait_base import _Undefined

# configuration utilitites
from config_utils import find_spm, environment
from capsul.utils.sorted_dictionary import SortedDictionary

# soma
from capsul.pipeline import Pipeline
from capsul.process import Process

# call functions
from memory import _joblib_run_process, _run_process


default_config = SortedDictionary(
    ("spm_directory", "/i2bm/local/spm8"),
    ("matlab_exec", "/neurospin/local/bin/matlab"),
    ("fsl_config", "/etc/fsl/4.1/fsl.sh"),
    ("spm_exec_cmd", "/i2bm/local/bin/spm8"),
    ("use_spm_mcr", False),
    ("use_fsl", True)
)


class StudyConfig(Controller):
    """ Class to store study parameters and processing options.
    This in turn is used to evaluate a Process instance or a Pipeline
    """

    def __init__(self, init_config=None):
        """ Set the traits to control the study parameters and
        processing options.
        """
        # update configuration
        init_config = init_config or default_config

        # inheritance
        super(StudyConfig, self).__init__()

        # Add some study parameters
        self.add_trait('input_directory', Directory(_Undefined()))
        self.add_trait('output_directory', Directory(_Undefined(),
                                                     exists=True))
        self.add_trait('shared_directory', Directory(_Undefined()))
        self.add_trait('generate_logging', Bool(False))

        # Add some dependencie parameters
        self.add_trait('spm_directory', Directory(_Undefined(),
                                                  exists=True))
        self.add_trait('matlab_exec', File(_Undefined(),
                                           exists=True))
        self.add_trait('fsl_config', File(_Undefined(),
                                          exists=True))
        self.add_trait('spm_exec_cmd', File(_Undefined(),
                                            exists=True))
        self.add_trait('use_spm_mcr', Bool(_Undefined()))
        self.add_trait('use_fsl', Bool(_Undefined()))

        # set the caller
        self.add_trait('use_smart_caching', Bool(False))
        self._caller = _run_process

        # set configuration
        for trait_name, trait_default_value in init_config.items():
            self.set_trait_value(trait_name, trait_default_value)

        # set_event
        #self.on_trait_change(self._use_smart_caching_update, 'output_type')

    ##############
    # Properties #
    ##############

    def set_trait_value(self, trait_name, trait_value):
        setattr(self, trait_name, trait_value)

    def get_trait(self, trait_name):
        """ Method that returns the class trait with name trait_name
        """
        # TODO test if trait_name exists
        return self.trait(trait_name)

    def get_trait_value(self, trait_name):
        return getattr(self, trait_name)

    ##############
    # Events     #
    ##############
    
    def _use_smart_caching_changed(self, old_trait_value, new_trait_value):
        """ Setup the caller
        """
        if new_trait_value:
            self._caller = _joblib_run_process
        else:
            self._caller = _run_process

    def _use_spm_mcr_changed(self, old_trait_value, new_trait_value):
        """ Setup SPM environment
        """
        # use compiled SPM
        if new_trait_value:
            if not isinstance(self.spm_exec_cmd, _Undefined):
                spm.SPMCommand.set_mlab_paths(
                    matlab_cmd=self.spm_exec_cmd + " run script",
                    use_mcr=True)
            else:
                raise Exception("No SPM execution command specified. "
                                "It is impossible to configure SPM.")
        # use Matlab + SPM
        else:
            spm.SPMCommand.set_mlab_paths(matlab_cmd="",
                                          use_mcr=False)
            if not isinstance(self.matlab_exec, _Undefined):
                matlab.MatlabCommand.set_default_matlab_cmd(self.matlab_exec +
                       " -nodesktop -nosplash")
            else:
                raise Exception("No MATLAB binary specified. "
                                "It is impossible to configure MATLAB.")
            if isinstance(self.spm_directory, _Undefined):
                # automatic search of SPM
                self.spm_directory = find_spm(self.matlab_exec)
            matlab.MatlabCommand.set_default_paths(self.spm_directory)

    def _use_fsl_changed(self, new_trait_value):
        """ Setup FSL environment
        """
        if new_trait_value:
            fsl_config_file = self.get_trait_value('fsl_config')
            if not isinstance(fsl_config_file, _Undefined):
                envfsl = environment(fsl_config_file)
                if (not envfsl["LD_LIBRARY_PATH"] in
                       (os.environ.get("LD_LIBRARY_PATH") or [])):
                    for envname, envval in envfsl.items():
                        if envname in os.environ:
                            if envname.startswith("FSL"):
                                os.environ[envname] = envval
                            else:
                                os.environ[envname] += ":" + envval
                        else:
                            os.environ[envname] = envval
            else:
                raise Exception("No FSL configuration file specified. "
                                "It is impossible to configure FSL.")

    ##############
    # Methods    #
    ##############

    def run(self, process_or_pipeline):
        """ Function to execute a process or a pipline
        with the Study parameters
        """
        # create the output log directory
        #date = datetime.datetime.now()
        #date_dir = "_".join([str(date.day), str(date.month),
        #                     str(date.year)])
        #log_dir = os.path.join(self.output_directory, date_dir)
        #ensure_is_dir(log_dir)

        # generate ordered execution list
        execution_list = []
        if isinstance(process_or_pipeline, Pipeline):
            execution_list = process_or_pipeline.workflow_ordered_nodes()
        elif isinstance(process_or_pipeline, Process):
            execution_list.append(process_or_pipeline)
        else:
            raise Exception("Unknown instance type. Got {0}"
                  "and expect Process or Pipeline"
                  "instances".format(process_or_pipeline.__module__.name__))

        # execute each element
        for cnt, process_instance in enumerate(execution_list):
            # run
            returncode, log_file = self._caller(self.output_directory,
                        "{0}-{1}".format(cnt + 1, process_instance.name),
                         process_instance,
                         self.generate_logging,
                         self.spm_directory)

if __name__ == "__main__":

    study = StudyConfig()
