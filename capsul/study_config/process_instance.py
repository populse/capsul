'''
Process instance factory

Functions
=========
:func:`is_process`
------------------
:func:`is_pipeline_node`
------------------------
:func:`get_process_instance`
----------------------------
:func:`get_node_class`
----------------------
:func:`get_node_instance`
-------------------------
'''

# System import
import sys
import os.path as osp
import importlib
import types
import re
import six
import os
import inspect

# Caspul import
from capsul.process.process import Process
from capsul.pipeline.pipeline import Pipeline
from capsul.process.nipype_process import nipype_factory
from capsul.process.xml import create_xml_process
from capsul.pipeline.xml import create_xml_pipeline
from capsul.pipeline.pipeline_nodes import Node
from soma.controller import Controller

# Nipype import
try:
    from nipype.interfaces.base import Interface
# If nipype is not found create a dummy Interface class
except ImportError:
    Interface = type("Interface", (object, ), {})

if sys.version_info[0] >= 3:
    basestring = str
    unicode = str


process_xml_re = re.compile(r'<process.*</process>', re.DOTALL)


def is_process(item):
    """ Check if the input item is a process class or function with decorator
    or XML docstring which makes it seen as a process
    """
    if inspect.isclass(item) and item not in (Pipeline, Process) \
            and (issubclass(item, Process) or issubclass(item, Interface)):
        return True
    if not inspect.isfunction(item):
        return False
    if hasattr(item, 'capsul_xml'):
        return True
    if item.__doc__:
        match = process_xml_re.search(item.__doc__)
        if match:
            return True
    return False


def is_pipeline_node(item):
    """ Check if the input is an instance of pipeline Node
    """
    return item is not Node and isinstance(item, Node)


def get_process_instance(process_or_id, study_config=None, **kwargs):
    """ Return a Process instance given an identifier.

    Note that it is convenient to create a process from a StudyConfig instance:
    StudyConfig.get_process_instance()

    The identifier is either:

        * a derived Process class.
        * a derived Process class instance.
        * a Nipype Interface instance.
        * a Nipype Interface class.
        * a string description of the class `<module>.<class>`.
        * a string description of a function to warp `<module>.<function>`.
        * a string description of a module containing a single process
          `<module>`
        * a string description of a pipeline `<module>.<fname>.xml`.
        * an XML filename for a pipeline.
        * a Python (.py) filename with process name in it:
          `/path/process_source.py#ProcessName`.
        * a Python (.py) filename for a file containg a single process.

    Default values of the process instance are passed as additional parameters.

    .. note:

        If no process is found an ImportError is raised.

    .. note:

        If the 'process_or_id' parameter is not valid a ValueError is raised.

    .. note:

        If the function to warp does not contain a process description in its
        docstring ('<process>...</process>') a ValueError is raised.

    Parameters
    ----------
    process_or_id: instance or class description (mandatory)
        a process/nipype interface instance/class or a string description.
    study_config: StudyConfig instance (optional)
        A Process instance belongs to a StudyConfig framework. If not specified
        the study_config can be set afterwards.
    kwargs:
        default values of the process instance parameters.

    Returns
    -------
    result: Process
        an initialized process instance.
    """
    # NOTE
    # here we make a bidouille to make study_config accessible from processes
    # constructors. It is used for instance in ProcessIteration.
    # This is not elegant, not thread-safe, and forbids to have one pipeline
    # build a second one in a different study_config context.
    # I don't have a better solution, however.
    import capsul.study_config.study_config as study_cmod
    set_study_config = (study_config is not None
                        and study_cmod._default_study_config
                            is not study_config)

    try:
        if set_study_config:
            old_default_study_config = study_cmod._default_study_config
            study_cmod._default_study_config = study_config
        return _get_process_instance(process_or_id, study_config=study_config,
                                     **kwargs)
    finally:
        if set_study_config:
            study_cmod._default_study_config = old_default_study_config


def _execfile(filename):
    # This chunk of code cannot be put inline in python 2.6
    glob_dict = {}
    exec(compile(open(filename, "rb").read(), filename, 'exec'),
          glob_dict, glob_dict)
    return glob_dict

def _get_process_instance(process_or_id, study_config=None, **kwargs):

    def _find_single_process(module_dict, filename):
        ''' Scan objects in module_dict and find out if a single one of them is
        a process
        '''
        object_name = None
        for name, item in six.iteritems(module_dict):
            if is_process(item):
                if object_name is not None:
                    raise KeyError(
                        'file %s contains several processes. Please '
                        'specify which one shoule be used using '
                        'filename.py#ProcessName or '
                        'module.submodule.ProcessName' % filename)
                object_name = name
        return object_name

    result = None
    # If the function 'process_or_id' parameter is already a Process
    # instance.
    if isinstance(process_or_id, Process):
        result = process_or_id

    # If the function 'process_or_id' parameter is a Process class.
    elif (isinstance(process_or_id, type) and
          issubclass(process_or_id, Process)):
        result = process_or_id()

    # If the function 'process_or_id' parameter is already a Nipye
    # interface instance, wrap this structure in a Process class
    elif isinstance(process_or_id, Interface):
        result = nipype_factory(process_or_id)

    # If the function 'process_or_id' parameter is an Interface class.
    elif (isinstance(process_or_id, type) and
          issubclass(process_or_id, Interface)):
        result = nipype_factory(process_or_id())

    # If the function 'process_or_id' parameter is a function.
    elif isinstance(process_or_id, types.FunctionType):
        xml = getattr(process_or_id, 'capsul_xml', None)
        if xml is None:
            # Check docstring
            if process_or_id.__doc__:
                match = process_xml_re.search(
                    process_or_id.__doc__)
                if match:
                    xml = match.group(0)
        if xml:
            result = create_xml_process(process_or_id.__module__,
                                        process_or_id.__name__, 
                                        process_or_id, xml)()
        else:
            raise ValueError('Cannot find XML description to make function {0} a process'.format(process_or_id))
        
    # If the function 'process_or_id' parameter is a class string
    # description
    elif isinstance(process_or_id, basestring):
        py_url = os.path.basename(process_or_id).split('#')
        object_name = None
        as_xml = False
        as_py = False
        module_dict = None
        module = None
        if len(py_url) >= 2 and py_url[-2].endswith('.py') \
                or len(py_url) == 1 and py_url[0].endswith('.py'):
            # python file + process name: something.py#ProcessName
            # or just something.py if it contains only one process class
            if len(py_url) >= 2:
                filename = process_or_id[:-len(py_url[-1]) - 1]
                object_name = py_url[-1]
            else:
                filename = process_or_id
                object_name = None
            glob_dict = _execfile(filename)
            module_name = '__main__'
            if object_name is None:
                object_name = _find_single_process(glob_dict, filename)
            if object_name is not None:
                module_dict = glob_dict
                as_py = True
        if object_name is None:
            elements = process_or_id.rsplit('.', 1)
            if len(elements) < 2:
                module_name, object_name = '__main__', elements[0]
            else:
                module_name, object_name = elements
            try:
                module = importlib.import_module(module_name)
                if object_name not in module.__dict__ \
                        or not is_process(getattr(module, object_name)):
                    # maybe a module with a single process in it
                    module = importlib.import_module(process_or_id)
                    module_dict = module.__dict__
                    object_name = _find_single_process(
                        module_dict, module_name)
                    if object_name is not None:
                        module_name = process_or_id
                        as_py = True
                else:
                    as_py = True
            except ImportError as e:
                pass
        if not as_py:
            # maybe XML filename or URL
            xml_url = process_or_id + '.xml'
            if osp.exists(xml_url):
                object_name = None
            elif process_or_id.endswith('.xml') and osp.exists(process_or_id):
                xml_url = process_or_id
                object_name = None
            else:
                # maybe XML file with pipeline name in it
                xml_url = module_name + '.xml'
                if not osp.exists(xml_url) and module_name.endswith('.xml') \
                        and osp.exists(module_name):
                    xml_url = module_name
                if not osp.exists(xml_url):
                    # try XML file in a module directory + class name
                    basename = None
                    module_name2 = None
                    if module_name in sys.modules:
                        basename = object_name
                        module_name2 = module_name
                        object_name = None # to allow unmatching class / xml
                        if basename.endswith('.xml'):
                            basename = basename[:-4]
                    else:
                        elements = module_name.rsplit('.', 1)
                        if len(elements) == 2:
                            module_name2, basename = elements
                    if module_name2 and basename:
                        try:
                            importlib.import_module(module_name2)
                            mod_dirname = osp.dirname(
                                sys.modules[module_name2].__file__)
                            xml_url = osp.join(mod_dirname, basename + '.xml')
                            if not osp.exists(xml_url):
                                # if basename includes .xml extension
                                xml_url = osp.join(mod_dirname, basename)
                        except ImportError as e:
                            raise ImportError('Cannot import %s: %s'
                                              % (module_name, str(e)))
            as_xml = True
            if osp.exists(xml_url):
                result = create_xml_pipeline(module_name, object_name,
                                             xml_url)()

        if result is None and not as_xml:
            if module_dict is not None:
                module_object = module_dict.get(object_name)
            else:
                module = sys.modules[module_name]
                module_object = getattr(module, object_name, None)
            if module_object is not None:
                if (isinstance(module_object, type) and
                    issubclass(module_object, Process)):
                    result = module_object()
                elif isinstance(module_object, Interface):
                    # If we have a Nipype interface, wrap this structure in a Process
                    # class
                    result = nipype_factory(result)
                elif (isinstance(module_object, type) and
                    issubclass(module_object, Interface)):
                    result = nipype_factory(module_object())
                elif isinstance(module_object, types.FunctionType):
                    xml = getattr(module_object, 'capsul_xml', None)
                    if xml is None:
                        # Check docstring
                        if module_object.__doc__:
                            match = process_xml_re.search(
                                module_object.__doc__)
                            if match:
                                xml = match.group(0)
                    if xml:
                        result = create_xml_process(module_name, object_name,
                                                    module_object, xml)()
            if result is None and module is not None:
                xml_file = osp.join(osp.dirname(module.__file__),
                                    object_name + '.xml')
                if osp.exists(xml_file):
                    result = create_xml_pipeline(module_name, None,
                                                 xml_file)()

    if result is None:
        raise ValueError("Invalid process_or_id argument. "
                         "Got '{0}' and expect a Process instance/string "
                         "description or an Interface instance/string "
                         "description".format(process_or_id))

    # Set the instance default parameters
    for name, value in six.iteritems(kwargs):
        result.set_parameter(name, value)

    if study_config is not None:
        if result.study_config is not None \
                and result.study_config is not study_config:
            raise ValueError("StudyConfig mismatch in get_process_instance "
                             "for process %s" % result)
        result.set_study_config(study_config)
    return result


def get_node_class(node_type):
    """
    Get a custom node class from module + class string.
    The class name is optional if the module contains only one node class.
    It is OK to pass a Node subclass or a Node instance also.
    """
    if inspect.isclass(node_type):
        if issubclass(node_type, Node):
            return node_type # already a Node class
        return Node
    if isinstance(node_type, Node):
        return node_type.__class__
    cls = None
    try:
        mod = importlib.import_module(node_type)
        for name, val in six.iteritems(mod.__dict__):
            if inspect.isclass(val) and val.__name__ != 'Node' \
                    and issubclass(val, Node):
                cls = val
                break
        else:
            return None
    except ImportError:
        name = node_type.split('.')[-1]
        modname = node_type[:-len(name) - 1]
        mod = importlib.import_module(modname)
        cls = getattr(mod, name)
    if cls is None:
        return None
    return name, cls


def get_node_instance(node_type, pipeline, conf_dict=None, **kwargs):
    """
    Get a custom node instance from a module + class name (see
    :func:`get_node_class`) and a configuration dict or Controller.
    The configuration contains parameters needed to instantiate the node type.
    Each node class may specify its parameters via its class method
    `configure_node`.

    Parameters
    ----------
    node_type: str or Node subclass or Node instance
        node type to be built. Either a class (Node subclass) or a Node
        instance (the node will be re-instantiated), or a string
        describing a module and class.
    pipeline: Pipeline
        pipeline in which the node will be inserted.
    conf_dict: dict or Controller
        configuration dict or Controller defining parameters needed to build
        the node. The controller should be obtained using the node class's
        `configure_node()` static method, then filled with the desired values.
        If not given the node is supposed to be built with no parameters, which
        will not work for every node type.
    kwargs:
        default values of the node instance parameters.
    """
    cls_and_name = get_node_class(node_type)
    if cls_and_name is None:
        raise ValueError("Could not find node class %s" % node_type)
    name, cls = cls_and_name

    if isinstance(conf_dict, Controller):
        conf_controller = conf_dict
    elif conf_dict is not None:
        if hasattr(cls, 'configure_controller'):
            conf_controller = cls.configure_controller()
            if conf_controller is None:
                raise ValueError("node type %s has a configuration controller "
                                 "problem (see %s.configure_controller()"
                                 % (node_type, node_type))
            conf_controller.import_from_dict(conf_dict)
        else:
            conf_controller = Controller()
    else:
        if hasattr(cls, 'configure_controller'):
            conf_controller = cls.configure_controller()
        else:
            conf_controller = Controller()
    if hasattr(cls, 'build_node'):
        node = cls.build_node(pipeline, name, conf_controller)
    else:
        # probably bound to fail...
        node = cls(pipeline, name, [], [])

    # Set the instance default parameters
    for name, value in six.iteritems(kwargs):
        setattr(node, name, value)

    return node

