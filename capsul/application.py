import dataclasses
import importlib
import importlib.resources
import inspect
import json
import os
import sys
import types
from pathlib import Path

from soma.controller import Controller, field
from soma.singleton import Singleton
from soma.undefined import undefined

from .config.configuration import ApplicationConfiguration
from .dataset import Dataset
from .pipeline.pipeline import CustomPipeline, Pipeline
from .pipeline.process_iteration import ProcessIteration
from .process.process import Node, Process

# note: nipype and related imports are not done here to avoid several seconds
# of import time when we don't use them.


def _is_nipype_interface(obj):
    """Checks whether the given object is an instance of a nipype interface.

    It basically behaves like isinstance(obj, NipypeInterface), but avoids to
    import nipype modules if they are not already loaded (in which case the
    object is definitely _not_ a nipype interface), because this import may
    take several seconds, and we want to load capsul _fast_.
    """
    if "nipype.interfaces.base" not in sys.modules:
        return False
    npype_base = sys.modules["nipype.interfaces.base"]
    NipypeInterface = npype_base.Interface
    return isinstance(obj, NipypeInterface)


def _is_nipype_interface_subclass(obj):
    """Checks whether the given object is a subclass of a nipype interface.

    It basically behaves like issubclass(obj, NipypeInterface), but avoids to
    import nipype modules if they are not already loaded (in which case the
    object is definitely _not_ a nipype interface), because this import may
    take several seconds, and we want to load capsul _fast_.
    """
    if "nipype.interfaces.base" not in sys.modules:
        return False
    npype_base = sys.modules["nipype.interfaces.base"]
    NipypeInterface = npype_base.Interface
    return issubclass(obj, NipypeInterface)


class Capsul:
    """User entry point to Capsul features.
    This objects reads Capsul configuration in site and user environments.
    It allows configuration customization and instantiation of a
    CapsulEngine instance to reach an execution environment.

    If database_path is given, it replaces
    self.config['databases']['builtin'].path after all site and user
    configuration is read.

    Example:

        from capsul.api import Capsul
        capsul = Capsul()
        e = capsul.executable('capsul.process.test.test_runprocess.DummyProcess')
        with capsul.engine() as capsul_engine:
            capsul_engine.run(e)

    """

    def __init__(
        self,
        app_name="capsul",
        user_file=undefined,
        site_file=undefined,
        database_path=None,
    ):
        if user_file is undefined:
            user_file = os.environ.get("CAPSUL_USER_CONFIG")
            if user_file is None:
                for user_file in (
                    f"~/.config/{app_name}/capsul_user.json",
                    f"~/.config/{app_name}/capsul_user.py",
                ):
                    user_file = os.path.expanduser(user_file)
                    if os.path.exists(user_file):
                        break
                else:
                    user_file = None
            elif not user_file:
                user_file = None
        if site_file is undefined:
            site_file = os.environ.get("CAPSUL_SITE_CONFIG")
            if site_file is None:
                for site_file in (
                    os.path.expandvars("$CASA_CONF/capsul_site.json"),
                    os.path.expandvars("$CASA_CONF/capsul_site.py"),
                    f"/etc/{app_name}/capsul_site.json",
                    f"/etc/{app_name}/capsul_site.py",
                ):
                    if os.path.exists(site_file):
                        break
                else:
                    site_file = None
            elif not site_file:
                site_file = None
        if isinstance(site_file, Path):
            site_file = str(site_file)
        if isinstance(user_file, Path):
            user_file = str(user_file)
        # print("User configuration file", user_file)
        # print("Site configuration file", site_file)
        self.label = app_name
        c = ApplicationConfiguration(
            app_name=app_name, user_file=user_file, site_file=site_file
        )
        self.config = c.merged_config
        if database_path is not None:
            self.config.databases["builtin"]["path"] = database_path

    @staticmethod
    def is_executable(item):
        """Check if the input item is a process class or function with decorator"""
        if (
            isinstance(item, type)
            and item not in (Pipeline, Process)
            and (issubclass(item, Process) or _is_nipype_interface_subclass(item))
        ):
            return True
        if not inspect.isfunction(item):
            return False
        if item.__annotations__:
            return True
        return False

    @staticmethod
    def executable(definition, **kwargs):
        """Get an "executable" instance
        (:class:`~capsul.process.process.Process`,
        :class:`~capsul.pipeline.pipeline.Pipeline...)` from its module or file
        name.
        """
        return executable(definition, **kwargs)

    def engines(self):
        for field in self.config.fields():  # noqa: F402
            if field.name != "databases":
                yield self.engine(field.name)

    def engine(self, name="builtin", workers_count=None, update_database=False):
        """Get a :class:`~capsul.engine.Engine` instance"""
        from .engine import Engine

        # get engine type from config
        engine_config = getattr(self.config, name, None)
        if engine_config is None:
            raise ValueError(f'engine "{name}" is not configured.')
        if workers_count is not None:
            engine_config.start_workers = engine_config.start_workers.copy()
            engine_config.start_workers["count"] = workers_count
        return Engine(
            name,
            engine_config,
            databases_config=self.config.databases,
            update_database=update_database,
        )

    @staticmethod
    def dataset(path):
        """Get a :class:`~.dataset.DataSet` instance associated with the given path

        Parameters
        ----------
        path: :class:`pathlib.Path`
            path for the dataset
        """
        return Dataset(path)

    @staticmethod
    def custom_pipeline():
        return CustomPipeline()

    @classmethod
    def executable_iteration(
        cls, executable, non_iterative_plugs=None, iterative_plugs=None
    ):
        """Create a ProcessIteration to run several times (in parallel
        if possible) the same executable with different parameters.

        Parameters
        ----------
        non_iterative_plugs: list (optional)
            passed to :meth:`ProcessIteration.__init__`
        iterative_plugs: list (optional)
            passed to :meth:`ProcessIteration.__init__`
        Returns
        -------
        iteration: :class:`ProcessIteration` instance
        """
        process = cls.executable(executable)
        if iterative_plugs is not None:
            if non_iterative_plugs is not None:
                raise ValueError(
                    "Both iterative_plugs and non_iterative_plugs are "
                    "specified - they are mutually exclusive"
                )
        else:
            forbidden = {
                "nodes_activation",
                "selection_changed",
                "pipeline_steps",
                "visible_groups",
                "enabled",
                "activated",
                "node_type",
            }
            if non_iterative_plugs:
                forbidden.update(non_iterative_plugs)
            iterative_plugs = [
                field.name for field in process.fields() if field.name not in forbidden
            ]

        iterative_process = ProcessIteration(
            definition=f"{process.definition}[]",
            process=process,
            iterative_parameters=iterative_plugs,
        )
        return iterative_process


def executable(definition, **kwargs):
    """
    Build a Process instance given a definition item.
    This definition item can be :
      - A dictionary containing the JSON serialization of a process.
        A new instance is created by desierializing this dictionary.
      - A process instance.
    """
    result = None
    item = None
    if isinstance(definition, dict):
        result = executable_from_json(None, definition)
    elif isinstance(definition, Process):
        if kwargs:
            raise ValueError(
                "executable() do not allow to modify parameters of an existing process"
            )
        return definition
    elif isinstance(definition, type) and issubclass(definition, Process):
        # A class is given as definition. Check that it can be imported.
        module_name = definition.__module__
        object_name = definition.__name__
        try:
            module = importlib.import_module(module_name)
        except ImportError as e:
            raise TypeError(
                f"Class {definition} cannot be used to create a Process "
                "because its module cannot be imported : {e}"
            ) from e
        cls = getattr(module, object_name, None)
        if cls is not definition:
            raise TypeError(
                f"Class {definition} cannot be used to create a Process "
                f"because variable {object_name} of module {module_name} "
                f"contains {cls}"
            )
        result = definition(definition=f"{module_name}.{object_name}")
    elif inspect.isfunction(definition):
        if definition.__module__ == "__main__":
            raise ValueError(
                "Cannot create a process from a function defined in a script. Please provide a function defined in a Python module."
            )
        function = definition
        definition = f"{function.__module__}.{function.__name__}"
        result = executable_from_python(definition, function)
    else:
        if definition.endswith(".json"):
            with open(definition, encoding="utf-8") as f:
                json_executable = json.load(f)
            result = executable_from_json(definition, json_executable)
        elif definition.endswith(".py") or len(definition.rsplit(".py#")) == 2:
            filename = definition
            object_name = None
            def_item = definition.rsplit(".py#")
            if len(def_item) == 2:
                # class/function name after # in the definition
                object_name = def_item[1]
                filename = def_item[0] + ".py"
            d = {}
            with open(filename) as f:
                exec(f.read(), d, d)
            if object_name:
                process = d.get(object_name)
                if process is None:
                    raise ValueError(f"Invalid executable definition: {definition}")
            else:
                processes = [
                    i
                    for i in d.values()
                    if isinstance(i, type)
                    and issubclass(i, Node)
                    and i not in (Node, Process, Pipeline)
                ]
                if not processes:
                    # TODO: try to find a function process
                    raise ValueError(f"No process class found in {definition}")
                if len(processes) > 1:
                    raise ValueError(f"Several process classes found in {definition}")
                process = processes[0]
            result = executable_from_python(definition, process)
        else:
            elements = definition.rsplit(".", 1)
            if len(elements) > 1:
                module_name, object_name = elements
                module = importlib.import_module(module_name)
                item = getattr(module, object_name, None)
                if item is None:
                    # maybe a sub-module to be imported
                    try:
                        module = importlib.import_module(definition)
                    except ModuleNotFoundError:
                        module = None
                    if module is not None:
                        item = module
                # check if item is a module containing a single process
                if inspect.ismodule(item) or (
                    inspect.isclass(item) and not issubclass(item, Node)
                ):
                    items = find_executables(item)
                    if len(items) == 1:
                        module = item
                        item = items[0]
                        definition = ".".join(
                            (definition, item.__name__.rsplit(".")[-1])
                        )
                    elif len(items) > 1:
                        raise ValueError(
                            f"Several process classes found in {definition}"
                        )
                if item is not None:
                    result = executable_from_python(definition, item)
                if result is None:
                    # maybe a JSON-defined pipeline
                    try:
                        is_resource = importlib.resources.is_resource(
                            module_name, object_name + ".json"
                        )
                    except TypeError:  # if module_name is not a package
                        is_resource = False
                    if is_resource:
                        with importlib.resources.open_text(
                            module_name, object_name + ".json"
                        ) as f:
                            json_executable = json.load(f)
                        result = executable_from_json(definition, json_executable)

    if result is not None:
        for f in result.fields():
            wf = result.writable_field(f)
        for name, value in kwargs.items():
            setattr(result, name, value)
        return result
    raise ValueError(f"Invalid executable definition: {definition}")


def find_executables(module):
    """Look for "executables" (:class:`~.process.node.Node` classes) in the
    given module
    """
    # report only Node classes, since it's difficult to be sure a function
    # is meant to be a Process or not.
    items = []
    for item in module.__dict__.values():
        if (
            inspect.isclass(item)
            and issubclass(item, Node)
            and item not in (Node, Process, Pipeline)
        ):
            items.append(item)
    return items


def executable_from_python(definition, item):
    """
    Build a process instance from a Python object and its definition string.
    """
    result = None
    # If item is already a Process
    # instance.
    if isinstance(item, Process):
        result = item

    # If item is a Process class.
    elif isinstance(item, type) and issubclass(item, Process):
        result = item(definition=definition)

    # If item is a Nipye
    # interface instance, wrap this structure in a Process class
    elif _is_nipype_interface(item):
        from .process.nipype_process import nipype_factory

        result = nipype_factory(definition, item)

    # If item is a Nipype Interface class.
    elif isinstance(item, type) and _is_nipype_interface_subclass(item):
        from .process.nipype_process import nipype_factory

        result = nipype_factory(item())

    # If item is a function.
    elif isinstance(item, types.FunctionType):
        annotations = getattr(item, "__annotations__", None)
        if annotations:
            result = process_from_function(item)(definition=definition)
        else:
            raise ValueError(
                f"Cannot find annotation description to make function {item} a process"
            )

    else:
        raise ValueError(f"Cannot create an executable from {item}")

    return result


def executable_from_json(definition, json_executable):
    """
    Build a process instance from a JSON dictionary and its definition string.
    """
    process_definition = json_executable.get("definition")
    if process_definition is None:
        raise ValueError(f"definition missing from process defined in {definition}")
    type = json_executable.get("type")
    if type is None:
        raise ValueError(f"type missing from process defined in {definition}")
    if definition is None:
        definition = json_executable.get("definition")
    if type in ("process", "pipeline"):
        result = executable(process_definition)
        if definition is not None:
            result.definition = definition
    elif type == "custom_pipeline":
        result = CustomPipeline(
            definition=definition, json_executable=process_definition
        )
    elif type == "iterative_process":
        result = ProcessIteration(
            definition=definition,
            process=executable(process_definition["process"]),
            iterative_parameters=process_definition["iterative_parameters"],
            context_name=process_definition["context_name"],
        )
    else:
        raise ValueError(f"Invalid executable type in {definition}: {type}")
    uuid = json_executable.get("uuid")
    if uuid:
        result._uuid = uuid
    parameters = json_executable.get("parameters")
    if parameters:
        result.import_json(parameters)
    return result


def process_from_function(function):
    """
    Build a process instance from an annotated function.
    """
    annotations = {}
    for name, type_ in getattr(function, "__annotations__", {}).items():
        output = name == "return"
        if isinstance(type_, dataclasses.Field):
            metadata = {}
            metadata.update(type_.metadata)
            metadata.update(type_.metadata.get("_metadata", {}))
            if "_metadata" in metadata:
                del metadata["_metadata"]
            metadata["output"] = output
            default = type_.default
            default_factory = type_.default_factory
            kwargs = dict(
                type_=type_.type,
                default=default,
                default_factory=default_factory,
                repr=type_.repr,
                hash=type_.hash,
                init=type_.init,
                compare=type_.compare,
                metadata=metadata,
            )
        else:
            kwargs = dict(type_=type_, default=undefined, output=output)
        if output:
            # "return" cannot be used as a parameter because it is a Python keyword.
            #  Change it to "result"
            name = "result"
        annotations[name] = field(**kwargs)

    def wrap(self, context):
        kwargs = {
            i: getattr(self, i)
            for i in annotations
            if i != "result" and getattr(self, i, undefined) is not undefined
        }
        self.result = function(**kwargs)

    namespace = {
        "__annotations__": annotations,
        "execute": wrap,
    }
    name = f"{function.__name__}_process"
    return type(name, (Process,), namespace)


def get_node_class(node_type):
    """
    Get a custom node class from module + class string.
    The class name is optional if the module contains only one node class.
    It is OK to pass a Node subclass or a Node instance also.
    """
    if inspect.isclass(node_type):
        if issubclass(node_type, Node):
            return node_type.__name__, node_type  # already a Node class
        return Node
    if isinstance(node_type, Node):
        return node_type.__class__.__name__, node_type.__class__
    cls = None
    try:
        mod = importlib.import_module(node_type)
        for name, val in mod.__dict__.items():
            if (
                inspect.isclass(val)
                and val.__name__ != "Node"
                and issubclass(val, Node)
            ):
                cls = val
                break
        else:
            return None
    except ImportError:
        name = node_type.split(".")[-1]
        modname = node_type[: -len(name) - 1]
        mod = importlib.import_module(modname)
        cls = getattr(mod, name)
    if cls is None:
        return None
    return name, cls


def get_node_instance(node_type, pipeline, conf_dict=None, name=None, **kwargs):
    """
    Get a custom node instance from a module + class name (see
    :func:`executable`) and a configuration dict or Controller.
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
    if cls_and_name is None or issubclass(cls_and_name[1], Process):
        raise ValueError("Could not find node class %s" % node_type)
    nname, cls = cls_and_name
    if not name:
        name = nname

    if isinstance(conf_dict, Controller):
        conf_controller = conf_dict
    elif conf_dict is not None:
        if hasattr(cls, "configure_controller"):
            conf_controller = cls.configure_controller()
            if conf_controller is None:
                raise ValueError(
                    "node type %s has a configuration controller "
                    "problem (see %s.configure_controller()" % (node_type, node_type)
                )
            conf_controller.import_dict(conf_dict)
        else:
            conf_controller = Controller()
    else:
        if hasattr(cls, "configure_controller"):
            conf_controller = cls.configure_controller()
        else:
            conf_controller = Controller()
    if hasattr(cls, "build_node"):
        node = cls.build_node(pipeline, name, conf_controller)
    else:
        # probably bound to fail...
        node = cls(pipeline, name, [], [])

    # Set the instance default parameters
    for name, value in kwargs.items():
        setattr(node, name, value)

    return node


_interface = None
_nipype_loaded = False


def _get_interface_class():
    """
    returns the nypype Interface type, or a custom type if it cannot be
    imported.
    We use this function on demand because importing nipype is long (it
    sometimes takes several seconds) and it's not always needed.
    We don't really import nipype, but use sys.modules to get it instead,
    because here we only use Interface to check if a given object is an
    instance of Interface.
    """
    global _interface, _nipype_loaded
    if _interface is not None and _nipype_loaded:
        return _interface
    if not _nipype_loaded:
        # Nipype import
        nipype = sys.modules.get("nipype.interfaces.base")
        if nipype is None:
            _interface = type("Interface", (object,), {})
        else:
            _interface = nipype.Interface
            _nipype_loaded = True
    return _interface


def is_executable(item):
    """Check if the input item is a process class or function with annotations"""
    Interface = _get_interface_class()
    if (
        inspect.isclass(item)
        and item not in (Pipeline, Process)
        and (issubclass(item, Process) or issubclass(item, Interface))
    ):
        return True
    if not inspect.isfunction(item):
        return False
    if hasattr(item, "__annotations__"):
        return True
    return False
