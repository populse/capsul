##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from traits.api import Bool, Str, Undefined, List, Dict
from capsul.study_config.study_config import StudyConfigModule
from soma.controller import Controller, ControllerTrait


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
                'path_translations',
                ControllerTrait(
                    Controller(),
                    inner_trait=List(trait=Str(), value=('', ''),
                                     minlen=2, maxlen=2),
                    output=False,
                    desc='Soma-workflow paths translations mapping: '
                    '{local_path: (identifier, uuid)}'))
                #Dict(
                    #value={},
                    #key_trait=Str(),
                    #value_trait=List(trait=Str(), value=('', ''),
                                     #minlen=2, maxlen=2),
                    #output=False,
                    #desc='Soma-workflow paths translations mapping: '
                    #'{local_path: (identifier, uuid)}'))

    def __init__(self, study_config, configuration):

        super(SomaWorkflowConfig, self).__init__(study_config, configuration)
        study_config.add_trait('use_soma_workflow', Bool(
            False,
            output=False,
            desc='Use soma workflow for the execution'))
        study_config.add_trait(
            'somaworkflow_computing_resource',
            Str(
                Undefined,
                output=False,
                desc='Soma-workflow computing resource to be used to run processing'))

        c = Controller()
        study_config.add_trait(
            'somaworkflow_computing_resources_config',
                ControllerTrait(
                    c,
                    inner_trait=ControllerTrait(
                        SomaWorkflowConfig.ResourceController(),
                        output=False, allow_none=False,
                        desc='Computing resource config'),
                    output=False, allow_none=False,
                    desc='Computing resource config'))

        #c.add_trait(
            #'localhost',
            #ControllerTrait(
                #SomaWorkflowConfig.ResourceController(),
                #output=False, allow_none=False,
                #desc='Computing resource config'))

    def initialize_callbacks(self):
        self.study_config.on_trait_change(
            self.initialize_module, 'use_soma_workflow')
