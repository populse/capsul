# -*- coding: utf-8 -*-
#
#  This software and supporting documentation were developed by
#      CEA/DSV/SHFJ and IFR 49
#      4 place du General Leclerc
#      91401 Orsay cedex
#      France
#
# This software is governed by the CeCILL license version 2 under
# French law and abiding by the rules of distribution of free software.
# You can  use, modify and/or redistribute the software under the
# terms of the CeCILL license version 2 as circulated by CEA, CNRS
# and INRIA at the following URL "http://www.cecill.info".
#
# As a counterpart to the access to the source code and  rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty  and the software's author,  the holder of the
# economic rights,  and the successive licensors  have only  limited
# liability.
#
# In this respect, the user's attention is drawn to the risks associated
# with loading,  using,  modifying and/or developing or reproducing the
# software by the user in light of its specific status of free software,
# that may mean  that it is complicated to manipulate,  and  that  also
# therefore means  that it is reserved for developers  and  experienced
# professionals having in-depth computer knowledge. Users are therefore
# encouraged to load and test the software's suitability as regards their
# requirements in conditions enabling the security of their systems and/or
# data to be ensured and,  more generally, to use and operate it in the
# same conditions as regards security.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL license version 2 and that you accept its terms.

"""
capsul.process.runprocess is not a real python module, but rather an executable script with commandline arguments and options parsing. It is provided as a module just to be easily called via the python command in a portable way::

    python -m capsul.process.runprocess <process name> <process arguments>

Classes
-------
:class:`ProcessParamError`
++++++++++++++++++++++++++

Functions
---------
:func:`set_process_param_from_str`
++++++++++++++++++++++++++++++++++
:func:`get_process_with_params`
+++++++++++++++++++++++++++++++
:func:`run_process_with_distribution`
+++++++++++++++++++++++++++++++++++++
:func:`convert_commandline_parameter`
+++++++++++++++++++++++++++++++++++++
:func:`main`
++++++++++++


"""

from capsul.api import StudyConfig
from capsul.api import capsul_engine
from capsul.api import Pipeline
from capsul.attributes.completion_engine import ProcessCompletionEngine
from soma.qt_gui import qt_backend
import os
import os.path as osp
import logging
import sys
import re
from optparse import OptionParser, OptionGroup
from traits.api import Undefined, List
import tempfile
import subprocess
try:
    import yaml
except ImportError:
    yaml = None
    import json
import six

# Define the logger
logger = logging.getLogger(__name__)


class ProcessParamError(Exception):
    ''' Exception used in the ``runprocess`` module
    '''
    pass


def set_process_param_from_str(process, k, arg):
    """Set a process parameter from a string representation."""
    if '.' in k:
        sub_node_name, k2 = k.split('.', 1)
        sub_node = process.nodes.get(sub_node_name)
        if sub_node is not None:
            try:
                return set_process_param_from_str(sub_node, k2, arg)
            except KeyError:
                sub_proc = getattr(sub_node, 'process', None)
                if sub_proc is not None:
                    return set_process_param_from_str(sub_proc, k2, arg)
    if not process.trait(k):
        if hasattr(process, k):
            # print('set non-trait value:', process, k, repr(arg))
            setattr(process, k, arg)
            return
        if hasattr(process, 'pipeline_node') \
                and hasattr(process.pipeline_node, k):
            setattr(process.pipeline_node, k, arg)
            return
        raise ProcessParamError("Unknown parameter {0} for process {1}"
                                .format(k, process.name))
    try:
        evaluate = process.trait(k).trait_type.evaluate
    except AttributeError:
        evaluate = None
    # print('set_process_param_from_str:', process, k, repr(arg))
    if evaluate:
        arg = evaluate(arg)
    setattr(process, k, arg)
    process.trait(k).forbid_completion = True
    if isinstance(process, Pipeline):
        process.propagate_metadata(process.pipeline_node, k,
                                   {'forbid_completion': True})


def get_process_with_params(process_name, study_config, iterated_params=[],
                            attributes={}, *args, **kwargs):
    ''' Instantiate a process, or an iteration over processes, and fill in its
    parameters.

    Parameters
    ----------
    process_name: string
        name (mosule and class) of the process to instantiate
    study_config: StudyConfig instance
    iterated_params: list (optional)
        parameters names which should be iterated on. If this list is not
        empty, an iteration process is built. All parameters values
        corresponding to the selected names should be lists with the same size.
    attributes: dict (optional)
        dictionary of attributes for completion system.
    *args:
        sequential parameters for the process. In iteration, "normal"
        parameters are set with the same value for all iterations, and iterated
        parameters dispatch their values to each iteration.
    **kwargs:
        named parameters for the process. Same as above for iterations.

    Returns
    -------
    process: Process instance
    '''
    process = study_config.get_process_instance(process_name)
    signature = process.user_traits()
    params = list(signature.keys())

    # check for iterations
    if iterated_params:

        pipeline = study_config.get_process_instance(Pipeline)
        pipeline.add_iterative_process('iteration', process, iterated_params)
        pipeline.autoexport_nodes_parameters(include_optional=True)
        process = pipeline

        # transform iterated attributes into lists if needed
        for param, value in attributes.items():
            if not isinstance(value, list) and not isinstance(value, tuple):
                attributes[param] = list([value])

    for i, arg in enumerate(args):
        set_process_param_from_str(process, params[i], arg)
    for k, arg in six.iteritems(kwargs):
        set_process_param_from_str(process, k, arg)

    completion_engine = ProcessCompletionEngine.get_completion_engine(process)
    completion_engine.get_attribute_values().import_from_dict(attributes)
    completion_engine.complete_parameters()

    return process


def run_process_with_distribution(
        study_config, process, use_soma_workflow=False,
        resource_id=None, password=None, config=None, rsa_key_pass=None,
        queue=None, input_file_processing=None, output_file_processing=None,
        keep_workflow=False, keep_failed_workflow=False,
        write_workflow_only=None):
    ''' Run the given process, either sequentially or distributed through
    Soma-Workflow.

    Parameters
    ----------
    study_config: StudyConfig instance
    process: Process instance
        the process to execute (or pipeline, or iteration...)
    use_soma_workflow: bool or None (default=None)
        if False, run sequentially, otherwise use Soma-Workflow. Its
        configuration has to be setup and valid for non-local execution, and
        additional file transfer options may be used.
    resource_id: string (default=None)
        soma-workflow resource ID, defaults to localhost
    password: string
        password to access the remote computing resource. Do not specify it if
        using a ssh key.
    config: dict (optional)
        Soma-Workflow config: Not used for now...
    rsa_key_pass: string
        RSA key password, for ssh key access
    queue: string
        Queue to use on the computing resource. If not specified, use the
        default queue.
    input_file_processing: brainvisa.workflow.ProcessToSomaWorkflow processing code
        Input files processing: local_path (NO_FILE_PROCESSING),
        transfer (FILE_TRANSFER), translate (SHARED_RESOURCE_PATH),
        or translate_shared (BV_DB_SHARED_PATH).
    output_file_processing: same as for input_file_processing
        Output files processing: local_path (NO_FILE_PROCESSING),
        transfer (FILE_TRANSFER), or translate (SHARED_RESOURCE_PATH).
        The default is local_path.
    keep_workflow: bool
        keep the workflow in the computing resource database after execution.
        By default it is removed.
    keep_failed_workflow: bool
        keep the workflow in the computing resource database after execution,
        if it has failed. By default it is removed.
    write_workflow_only: str
        if specified, this is an output filename where the workflow file will
        be written. The workflow will not be actually run, because int his
        situation the user probably wants to use the workflow on his own.
    '''
    if write_workflow_only:
        use_soma_workflow = True

    if use_soma_workflow is not None:
        study_config.use_soma_workflow = use_soma_workflow

    if study_config.use_soma_workflow:

        if write_workflow_only:
            # Create soma workflow pipeline
            from capsul.pipeline.pipeline_workflow \
                import workflow_from_pipeline
            import soma_workflow.client as swclient

            workflow = workflow_from_pipeline(process)
            swclient.Helper.serialize(write_workflow_only, workflow)

            return

        swm = study_config.modules['SomaWorkflowConfig']
        resource_id = swm.get_resource_id(resource_id, set_it=True)
        if password is not None or rsa_key_pass is not None:
            swm.set_computing_resource_password(resource_id, password,
                                                rsa_key_pass)
        if queue is not None:
            if not hasattr(
                    study_config.somaworkflow_computing_resources_config,
                    resource_id):
                setattr(study_config.somaworkflow_computing_resources_config,
                        resource_id, {})
            getattr(study_config.somaworkflow_computing_resources_config,
                    resource_id).queue = queue

    res = study_config.run(process)
    return res


def convert_commandline_parameter(i):
    if len(i) > 0 and ( i[0] in '[({' or i in ( 'None', 'True', 'False' ) ):
        try:
            res=eval(i)
        except Exception:
            res=i
    else:
        res = i
    return res


# main
def main():
    ''' Run the :mod:`capsul.process.runprocess` module as a commandline
    '''

    # disable any GUI
    qt_backend.set_headless(needs_opengl=False)

    usage = '''Usage: python -m capsul [options] processname [arg1] [arg2] ...
    [argx=valuex] [argy=valuey] ...

    Example::

        python -m capsul threshold ~/data/irm.ima /tmp/th.nii threshold1=80

    Named arguments (in the shape argx=valuex) may address sub-processes of a
    pipeline, using the dot separator::

        PrepareSubject.t1mri=/home/myself/mymri.nii

    For a more precise description, please look at the web documentation:
    https://brainvisa.info/capsul/user_guide_tree/index.html

    Configuration:

    The ``--config`` option allows to pass a Capsul configuration file (a JSON
    dict). If you have a configuration in Brainvisa/Axon and want to convert
    it, use the following::

        axon-runprocess capsul://capsul.engine.write_engine_config engine.json

    Then the file ``engine.json`` will be OK.
    Alternatively, using "--config axon" will do this for you internally.

    It is possible to reach sub-process parameters in a pipeline by addressing
    their node in the parent pipeline:

    python -m capsul morphologist.capsul.morphologist Renorm.enabled=False
    '''

    # Set up logging on stderr. This must be called before any logging takes
    # place, to avoid "No handlers could be found for logger" errors.
    logging.basicConfig()

    parser = OptionParser(description='Run a single CAPSUL process',
        usage=usage)
    group1 = OptionGroup(
        parser, 'Config',
        description='Processing configuration, database options')
    group1.add_option('--studyconfig', dest='studyconfig',
        help='load StudyConfig configuration from the given file (JSON)')
    group1.add_option(
        '--config', dest='config',
        help='load Capsul engine configuration from the given file (JSON) '
        '(CapsulEngine shape, not Studyconfig -- use --studyconfig '
        'otherwise). Using "--config axon" will run the conversion process in '
        'Axon and import the config.')
    group1.add_option('-i', '--input', dest='input_directory',
                      help='input data directory (if not specified in '
                      'studyconfig file). If not specified neither on the '
                      'commandline nor study configfile, taken as the same as '
                      'output.')
    group1.add_option('-o', '--output', dest='output_directory',
                      help='output data directory (if not specified in '
                      'studyconfig file). If not specified neither on the '
                      'commandline nor study configfile, taken as the same as '
                      'input.')
    group1.add_option('--if', '--input-fom', dest='input_fom',
                      help='input FOM (File Organization Model). Decides '
                      'which files and directories layout for the input '
                      'data. Generally "morphologist-bids-1.0" or '
                      '"morphologist-auto-nonoverlap-1.0". Default: '
                      '"morphologist-bids-1.0"')
    group1.add_option('--of', '--output-fom', dest='output_fom',
                      help='input FOM (File Organization Model). Decides '
                      'which files and directories layout for the output '
                      'data. Generally "morphologist-bids-1.0" or '
                      '"morphologist-auto-nonoverlap-1.0". Default: '
                      '"morphologist-bids-1.0"')
    group1.add_option('--params', dest='paramsfile', default=None,
                      help='specify a file containing commandline parameters. '
                      'The file will contain arguments for this commandline '
                      '(argv): it is an alternative to providing them here. '
                      'It can be useful to reuse parameters, or when the '
                      'parameters are too long (in a large iteration, '
                      'typically). The file syntax is one line per parameter, '
                      'with no further parsing. It will be processed after '
                      'all the current commandline arguments, not right now '
                      'as the argument appears. But if a parameter has '
                      'already been set (via commandline), it will not be '
                      'replaced: first set arguments have priority. If the '
                      'params file itself contains a --params parameter, '
                      'then another file will be read afterwards, and so on.')
    group1.add_option('--opengl', action='store_true', default=False,
                      help='Tell the process loading system that we will '
                      'require headless OpenGL, which needs proper setup and '
                      'libraries loading tweaks. Without this option, Qt and '
                      'potentially graphical modules will be initialized in '
                      'headless mode, but there will be no check for a '
                      'working OpenGL/GLX implementation. In some cases it '
                      'will work anyway, but in others (no X server) OpenGL '
                      'will require using a virtual X server (Xvfb) and '
                      'possibly loading appropriate OpenGL libraries. This is '
                      'not done systematically because of the '
                      'overhead it brings.')
    parser.add_option_group(group1)

    group2 = OptionGroup(parser, 'Processing',
                        description='Processing options, distributed execution')
    group2.add_option('--swf', '--soma_workflow', dest='soma_workflow',
                      default=False,
                      action='store_true',
                      help='use soma_workflow. Soma-Workflow '
                      'configuration has to be setup and valid for non-local '
                      'execution, and additional file transfer options '
                      'may be used. The default is *not* to use SWF and '
                      'process mono-processor, sequential execution.')
    group2.add_option('-r', '--resource_id', dest='resource_id', default=None,
                      help='soma-workflow resource ID, defaults to localhost')
    group2.add_option('-w', '--write-workflow-only', dest='write_workflow',
                      default=None,
                      help='if specified, this is an output '
                      'filename where the workflow file will be written. The '
                      'workflow will not be actually run, because in this '
                      'situation the user probably wants to use the workflow '
                      'on his own.')
    group2.add_option('-p', '--password', dest='password', default=None,
                      help='password to access the remote computing resource. '
                      'Do not specify it if using a ssh key')
    group2.add_option('--rsa-pass', dest='rsa_key_pass', default=None,
                      help='RSA key password, for ssh key access')
    group2.add_option('--queue', dest='queue', default=None,
                      help='Queue to use on the computing resource. If not '
                      'specified, use the default queue.')
    #group2.add_option('--input-processing', dest='input_file_processing',
                      #default=None, help='Input files processing: local_path, '
                      #'transfer, translate, or translate_shared. The default is '
                      #'local_path if the computing resource is the localhost, or '
                      #'translate_shared otherwise.')
    #group2.add_option('--output-processing', dest='output_file_processing',
                      #default=None, help='Output files processing: local_path, '
                      #'transfer, or translate. The default is local_path.')
    group2.add_option('--keep-succeeded-workflow', dest='keep_succeded_workflow',
                      action='store_true', default=False,
                      help='keep the workflow in the computing resource '
                      'database after execution. By default it is removed.')
    group2.add_option('--delete-failed-workflow', dest='delete_failed_workflow',
                      action='store_true', default=False,
                      help='delete the workflow in the computing resource '
                      'database after execution, if it has failed. By default '
                      'it is kept.')
    parser.add_option_group(group2)

    group3 = OptionGroup(parser, 'Iteration',
                        description='Iteration')
    group3.add_option('-I', '--iterate', dest='iterate_on', action='append',
                      help='Iterate the given process, iterating over the '
                      'given parameter(s). Multiple parameters may be '
                      'iterated jointly using several -I options. In the '
                      'process parameters, values are replaced by lists, all '
                      'iterated lists should have the same size.\n'
                      'Ex:\n'
                      'python -m capsul -I par_a -I par_c a_process '
                      'par_a="[1, 2]" par_b="something" '
                      'par_c="[\\"one\\", \\"two\\"]"')
    parser.add_option_group(group3)

    group4 = OptionGroup(parser, 'Attributes completion')
    group4.add_option('-a', '--attribute', dest='attributes', action='append',
                      default=[],
                      help='set completion (including FOM) attribute. '
                      'Syntax: attribute=value, value the same syntax as '
                      'process parameters (python syntax for lists, for '
                      'instance), with proper quotes if needed for shell '
                      'escaping.\n'
                      'Ex: -a acquisition="default" '
                      '-a subject=\'["s1", "s2"]\'')
    parser.add_option_group(group4)

    group5 = OptionGroup(parser, 'Help',
                        description='Help and documentation options')
    group5.add_option('--process-help', dest='process_help',
        action='store_true', default=False,
        help='display specified process help')
    parser.add_option_group(group5)

    parser.disable_interspersed_args()
    (options, args) = parser.parse_args()

    default_fom = 'morphologist-bids-1.0'

    if options.opengl:
        qt_backend.set_headless(needs_opengl=True)

    while options.paramsfile:
        pfile = options.paramsfile
        options.paramsfile = None
        with open(pfile) as f:
            new_argv = [l.strip() for l in f.readlines()]
        new_options, new_args = parser.parse_args(new_argv)
        for k, v in new_options.__dict__.items():
            if not getattr(options, k, None):
                setattr(options, k, v)
        args += new_args

    engine = capsul_engine()
    engine.load_modules(['fom', 'axon'])
    study_config = engine.study_config

    if options.config:
        config_file = options.config
        tmp = None
        if options.config == 'axon':
            tmp = tempfile.mkstemp(prefix='capsul_conf', suffix='.json')
            os.close(tmp[0])
            cmd = ['axon-runprocess',
                    'capsul://capsul.engine.write_engine_config',
                    tmp[1]]
            subprocess.check_call(cmd)
            config_file = tmp[1]
        with open(config_file) as f:
            if yaml:
                conf = yaml.load(f, Loader=yaml.SafeLoader)
            else:
                conf = json.load(f)
        if tmp:
            os.unlink(tmp[1])
        for env, c in conf.items():
            engine.import_configs(env, c)
    elif options.studyconfig:
        with open(options.studyconfig) as f:
            if yaml:
                scdict = yaml.load(f, Loader=yaml.SafeLoader)
            else:
                scdict = json.load(f)
        study_config.set_study_configuration(scdict)
        engine = study_config.engine
    else:
        study_config = StudyConfig(
            modules=StudyConfig.default_modules + ['FomConfig'])
        study_config.read_configuration()
        study_config.use_fom = True
        engine = study_config.engine

    if options.input_directory:
        study_config.input_directory = options.input_directory
    if options.output_directory:
        study_config.output_directory = options.output_directory
    if study_config.output_directory in (None, Undefined, '') \
            and study_config.input_directory not in (None, Undefined, ''):
        study_config.output_directory = study_config.input_directory
    if study_config.input_directory in (None, Undefined, '') \
            and study_config.output_directory not in (None, Undefined, ''):
        study_config.input_directory = study_config.output_directory
    study_config.somaworkflow_keep_succeeded_workflows \
        = options.keep_succeded_workflow
    study_config.somaworkflow_keep_failed_workflows \
        = not options.delete_failed_workflow

    with engine.settings as session:
        config = session.config('fom', 'global')
        if options.input_fom is not None:
            config.input_fom = options.input_fom
        else:
            try:
                config.input_fom = default_fom
            except KeyError:
                global sys  # WHY does the global import not work here ??
                print('Warning: FOM', default_fom, 'could not be loaded.',
                      file=sys.stderr)
        if options.output_fom is not None:
            config.output_fom = options.output_fom
        else:
            try:
                config.output_fom = default_fom
            except KeyError:
                pass

    kwre = re.compile(r'([a-zA-Z_](\.?[a-zA-Z0-9_])*)\s*=\s*(.*)$')

    attributes = {}
    for att in options.attributes:
        m = kwre.match(att)
        if m is None:
            raise SyntaxError('syntax error in attribute definition: %s' % att)
        attributes[m.group(1)] = convert_commandline_parameter(m.group(3))

    args = tuple((convert_commandline_parameter(i) for i in args))
    kwargs = {}
    todel = []
    for arg in args:
        if isinstance(arg, six.string_types):
            m = kwre.match(arg)
            if m is not None:
                kwargs[m.group(1)] = convert_commandline_parameter(m.group(3))
                todel.append(arg)
    args = [arg for arg in args if arg not in todel]

    if not args:
        parser.print_usage()
        sys.exit(2)

    # get the main process
    process_name = args[0]
    args = args[1:]

    iterated = options.iterate_on
    try:
        process = get_process_with_params(process_name, study_config, iterated,
                                          attributes,
                                          *args, **kwargs)
    except ProcessParamError as e:
        print("error: {0}".format(e), file=sys.stderr)
        sys.exit(1)

    if options.process_help:
        process.help()

        print()

        completion_engine \
            = ProcessCompletionEngine.get_completion_engine(process)
        attribs = completion_engine.get_attribute_values()
        aval = attribs.export_to_dict()
        print('Completion attributes:')
        print('----------------------')
        print()
        print('(note: may differ depending on study config file contents, '
              'completion rules (FOM)...)')
        print()

        skipped = set(['generated_by_parameter', 'generated_by_process'])
        for name, value in six.iteritems(aval):
            if name in skipped:
                continue
            ttype = attribs.trait(name).trait_type.__class__.__name__
            if isinstance(attribs.trait(name).trait_type, List):
                ttype += '(%s)' \
                    % attribs.trait(name).inner_traits[
                        0].trait_type.__class__.__name__
            print('%s:' % name, ttype)
            if value not in (None, Undefined):
                print('   ', value)

        print()

        del aval, attribs, completion_engine, process
        sys.exit(0)

    resource_id = options.resource_id
    password = options.password
    rsa_key_pass = options.rsa_key_pass
    queue = options.queue
    file_processing = []

    study_config.use_soma_workflow = options.soma_workflow

    if options.soma_workflow:
        file_processing = [None, None]

    else:
        file_processing = [None, None]

    res = run_process_with_distribution(
        study_config, process, options.soma_workflow, resource_id=resource_id,
        password=password, rsa_key_pass=rsa_key_pass,
        queue=queue, input_file_processing=file_processing[0],
        output_file_processing=file_processing[1],
        write_workflow_only=options.write_workflow)

    # if there was no exception, we assume the process has succeeded.
    # sys.exit(0)
    # no error, do a dirty exit, but avoid cleanup crashes after the process
    # has succeeded...
    os._exit(0)

    # otherwise it has raised an exception, exit "normally"


if __name__ == '__main__':
    main()
