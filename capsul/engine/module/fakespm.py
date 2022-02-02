# -*- coding: utf-8 -*-


def is_valid_config(config, requirements):
    required_version = requirements.get('version')
    if required_version and config.get(version) != required_version:
        return False
    return True


def init_execution_context(execution_context):
    '''
    Configure an execution context given a capsul_engine and some requirements.
    '''
    config =  execution_context.config['modules']['fakespm']
    execution_context.fakespm = object()
    execution_context.fakespm.directory = config['directory']
    execution_context.fakespm.version = config.get('version')
