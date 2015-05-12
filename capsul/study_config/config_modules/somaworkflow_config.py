##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from traits.api import Bool, Str, Undefined, List, Dict, TraitType, TraitError
from capsul.study_config.study_config import StudyConfigModule
from soma.controller import Controller


class SomaWorkflowConfig(StudyConfigModule):

    class ResourceController(Controller):
        def __init__(self, dummy=None):
            super(SomaWorkflowConfig.ResourceController, self).__init__()
            self.add_trait(
                'transfer_paths', List(
                    [],
                    output=False,
                    desc='list of paths where files have to be transferred '
                    'by soma-workflow'))
            self.add_trait(
                'path_translations', Dict(
                    value={},
                    key_trait=Str(),
                    value_trait=Str(),
                    output=False,
                    desc='Soma-workflow paths translations mapping: '
                    '{local_path: remote_path}'))

    class ControllerTrait(TraitType):
        def __init__(self, controller, open_keys=False, open_trait_type=None,
                     **kwargs):
            super(SomaWorkflowConfig.ControllerTrait, self).__init__(
                None, **kwargs)
            self.controller = controller
            self.default_value = controller
            self.open_keys = open_keys
            self.open_trait_type = open_trait_type

        def validate(self, object, name, value):
            if isinstance(value, Controller):
                return super(SomaWorkflowConfig.ControllerTrait,
                             self).validate(value)
            if not hasattr(value, 'iteritems'):
                raise TraitError('trait must be a Controller')
            new_value = getattr(object, name).copy(with_values=False)
            if self.open_keys:
                for key in value:
                    if not self.controller.trait(key):
                        new_value.add_trait(key, self.open_trait_type)
            new_value.import_from_dict(value)
            return new_value

    def __init__(self, study_config, configuration):

        super(SomaWorkflowConfig, self).__init__(study_config, configuration)
        study_config.add_trait('use_soma_workflow', Bool(
            False,
            output=False,
            desc='Use soma workflow for the execution'))
        study_config.add_trait('somaworkflow_computing_resource', Str(
            Undefined,
            output=False,
            desc='Soma-workflow computing resource to be used to run processing'))

        c = Controller()
        study_config.add_trait(
            'somaworkflow_computing_resources_config',
                SomaWorkflowConfig.ControllerTrait(
                    c,
                    open_keys=True,
                    open_trait_type=SomaWorkflowConfig.ControllerTrait(
                        SomaWorkflowConfig.ResourceController(),
                        output=False, allow_none=False,
                        desc='Computing resource config'),
                    output=False, allow_none=False,
                    desc='Computing resource config'))

        #c.add_trait(
            #'localhost',
            #SomaWorkflowConfig.ControllerTrait(
                #SomaWorkflowConfig.ResourceController(),
                #output=False, allow_none=False,
                #desc='Computing resource config'))

    def initialize_callbacks(self):
        self.study_config.on_trait_change(
            self.initialize_module, 'use_soma_workflow')
