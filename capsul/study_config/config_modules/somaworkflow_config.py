# -*- coding: utf-8 -*-
'''
`Soma-Workflow <http://brainvisa.info/soma-workflow/>`_ configuration module

Classes
=======
:class:`ResourceController`
---------------------------
:class:`SomaWorkflowConfig`
---------------------------
'''

from __future__ import absolute_import
from traits.api import Bool, Str, Undefined, List, Dict, File
from capsul.study_config.study_config import StudyConfigModule
from soma.controller import Controller, ControllerTrait, OpenKeyController

class ResourceController(Controller):
    ''' Configuration options for one Soma-Workflow computing resource

    Attributes
    ----------
    queue: str
        Jobs queue to be used on the computing resource for w
        orkflow submissions
    transfer_paths: list(str)
        list of paths where files have to be transferred by soma-workflow
    path_translations: dict(str, (str, str))
        Soma-workflow paths translations mapping:
        ``{local_path: (identifier, uuid)}``
    '''
    def __init__(self):
        super(ResourceController, self).__init__()
        self.add_trait(
            'queue',
            Str(Undefined, output=False,
                desc='Jobs queue to be used on the computing resource for '
                'workflow submissions'))
        self.add_trait(
            'transfer_paths', List(
                [],
                output=False,
                desc='list of paths where files have to be transferred '
                'by soma-workflow'))
        self.add_trait(
            'path_translations',
            ControllerTrait(
                OpenKeyController(
                    value_trait=List(trait=Str(), value=('', ''),
                    minlen=2, maxlen=2)),
                output=False,
                desc='Soma-workflow paths translations mapping: '
                '{local_path: (identifier, uuid)}'))

class SomaWorkflowConfig(StudyConfigModule):
    ''' Configuration module for :somaworkflow:`Soma-Workflow <index.html>`

    Stores configuration options which are not part of Soma-Workflow own
    configuration, and used to run workflows from CAPSUL pipelines.

    The configuration module may also store connected Soma-Workflow
    :somaworkflow:`WorkflowController <client_API.html>` objects to allow
    monitoring and submiting workflows.

    Attributes
    ----------
    use_soma_workflow: bool
        Use soma workflow for the execution
    somaworkflow_computing_resource: str
        Soma-workflow computing resource to be used to run processing
    somaworkflow_config_file: filename
        Soma-Workflow configuration file. Default: ``$HOME/.soma_workflow.cfg``
    somaworkflow_keep_failed_workflows: bool
        Keep failed workflows after pipeline execution through StudyConfig
    somaworkflow_keep_succeeded_workflows: bool
        Keep succeeded workflows after pipeline execution through StudyConfig
    somaworkflow_computing_resources_config: dict(str, ResourceController)
        Computing resource config dict, keys are resource ids. Values are
        :py:class:`ResourceController` instances

    Methods
    -------
    get_resource_id
    set_computing_resource_password
    get_workflow_controller
    connect_resource
    disconnect_resource
    '''
    
    def __init__(self, study_config, configuration):

        super(SomaWorkflowConfig, self).__init__(study_config, configuration)
        study_config.add_trait('use_soma_workflow', Bool(
            False,
            output=False,
            desc='Use soma workflow for the execution',
            groups=['soma-workflow']))
        study_config.add_trait(
            'somaworkflow_computing_resource',
            Str(
                Undefined,
                output=False,
                desc='Soma-workflow computing resource to be used to run processing',
                groups=['soma-workflow']))
        study_config.add_trait(
            'somaworkflow_config_file',
            File(Undefined, output=False, optional=True,
                 desc='Soma-Workflow configuration file. '
                 'Default: $HOME/.soma_workflow.cfg',
                 groups=['soma-workflow']))
        study_config.add_trait(
            'somaworkflow_keep_failed_workflows',
            Bool(
                True,
                desc='Keep failed workflows after pipeline execution through '
                'StudyConfig',
                groups=['soma-workflow']))
        study_config.add_trait(
            'somaworkflow_keep_succeeded_workflows',
            Bool(
                False,
                desc='Keep succeeded workflows after pipeline execution '
                'through StudyConfig',
                groups=['soma-workflow']))
        study_config.add_trait(
            'somaworkflow_computing_resources_config',
            ControllerTrait(
                OpenKeyController(
                    value_trait=ControllerTrait(
                        ResourceController(),
                        output=False, allow_none=False,
                        desc='Computing resource config')),
                output=False, allow_none=False,
                desc='Computing resource config',
                groups=['soma-workflow']))
        self.study_config.modules_data.somaworkflow = {}

    def initialize_callbacks(self):
        self.study_config.on_trait_change(
            self.initialize_module, 'use_soma_workflow')

    def get_resource_id(self, resource_id=None, set_it=False):
        ''' Get a computing resource name according to the (optional) input
        resource_id and Soma-Workflow configuration.

        For instance, ``None`` or ``"localhost"`` will be transformed to the
        local host id.

        Parameters
        ----------
        resource_id: str (optional)
        set_it: bool (optional)
            if True, the computed resource id will be set as the current
            resource in the somaworkflow_computing_resource trait value.

        Returns
        -------
        computed resource id.
        '''
        if resource_id is None:
            resource_id = self.study_config.somaworkflow_computing_resource
        else:
            self.study_config.somaworkflow_computing_resource = resource_id
        if resource_id in (None, Undefined, 'localhost'):
            from soma_workflow import configuration as swcf
            resource_id = swcf.Configuration.get_local_resource_id()
        if set_it:
            if resource_id is None:
                import socket
                resource_id = socket.gethostname()
            self.study_config.somaworkflow_computing_resource = resource_id
        return resource_id

    def set_computing_resource_password(self, resource_id, password=None,
                                        rsa_key_password=None):
        ''' Set credentials for a given computinf resource.

        Such credentials are stored in the config object, but will not be
        written when the config is saved in a file. They are thus non-
        persistent.

        Parameters
        ----------
        resource_id: str (optional)
        password: str (optional)
        rsa_key_password: str (optional)
        '''
        resource_id = self.get_resource_id(resource_id)
        r = self.study_config.modules_data.somaworkflow.setdefault(
            resource_id, Controller())
        if password:
            r.password = password
        if rsa_key_password:
            r.rsa_key_password = rsa_key_password

    def get_workflow_controller(self, resource_id=None):
        ''' Get a connected
        :somaworkflow:`WorkflowController <client_API.html>` for the given
        resource
        '''
        resource_id = self.get_resource_id(resource_id)

        r = self.study_config.modules_data.somaworkflow.setdefault(
            resource_id, Controller())
        wc = getattr(r, 'workflow_controller', None)
        return wc

    def connect_resource(self, resource_id=None, force_reconnect=False):
        ''' Connect a soma-workflow computing resource.

        Sets the current resource to the given resource_id (transformed by
        get_resource_id() if None or "localhost" is given, for instance).

        Parameters
        ----------
        resource_id: str (optional)
            resource name, may be None or "localhost". If None, the current
            one (study_config.somaworkflow_computing_resource) is used, or
            the localhost if none is configured.
        force_reconnect: bool (optional)
            if True, if an existing workflow controller is already connected,
            it will be disconnected (deleted) and a new one will be connected.
            If False, an existing controller will be reused without
            reconnection.

        Returns
        -------
        :somaworkflow:`WorkflowController <client_API.html>` object
        '''
        import soma_workflow.client as swclient

        resource_id = self.get_resource_id(resource_id, True)

        if force_reconnect:
            self.disconnect_resource(resource_id)

        r = self.study_config.modules_data.somaworkflow.setdefault(
            resource_id, Controller())

        if not force_reconnect:
            wc = self.get_workflow_controller(resource_id)
            if wc is not None:
                return wc

        conf_file = self.study_config.somaworkflow_config_file
        if conf_file in (None, Undefined):
            conf_file \
                = swclient.configuration.Configuration.search_config_path()
        login = swclient.configuration.Configuration.get_logins(
            conf_file).get(resource_id)
        config = getattr(r, 'config', None)
        if config is None:
            config = swclient.configuration.Configuration.load_from_file(
                resource_id=resource_id, config_file_path=conf_file)
            r.config = config
        password = getattr(r, 'password', None)
        rsa_key_pass = getattr(r, 'rsa_key_password', None)
        wc = swclient.WorkflowController(
            resource_id=resource_id,
            login=login,
            password=password,
            rsa_key_pass=rsa_key_pass,
            config=config)
        r.workflow_controller = wc
        return wc

    def disconnect_resource(self, resource_id=None):
        ''' Disconnect a connected
        :somaworkflow:`WorkflowController <client_API.html>` and removes it
        from the internal list
        '''
        resource_id = self.get_resource_id(resource_id, True)
        wc = self.get_workflow_controller(resource_id)
        if wc:
            wc.disconnect()
            del self.study_config.modules_data.somaworkflow[
                self.study_config.somaworkflow_computing_resource
                ].workflow_controller
