# -*- coding: utf-8 -*-
''' Pipeline main class module

Classes
=======
:class:`Pipeline`
-----------------
'''

from concurrent.futures import process
from copy import deepcopy
import sys

from soma.undefined import undefined


from capsul.process.process import Process, NipypeProcess
from .topological_sort import GraphNode
from .topological_sort import Graph
from .pipeline_nodes import Plug
from .pipeline_nodes import Switch
from .pipeline_nodes import OptionalOutputSwitch

from soma.controller import (Controller, 
                             Event,
                             field,
                             Literal)
from soma.sorted_dictionary import SortedDictionary

class Pipeline(Process):
    """ Pipeline containing Process nodes, and links between node parameters.

    A Pipeline is normally subclassed, and its :py:meth:`pipeline_definition`
    method is overloaded to define its nodes and links.
    :py:meth:`pipeline_definition` will be called by the pipeline constructor.

    ::

        from capsul.pipeline import Pipeline

        class MyPipeline(Pipeline):

          def pipeline_definition(self):
              self.add_process('proc1', 'my_toolbox.my_process1')
              self.add_process('proc2', 'my_toolbox.my_process2')
              self.add_switch('main_switch', ['in1', 'in2'], ['out1', 'out2'])
              self.add_link('proc1.out1->main_switch.in1_switch_out1')
              self.add_link('proc1.out2->main_switch.in1_switch_out2')
              self.add_link('proc2.out1->main_switch.in2_switch_out1')
              self.add_link('proc2.out1->main_switch.in2_switch_out2')

    After execution of :py:meth:`pipeline_definition`, the inner nodes
    parameters which are not connected will be automatically exported to the
    parent pipeline, with names prefixed with their process name, unless they
    are listed in a special "do_not_export" list (passed to
    :py:meth:`add_process` or stored in the pipeline instance).

    >>> pipeline = MyPipeline()
    >>> print(pipeline.proc1_input)
    <undefined>

    **Nodes**

    A pipeline is made of nodes, and links between their parameters. Several
    types of nodes may be part of a pipeline:

    .. currentmodule:: capsul.pipeline

    * process nodes (:py:class:`~capsul.process.process.Process`) are the leaf
      nodes which represent actual processing bricks.
    * pipeline nodes are
      sub-pipelines which allow to reuse an existing pipeline within another
      one
    * switch nodes (:py:class:`pipeline_nodes.Switch`) allows to select values
      between several possible inputs. The switch mechanism also allows to
      select between several alternative processes or processing branches.
    * iterative process (:py:class:process_iteration.ProcessIteration`)
      represent parallel processing of the same pipeline on a set of
      parameters.

    .. currentmodule:: capsul.pipeline.pipeline

    Note that you normally do not instantiate these nodes explicitly when
    building a pipeline. Rather programmers may call the
    :py:meth:`add_process`, :py:meth:`add_switch`,
    :py:meth:`add_iterative_process` methods.

    **Nodes activation**

    Pipeline nodes may be enabled or disabled. Disabling a node will trigger
    a global pipeline nodes activation step, where all nodes which do not form
    a complete chain will be inactive. This way a branch may be disabled by
    disabling one of its nodes. This process is used by the switch system,
    which allows to select one processing branch between several, and disables
    the unselected ones.

    **Pipeline steps**

    Pipelines may define execution steps: they are user-oriented groups of
    nodes that are to be run together, or disabled together for runtime
    execution.
    They are intended to allow partial, or step-by-step execution. They do not
    work like the nodes enabling mechanism described above.

    Steps may be defined within the :py:meth:`pipeline_definition` method.
    See :py:meth:`add_pipeline_step`.

    Note also that pipeline steps only act at the highest level: if a
    sub-pipeline has disabled steps, they will not be taken into account in the
    higher level pipeline execution, because executing by steps a part of a
    sub-pipeline within the context of a higher one does generally not make
    sense.

    **Main methods**

    * :meth:`pipeline_definition`
    * :meth:`add_process`
    * :meth:`add_switch`
    * :meth:`add_custom_node`
    * :meth:`add_iterative_process`
    * :meth:`add_optional_output_switch`
    * :meth:`add_processes_selection`
    * :meth:`add_link`
    * :meth:`remove_link`
    * :meth:`export_parameter`
    * :meth:`autoexport_nodes_parameters`
    * :meth:`add_pipeline_step`
    * :meth:`define_pipeline_steps`
    * :meth:`define_groups_as_steps`
    * :meth:`remove_pipeline_step`
    * :meth:`enable_all_pipeline_steps`
    * :meth:`disabled_pipeline_steps_nodes`
    * :meth:`get_pipeline_step_nodes`
    * :meth:`find_empty_parameters`
    * :meth:`count_items`

    Attributes
    ----------
    nodes: dict {node_name: node}
        a dictionary containing the pipline nodes and where the pipeline node
        name is ''
    workflow_list: list
        a list of odered nodes that can be executed
    workflow_repr: str
        a string representation of the workflow list <node_i>-><node_i+1>

    """

    #Methods
    #-------
    #pipeline_definition
    #add_field
    #add_process
    #add_switch
    #add_link
    #remove_link
    #export_parameter
    #workflow_ordered_nodes
    #workflow_graph
    #update_nodes_and_plugs_activation
    #parse_link
    #parse_parameter
    #find_empty_parameters
    #count_items
    #define_pipeline_steps
    #add_pipeline_step
    #remove_pipeline_step
    #disabled_pipeline_steps_nodes
    #get_pipeline_step_nodes
    #enable_all_pipeline_steps
    #"""

    _doc_path = 'api/pipeline.html#pipeline'

    selection_changed = Event()
    
    # The default value for do_autoexport_nodes_parameters is stored in the
    # pipeline class. This makes it possible to change this default value
    # in derived classes (for instance in DynamicPipeline).
    do_autoexport_nodes_parameters = True
    
    # By default nodes_activation attribute is hidden in user interface. Changing
    # this value to False will make it visible.
    hide_nodes_activation = True

    def __init__(self, autoexport_nodes_parameters=None, **kwargs):
        """ Initialize the Pipeline class

        Parameters
        ----------
        autoexport_nodes_parameters: bool
            if True (default) nodes containing pipeline plugs are automatically
            exported.
        """
        super().__setattr__('enable_parameter_links', False)
        # Inheritance
        if 'definition' not in kwargs:
            kwargs['definition'] = 'custom'
        super(Pipeline, self).__init__()
        super(Pipeline, self).add_field(
            'nodes_activation',
            Controller, hidden=self.hide_nodes_activation)

        # Class attributes
        self.nodes_activation = Controller()
        self.nodes = SortedDictionary()
        self._invalid_nodes = set()
        self._skip_invalid_nodes = set()
        # Get node_position from the Pipeline class if it is
        # defined
        node_position = getattr(self,'node_position', None)
        if node_position:
            self.node_position = node_position.copy()
        else:
            self.node_position = {}
        
        node_dimension = getattr(self,'node_dimension', None)
        if node_dimension:
            self.node_dimension = node_dimension.copy()
        else:
            self.node_dimension = {}
            
        self.nodes[''] = self  # FIXME may cause memory leaks
        self.do_not_export = set()
        self._disable_update_nodes_and_plugs_activation = 1
        self._must_update_nodes_and_plugs_activation = False
        self.pipeline_definition()

        self.workflow_repr = ""
        self.workflow_list = []

        if autoexport_nodes_parameters is None:
            autoexport_nodes_parameters = self.do_autoexport_nodes_parameters
        else:
            self.do_autoexport_nodes_parameters = autoexport_nodes_parameters
        if self.do_autoexport_nodes_parameters:
            self.autoexport_nodes_parameters()

        # Refresh pipeline activation
        self._disable_update_nodes_and_plugs_activation -= 1
        self.update_nodes_and_plugs_activation()
        super().__setattr__('enable_parameter_links', True)
        for k, v in kwargs.items():
            setattr(self, k, v)

    def pipeline_definition(self):
        """ Define pipeline structure, nodes, sub-pipelines, switches, and
        links.

        This method should be overloaded in subclasses, it does nothing in the
        base Pipeline class.
        """
        pass

    def autoexport_nodes_parameters(self, include_optional=False):
        """ Automatically export nodes plugs to the pipeline.

        Some parameters can be explicitly preserved from exportation if they
        are listed in the pipeline "do_not_export" variable (list or set).

        Parameters
        ----------
        include_optional: bool (optional)
            If True (the default), optional plugs are not exported
            Exception: optional output plugs of switches are exported
            (otherwise they are useless). It should probably be any single
            output plug of a node.
        """
        for node_name, node in self.nodes.items():
            if node_name == "":
                    continue
            for parameter_name, plug in node.plugs.items():
                if parameter_name in ("nodes_activation", "selection_changed"):
                    continue
                if ((node_name, parameter_name) not in self.do_not_export and
                    ((plug.output and not plug.links_to) or
                     (not plug.output and not plug.links_from)) and
                    (include_optional
                     or (plug.output and isinstance(node, Switch))
                     or not self.nodes[node_name].field(
                          parameter_name).optional)):

                    self.export_parameter(node_name, parameter_name)

    def remove_field(self, name):
        """ Remove a field from the pipeline

        Parameters
        ----------
        name: str (mandatory)
            the field name
        """
        field = self.field(name)

        # If we remove a field, clear/remove the associated plug
        if name in self.plugs:
            plug = self.plugs[name]
            links_to_remove = []
            # use intermediary links_to_remove to avoid modifying
            # the links set while iterating on it...
            for link in plug.links_to:
                dst = f'{link[0]}.{link[1]}'
                links_to_remove.append(f'{name}->{dst}')
            for link in plug.links_from:
                src = f'{link[0]}.{link[1]}'
                links_to_remove.append(f'{src}->{name}')
            for link in links_to_remove:    
                self.remove_link(link)
            del self.plugs[name]
        super().remove_field(name)

    def _make_subprocess_context_name(self, name):
        ''' build full contextual name on process instance
        '''
        pipeline_name = getattr(self, 'context_name', None)
        if pipeline_name is None:
            pipeline_name = self.name
        context_name = '.'.join([pipeline_name, name])
        return context_name

    def add_process(self, name, process, do_not_export=None,
                    make_optional=None, inputs_to_copy=None,
                    inputs_to_clean=None, skip_invalid=False, **kwargs):
        """ Add a new node in the pipeline

        **Note about invalid nodes:**

        A pipeline can typically offer alternatives (through a switch) to
        different algorithmic nodes, which may have different dependencies, or
        may be provided through external modules, thus can be missing. To handle
        this, Capsul can be telled that a process node can be invalid (or
        missing) without otherwise interfering the rest of the pipeline. This is
        done using the "skip_invalid" option. When used, the process to be added
        is tested, and if its instantiation fails, it will not be added in the
        pipeline, but will not trigger an error. Instead the missing node will
        be marked as "allowed invalid", and links and exports built using this
        node will silently do nothing. thus the pipeline will work normally,
        without the invalid node.

        Such nodes are generally gathered through a switch mechanism. However
        the switch inputs should be restricted to actually available nodes. The
        recommended method is to check that nodes have actually been added in
        the pipeline. Then links can be made normally as if the nodes were all
        present::

            self.add_process('method1', 'module1.Module1', skip_invalid=True)
            self.add_process('method2', 'module2.Module2', skip_invalid=True)
            self.add_process('method3', 'module3.Module3', skip_invalid=True)

            input_params = [n for n in ['method1', 'method2', 'method3']
                            if n in self.nodes]
            self.add_switch('select_method', input_params, 'output')

            self.add_link('method1.input->select_method.method1_switch_output')
            self.add_link('method2.input->select_method.method2_switch_output')
            self.add_link('method3.input->select_method.method3_switch_output')

        A last note about invalid nodes:

        When saving a pipeline (through the :class:`graphical editor
        <capsul.qt_gui.widgets.pipeline_developper_view.PipelineDeveloperView>`
        typically), missing nodes *will not be saved* because they are not
        actually in the pipeline. So be careful to save only pipelines with full
        features.

        Parameters
        ----------
        name: str (mandatory)
            the node name (has to be unique).
        process: Process (mandatory)
            the process we want to add. May be a string ('module.process'), a
            process instance or a class.
        do_not_export: list of str (optional)
            a list of plug names that we do not want to export.
        make_optional: list of str (optional)
            a list of plug names that we do not want to export.
        inputs_to_copy: list of str (optional)
            a list of item to copy.
        inputs_to_clean: list of str (optional)
            a list of temporary items.
        skip_invalid: bool
            if True, if the process is failing (cannot be instantiated), don't
            throw an exception but instead don't insert the node, and mark
            it as such in order to make add_link() to also silently do nothing.
            This option is useful for optional process nodes which may or may
            not be available depending on their dependencies, typically in a
            switch offering several alternative methods.
        """
        # Unique constrains
        make_optional = set(make_optional or [])
        do_not_export = set(do_not_export or [])
        do_not_export.update(kwargs)

        # Check the unicity of the name we want to insert
        if name in self.nodes:
            raise ValueError("Pipeline cannot have two nodes with the "
                             "same name : {0}".format(name))

        if skip_invalid:
            self._skip_invalid_nodes.add(name)
        # Create a process node
        try:
            node = get_process_instance(process, **kwargs)
        except Exception:
            if skip_invalid:
                node = None
                self._invalid_nodes.add(name)
                return
            else:
                raise

        # Update the list of files item to copy
        if inputs_to_copy is not None and hasattr(node, "inputs_to_copy"):
            node.inputs_to_copy.extend(inputs_to_copy)
        if inputs_to_clean is not None and hasattr(node, "inputs_to_clean"):
            node.inputs_to_clean.extend(inputs_to_clean)

        node.set_pipeline(self)
        # Create the pipeline node
        node.name = name
        self.nodes[name] = node

        # If a default value is given to a parameter, change the corresponding
        # plug so that it gets activated even if not linked
        for parameter_name in kwargs:
            if node.field(parameter_name):
                node.plugs[parameter_name].has_default_value = True
                make_optional.add(parameter_name)

        # Change plug default properties
        for parameter_name in node.plugs:
            # Do not export plug
            if (parameter_name in do_not_export or
                    parameter_name in make_optional):
                self.do_not_export.add((name, parameter_name))

            # Optional plug
            if parameter_name in make_optional:
                node.set_optional(parameter_name, True)

        # Create a field to control the node activation (enable property)
        self.nodes_activation.add_field(name, bool)
        setattr(self.nodes_activation, name, node.enabled)

        # Observer
        self.nodes_activation.on_attribute_change.add(self._set_node_enabled,
                                                      name)

    def remove_node(self, node_name):
        """ Remove a node from the pipeline
        """
        node = self.nodes[node_name]
        for plug_name, plug in node.plugs.items():
            if not plug.output:
                for link_def in list(plug.links_from):
                    src_node, src_plug = link_def[:2]
                    link_descr = '%s.%s->%s.%s' \
                                 % (src_node, src_plug, node_name, plug_name)
                    self.remove_link(link_descr)
            else:
                for link_def in list(plug.links_to):
                    dst_node, dst_plug = link_def[:2]
                    link_descr = '%s.%s->%s.%s' \
                                 % (node_name, plug_name, dst_node, dst_plug)
                    self.remove_link(link_descr)
        del self.nodes[node_name]
        self.nodes_activation.on_attribute_change.remove(
            self._set_node_enabled, node_name)
        self.nodes_activation.remove_field(node_name)

    def add_iterative_process(self, name, process, iterative_plugs=None,
                              do_not_export=None, make_optional=None,
                              inputs_to_copy=None, inputs_to_clean=None,
                              **kwargs):
        """ Add a new iterative node in the pipeline.

        Parameters
        ----------
        name: str (mandatory)
            the node name (has to be unique).
        process: Process or str (mandatory)
            the process we want to add.
        iterative_plugs: list of str (optional)
            a list of plug names on which we want to iterate.
            If None, all plugs of the process will be iterated.
        do_not_export: list of str (optional)
            a list of plug names that we do not want to export.
        make_optional: list of str (optional)
            a list of plug names that we do not want to export.
        inputs_to_copy: list of str (optional)
            a list of item to copy.
        inputs_to_clean: list of str (optional)
            a list of temporary items.
        """
        if isinstance(process, str):
            process = get_process_instance(process)
        if iterative_plugs is None:
            forbidden = set(['nodes_activation', 'selection_changed',
                             'pipeline_steps', 'visible_groups'])
            iterative_plugs = [field.name for field in process.fields()
                               if field.name not in forbidden]

        from .process_iteration import ProcessIteration
        context_name = self._make_subprocess_context_name(name)
        self.add_process(
            name,
            ProcessIteration(process, iterative_plugs,
                              context_name=context_name),
            do_not_export, make_optional, **kwargs)
        return

    def call_process_method(self, process_name, method,
                            *args, **kwargs):
        """ Call a method of a process previously added
        with add_process or add_iterative_process.

        Parameters
        ----------
        process_name: str (mandatory)
            name given to the process node.
        method: str (mandatory)
            name of the method to call.
        """
        return getattr(self.nodes[process_name], method)(*args, **kwargs)
    
    def add_switch(self, name, inputs, outputs, export_switch=True,
                   make_optional=(), output_types=None, switch_value=None,
                   opt_nodes=None):
        """ Add a switch node in the pipeline

        Parameters
        ----------
        name: str (mandatory)
            name for the switch node (has to be unique)
        inputs: list of str (mandatory)
            names for switch inputs.
            Switch activation will select amongst them.
            Inputs names will actually be a combination of input and output,
            in the shape "input_switch_output".
            This behaviour is needed when there are several outputs, and thus
            several input groups.
        outputs: list of str (mandatory)
            names for outputs.
        export_switch: bool (optional)
            if True, export the switch trigger to the parent pipeline with
            ``name`` as parameter name
        make_optional: sequence (optional)
            list of optional outputs.
            These outputs will be made optional in the switch output. By
            default they are mandatory.
        output_types: sequence of types or field (optional)
            If given, this sequence should have the same size as outputs. It
            will specify each switch output parameter type. Input parameters 
            for each input block will also have this type.
        switch_value: str (optional)
            Initial value of the switch parameter (one of the inputs names).
            Defaults to 1st input.
        opt_nodes: bool or list
            tells that switch values are node names, and some of them may be
            optional and missing. In such a case, missing nodes are not added
            as inputs. If a list is passed, then it is a list of node names
            which length should match the number of inputs, and which order
            tells nodes related to inputs (in case inputs names are not
            directly node names).

        Examples
        --------
        >>> pipeline.add_switch('group_switch', ['in1', 'in2'],
                                ['out1', 'out2'])

        will create a switch with 4 inputs and 2 outputs:
        inputs: "in1_switch_out1", "in2_switch_out1", "in1_switch_out2",
        "in2_switch_out2"
        outputs: "out1", "out2"

        See Also
        --------
        capsul.pipeline.pipeline_nodes.Switch
        """
        # Check the unicity of the name we want to insert
        if name in self.nodes:
            raise ValueError("Pipeline cannot have two nodes with the same "
                             "name: {0}".format(name))

        if opt_nodes:
            if opt_nodes is True:
                opt_nodes = inputs
            opt_inputs = list(zip(inputs, opt_nodes))
            # filter inputs
            inputs = [i for i, n in opt_inputs if n in self.nodes]
        # Create the node
        node = Switch(self, name, inputs, outputs, make_optional=make_optional,
                      output_types=output_types)
        if opt_nodes:
            node._optional_input_nodes = opt_inputs
        self.nodes[name] = node

        # Export the switch controller to the pipeline node
        if export_switch:
            self.export_parameter(name, "switch", name)

        if switch_value:
            node.switch = switch_value

    def add_optional_output_switch(self, name, input, output=None):
        """ Add an optional output switch node in the pipeline

        An optional switch activates or disables its input/output link
        according to the output value. If the output value is not None or
        Undefined, the link is active, otherwise it is inactive.

        This kind of switch is meant to make a pipeline output optional, but
        still available for temporary files values inside the pipeline.

        Ex:

        A.output -> B.input

        B.input is mandatory, but we want to make A.output available and
        optional in the pipeline outputs. If we directlty export A.output, then
        if the pipeline does not set a value, B.input will be empty and the
        pipeline run will fail.

        Instead we can add an OptionalOutputSwitch between A.output and
        pipeline.output. If pipeline.output is set a valid value, then A.output
        and B.input will have the same valid value. If pipeline.output is left
        Undefined, then A.output and B.input will get a temporary value during
        the run.

        Add an optional output switch node in the pipeline

        Parameters
        ----------
        name: str (mandatory)
            name for the switch node (has to be unique)
        input: str (mandatory)
            name for switch input.
            Switch activation will select between it and a hidden input,
            "_none". Inputs names will actually be a combination of input and
            output, in the shape "input_switch_output".
        output: str (optional)
            name for output. Default is the switch name

        Examples
        --------
        >>> pipeline.add_optional_output_switch('out1', 'in1')
        >>> pipeline.add_link('node1.output->out1.in1_switch_out1')


        See Also
        --------
        capsul.pipeline.pipeline_nodes.OptionalOutputSwitch
        """
        # Check the unicity of the name we want to insert
        if name in self.nodes:
            raise ValueError("Pipeline cannot have two nodes with the same "
                             "name: {0}".format(name))

        if output is None:
            output = name
        # Create the node
        node = OptionalOutputSwitch(self, name, input, output)
        self.nodes[name] = node

    def add_custom_node(self, name, node_type, parameters=None,
                        make_optional=(), do_not_export=None, **kwargs):
        """
        Inserts a custom node (Node subclass instance which is not a Process)
        in the pipeline.

        Parameters
        ----------
        node_type: str or Node subclass or Node instance
            node type to be built. Either a class (Node subclass) or a Node
            instance (the node will be re-instantiated), or a string
            describing a module and class.
        parameters: dict or Controller or None
            configuration dict or Controller defining parameters needed to
            build the node. The controller should be obtained using the node
            class's `configure_node()` static method, then filled with the
            desired values.
            If not given the node is supposed to be built with no parameters,
            which will not work for every node type.
        make_optional: list or tuple
            parameters names to be made optional
        do_not_export: list of str (optional)
            a list of plug names that we do not want to export.
        kwargs: default values of node parameters
        """
        raise NotImplementedError('get_node_instance')
        node = get_node_instance(node_type, self, parameters, name=name,
                                 **kwargs)
        if node is None:
            raise ValueError(
                "could not build a Node of type '%s' with the given parameters"
                % node_type)
        self.nodes[name] = node

        do_not_export = set(do_not_export or [])
        do_not_export.update(kwargs)

        # Change plug default properties
        for parameter_name in node.plugs:
            # Optional plug
            if parameter_name in make_optional:
                node.plugs[parameter_name].optional = True
                field = node.field(parameter_name)
                if field is not None:
                    node.set_optional(field, True)

            # Do not export plug
            if (parameter_name in do_not_export or
                    parameter_name in make_optional):
                self.do_not_export.add((name, parameter_name))

        return node

    def parse_link(self, link, check=True):
        """ Parse a link coming from export_parameter method.

        Parameters
        ----------
        link: str
            the link description of the form
            'node_from.plug_name->node_to.plug_name'
        check: bool
            if True, check that the node and plug exist

        Returns
        -------
        output: tuple
            tuple containing the link description and instances

        Examples
        --------
        >>> Pipeline.parse_link("node1.plug1->node2.plug2")
        "node1", "plug1", <instance node1>, <instance plug1>,
        "node2", "plug2", <instance node2>, <instance plug2>

        For a pipeline node:

        >>> Pipeline.parse_link("plug1->node2.plug2")
        "", "plug1", <instance pipeline>, <instance plug1>,
        "node2", "plug2", <instance node2>, <instance plug2>
        """
        # Split source and destination node descriptions
        source, dest = link.split("->")

        # Parse the source and destination parameters
        err = None
        try:
            source_node_name, source_plug_name, source_node, source_plug = \
                self.parse_parameter(source, check=check)
        except ValueError:
            err = sys.exc_info()
            source_node_name, source_plug_name, source_node, source_plug \
                = (None, None, None, None)
        try:
            dest_node_name, dest_plug_name, dest_node, dest_plug = \
                self.parse_parameter(dest, check=check)
        except ValueError:
            if err or (source_node is not None and source_plug is not None):
                raise
            dest_node_name, dest_plug_name, dest_node, dest_plug \
                = (None, None, None, None)
            err = None
        if err and dest_node is not None and dest_plug is not None and check:
            raise err[0].with_traceback(err[1], err[2])

        return (source_node_name, source_plug_name, source_node, source_plug,
                dest_node_name, dest_plug_name, dest_node, dest_plug)

    def parse_parameter(self, name, check=True):
        """ Parse parameter of a node from its description.

        Parameters
        ----------
        name: str
            the description plug we want to load 'node.plug'
        check: bool
            if True, check that the node and plug exist

        Returns
        -------
        output: tuple
            tuple containing the plug description and instances
        """
        # Parse the plug description
        dot = name.find(".")

        # Check if its a pipeline node
        if dot < 0:
            node_name = ""
            node = self
            plug_name = name
        else:
            node_name = name[:dot]
            node = self.nodes.get(node_name)
            if node is None:
                if node_name in self._invalid_nodes:
                    node = None
                    plug = None
                else:
                    raise ValueError("{0} is not a valid node name".format(
                                    node_name))
            plug_name = name[dot + 1:]

        # Check if plug nexists
        plug = None
        if node is not None:
            if plug_name not in node.plugs:
                if plug_name not in node.invalid_plugs:
                    # adhoc search: look for an invalid node which is the
                    # beginning of the plug name: probably an auto_exported one
                    # from an invalid node
                    err = True
                    if hasattr(node, 'process') \
                            and hasattr(node, '_invalid_nodes'):
                        invalid = node._invalid_nodes
                        for ip in invalid:
                            if plug_name.startswith(ip + '_'):
                                err = False
                                node.invalid_plugs.add(plug_name)
                                break
                    if err and check:
                        raise ValueError(
                            "'{0}' is not a valid parameter name for "
                            "node '{1}'".format(
                                plug_name, (node_name if node_name
                                            else "pipeline")))
            else:
                plug = node.plugs[plug_name]
        return node_name, plug_name, node, plug

    def add_link(self, link, weak_link=False, allow_export=False):
        """ Add a link between pipeline nodes.

        If the destination node is a switch, force the source plug to be not
        optional.

        Parameters
        ----------
        link: str or list/tuple
            link description. Its shape should be:
            "node.output->other_node.input".
            If no node is specified, the pipeline itself is assumed.
            Alternatively the link can be
            (source_node, source_plug_name, dest_node, dest_plug_name)
        weak_link: bool
            this property is used when nodes are optional,
            the plug information may not be generated.
        allow_export: bool
            if True, if the link links from/to the pipeline node with a plug
            name which doesn't exist, the plug will be created, and the
            function will act exactly like export_parameter. This may be a more
            convenient way of exporting/connecting pipeline plugs to several
            nodes without having to export the first one, then link the others.
        """
        check = True
        if allow_export:
            check = False
        if isinstance(link, str):
            # Parse the link
            (source_node_name, source_plug_name, source_node,
            source_plug, dest_node_name, dest_plug_name, dest_node,
            dest_plug) = self.parse_link(link, check=check)
        else:
            (source_node, source_plug_name, dest_node, dest_plug_name) = link
            source_plug = source_node.plugs[source_plug_name]
            dest_plug = dest_node.plugs[dest_plug_name]
            source_node_name = [k for k, n in self.nodes.items()
                                if n is source_node][0]
            dest_node_name = [k for k, n in self.nodes.items()
                              if n is dest_node][0]

        if allow_export:
            if source_node is self.pipeline_node \
                    and source_plug_name not in source_node.plugs:
                print(dest_node_name, dest_node, dest_node.plugs.keys())
                self.export_parameter(dest_node_name, dest_plug_name,
                                      source_plug_name)
                return
            elif dest_node is self.pipeline_node \
                    and dest_plug_name not in dest_node.plugs:
                self.export_parameter(source_node_name, source_plug_name,
                                      dest_plug_name)
                return

        if source_node is None \
                or dest_node is None or source_plug is None \
                or dest_plug is None:
            # link from/to an invalid node
            return

        # Assure that pipeline plugs are not linked
        if (not source_plug.output and source_node is not self):
              raise ValueError(
                  "Cannot link from an input plug: {0}".format(link))
        if (source_plug.output and source_node is self):
            raise ValueError("Cannot link from a pipeline output "
                             "plug: {0}".format(link))
        if (dest_plug.output and dest_node is not self):
            raise ValueError("Cannot link to an output plug: {0}".format(link))
        if (not dest_plug.output and dest_node is self):
            raise ValueError("Cannot link to a pipeline input "
                             "plug: {0}".format(link))

        # Propagate the plug value from source to destination
        value = getattr(source_node, source_plug_name, None)
        if value is not None:
            dest_node.set_plug_value(dest_plug_name, value)

        # Update plugs memory of the pipeline
        source_plug.links_to.add((dest_node_name, dest_plug_name, dest_node,
                                  dest_plug, weak_link))
        dest_plug.links_from.add((source_node_name, source_plug_name,
                                  source_node, source_plug, weak_link))

        # Set a connected_output property
        if (isinstance(dest_node, Process) and
                isinstance(source_node, Process)):
            source_field = source_node.field(source_plug_name)
            dest_field = dest_node.field(dest_plug_name)
            if source_field.is_output() and not dest_field.is_output():
                dest_field.connected_output = True

        # Propagate the doc in case of destination switch node
        if isinstance(dest_node, Switch):
            source_field = source_node.field(source_plug_name)
            dest_field = dest_node.field(dest_plug_name)
            dest_field.doc = source_field.metadata('doc')
            dest_node._switch_changed(getattr(dest_node, "switch", undefined),
                                      getattr(dest_node, "switch", undefined))

        # Refresh pipeline activation
        self.update_nodes_and_plugs_activation()

    def remove_link(self, link):
        """ Remove a link between pipeline nodes

        Parameters
        ----------
        link: str or list/tuple
            link description. Its shape should be:
            "node.output->other_node.input".
            If no node is specified, the pipeline itself is assumed.
            Alternatively the link can be
            (source_node, source_plug_name, dest_node, dest_plug_name)
        """
        if isinstance(link, str):
            # Parse the link
            (source_node_name, source_plug_name, source_node,
            source_plug, dest_node_name, dest_plug_name, dest_node,
            dest_plug) = self.parse_link(link)
        else:
            (source_node, source_plug_name, dest_node, dest_plug_name) = link
            source_plug = source_node.plugs[source_plug_name]
            dest_plug = dest_node.plugs[dest_plug_name]
            source_node_name = [k for k, n in self.nodes.items()
                                if n is source_node][0]
            dest_node_name = [k for k, n in self.nodes.items()
                              if n is dest_node][0]

        if source_node is None or dest_node is None or source_plug is None \
                or dest_plug is None:
            return

        # Update plugs memory of the pipeline
        source_plug.links_to.discard((dest_node_name, dest_plug_name,
                                      dest_node, dest_plug, True))
        source_plug.links_to.discard((dest_node_name, dest_plug_name,
                                      dest_node, dest_plug, False))
        dest_plug.links_from.discard((source_node_name, source_plug_name,
                                      source_node, source_plug, True))
        dest_plug.links_from.discard((source_node_name, source_plug_name,
                                      source_node, source_plug, False))

        # Set a connected_output property
        if (isinstance(dest_node, Process) and
                isinstance(source_node, Process)):
            dest_field = dest_node.field(dest_plug_name)
            if dest_field.metadata('connected_output'):
                dest_field.connected_output = False  # FIXME

        # Refresh pipeline activation
        self.update_nodes_and_plugs_activation()

    def export_parameter(self, node_name, plug_name,
                         pipeline_parameter=None, weak_link=False,
                         is_enabled=None, is_optional=None,
                         allow_existing_plug=None):
        """ Export a node plug at the pipeline level.

        Parameters
        ----------
        node_name: str (mandatory)
            the name of node containing the plug we want to export
        plug_name: str (mandatory)
            the node plug name we want to export
        pipeline_parameter: str (optional)
            the name to access this parameter at the pipeline level.
            Default None, the plug name is used
        weak_link: bool (optional)
            this property is used when nodes are weak,
            which means that the link will not propagate nodes activation
            status.
            The plug information may not be generated.
        is_enabled: bool (optional)
            a property to specify that it is not a user-parameter
            automatic generation)
        is_optional: bool (optional)
            sets the exported parameter to be optional
        allow_existing_plug:bool (optional)
            the same pipeline plug may be connected to several process plugs
        """
        # If a tuned name is not specified, used the plug name
        if not pipeline_parameter:
            pipeline_parameter = plug_name

        # Get the node and parameter
        node = self.nodes.get(node_name)
        if node is None and node_name in self._invalid_nodes:
            # export an invalid plug: mark it as invalid
            self.invalid_plugs.add(pipeline_parameter)
            return

        # Make a copy of the field
        source_field = node.field(plug_name)

        # Check if the plug name is valid
        if source_field is None:
            raise ValueError(f"Node {node_name} ({node.name}) has no parameter "
                             f"{plug_name}")

        # Check the pipeline parameter name is not already used
        if (self.field(pipeline_parameter) and not allow_existing_plug):
            raise ValueError(
                f"Parameter '{plug_name}' of node '{node_name or 'pipeline'}' cannot be exported to pipeline "
                f"parameter '{pipeline_parameter}'")

        f = field(pipeline_parameter, type_=source_field)

        # Set user enabled parameter only if specified
        # Important because this property is automatically set during
        # the nipype interface wrappings
        if is_enabled is not None:
            f.enabled = bool(is_enabled)

        # Now add the parameter to the pipeline
        if not self.field(pipeline_parameter):
            self.add_field(pipeline_parameter, f)

        # Change the field optional property
        if is_optional is not None:
            self.set_optional(f.name, bool(is_optional))

        # Propagate the parameter value to the new exported one
        v = getattr(node, plug_name, undefined)
        setattr(self, pipeline_parameter, v)
        # TODO: catch appropriate error type
        # except dataclass.ValidationError:
        #     pass

        # Do not forget to link the node with the pipeline node

        if f.is_output():
            link_desc = f'{node_name}.{plug_name}->{pipeline_parameter}'
            self.add_link(link_desc,  weak_link)
        else:
            link_desc = f'{pipeline_parameter}->{node_name}.{plug_name}'
            self.add_link(link_desc, weak_link)

    def _set_node_enabled(self, is_enabled, _, node_name):
        """ Method to enable or disabled a node

        Parameters
        ----------
        is_enabled: bool (mandatory)
            the desired property
        old_value: bool
            former is_enabled value (not used)
        node_name: str (mandatory)
            the node name
        """
        node = self.nodes.get(node_name)
        if node:
            node.enabled = is_enabled

    def all_nodes(self):
        """ Iterate over all pipeline nodes including sub-pipeline nodes.

        Returns
        -------
        nodes: Generator of Node
            Iterates over all nodes
        """
        for node in self.nodes.values():
            yield node
            if (isinstance(node, Pipeline) and
               node is not self):
                for sub_node in node.all_nodes():
                    if sub_node is not node:
                        yield sub_node

    def _check_local_node_activation(self, node):
        """ Try to activate a node and its plugs according to its
        state and the state of its direct neighbouring nodes.

        Parameters
        ----------
        node: Node (mandatory)
            node to check

        Returns
        -------
        plugs_activated: list
            list of (plug_name,plug) containing all plugs that have been
            activated
        """
        plugs_activated = []
        # If a node is disabled, it will never be activated
        if node.enabled:
            # Try to activate input plugs
            node_activated = True
            if node is self:
                # For the top-level pipeline node, all enabled plugs
                # are activated
                for plug_name, plug in node.plugs.items():
                    if plug.enabled:
                        if not plug.activated:
                            plug.activated = True
                            plugs_activated.append((plug_name, plug))
            else:
                # Look for input plugs that can be activated
                for plug_name, plug in node.plugs.items():
                    if plug.output:
                        # ignore output plugs
                        continue
                    if plug.enabled and not plug.activated:
                        if plug.has_default_value:
                            plug.activated = True
                            plugs_activated.append((plug_name, plug))
                        else:
                            # Look for a non weak link connected to an
                            # activated plug in order to activate the plug
                            for nn, pn, n, p, weak_link in plug.links_from:
                                if not weak_link and p.activated:
                                    plug.activated = True
                                    plugs_activated.append((plug_name, plug))
                                    break
                    # If the plug is not activated and is not optional the
                    # whole node is deactivated
                    if not plug.activated and not plug.optional:
                        node_activated = False
            if node_activated:
                node.activated = True
                # If node is activated, activate enabled output plugs
                for plug_name, plug in node.plugs.items():
                    if plug.output and plug.enabled:
                        if not plug.activated:
                            plug.activated = True
                            plugs_activated.append((plug_name, plug))
        return plugs_activated

    def _check_local_node_deactivation(self, node):
        """ Check plugs that have to be deactivated according to node
        activation state and to the state of its direct neighbouring nodes.

        Parameters
        ----------
        node: Node (mandatory)
            node to check

        Returns
        -------
        plugs_deactivated: list
            list of (plug_name,plug) containing all plugs that have been
            deactivated
        """
        def check_plug_activation(plug, links):
            # After the following for loop, plug_activated can have three
            # values:
            #  True  if there is a non weak link connected to an
            #        activated plug
            #  False if there are non weak links that are all connected
            #        to inactive plugs
            #  None if there is no non weak links
            plug_activated = None
            # weak_activation will be True if there is at least one
            # weak link connected to an activated plug
            weak_activation = False
            for nn, pn, n, p, weak_link in links:
                if weak_link:
                    weak_activation = (weak_activation or p.activated)
                else:
                    if p.activated:
                        plug_activated = True
                        break
                    else:
                        plug_activated = False
            if plug_activated is None:
                # plug is connected only with weak links therefore
                # they are used to define its activation state
                plug_activated = weak_activation
            return plug_activated

        plugs_deactivated = []
        # If node has already been  deactivated there is nothing to do
        if node.activated:
            deactivate_node = bool(
                [plug for plug in node.plugs.values()
                 if plug.output])
            for plug_name, plug in node.plugs.items():
                # Check all activated plugs
                try:
                    if plug.activated:
                        # A plug with a default value is always activated
                        if plug.has_default_value:
                            continue
                        output = plug.output
                        if (isinstance(node, Pipeline) and
                                node is not self and output):
                            plug_activated = (
                                check_plug_activation(plug, plug.links_to) and
                                check_plug_activation(plug, plug.links_from))
                        else:
                            if node is self:
                                output = not output
                            if output:
                                plug_activated = check_plug_activation(
                                    plug, plug.links_to)
                            else:
                                plug_activated = check_plug_activation(
                                    plug, plug.links_from)

                        # Plug must be deactivated, record it in result and
                        # check if this deactivation also deactivate the node
                        if not plug_activated:
                            plug.activated = False
                            plugs_deactivated.append((plug_name, plug))
                            if not (plug.optional or
                                    node is self):
                                node.activated = False
                                break
                finally:
                    # this must be done even if break or continue has been
                    # encountered
                    if plug.output and plug.activated:
                        deactivate_node = False
            if deactivate_node:
                node.activated = False
                for plug_name, plug in node.plugs.items():
                    if plug.activated:
                        plug.activated = False
                        plugs_deactivated.append((plug_name, plug))
        return plugs_deactivated

    def delay_update_nodes_and_plugs_activation(self):
        parent_pipeline = self.get_pipeline()
        if parent_pipeline is not None:
            # Only the top level pipeline can manage activations
            parent_pipeline.delay_update_nodes_and_plugs_activation()
            return
        if self._disable_update_nodes_and_plugs_activation == 0:
            self._must_update_nodes_and_plugs_activation = False
        self._disable_update_nodes_and_plugs_activation += 1

    def restore_update_nodes_and_plugs_activation(self):
        parent_pipeline = self.get_pipeline()
        if parent_pipeline is not None:
            # Only the top level pipeline can manage activations
            parent_pipeline.restore_update_nodes_and_plugs_activation()
            return
        self._disable_update_nodes_and_plugs_activation -= 1
        if self._disable_update_nodes_and_plugs_activation == 0 and \
                self._must_update_nodes_and_plugs_activation:
            self.update_nodes_and_plugs_activation()

    def update_nodes_and_plugs_activation(self):
        """ Reset all nodes and plugs activations according to the current
        state of the pipeline (i.e. switch selection, nodes disabled, etc.).
        Activations are set according to the following rules.
        """
        parent_pipeline = self.get_pipeline()

        #if not hasattr(self, 'pipeline'):
            ## self is being initialized (the call comes from self.__init__).
            #return

        if parent_pipeline is not None:
            # Only the top level pipeline can manage activations
            parent_pipeline.update_nodes_and_plugs_activation()
            return
        if self._disable_update_nodes_and_plugs_activation:
            self._must_update_nodes_and_plugs_activation = True
            return

        self._disable_update_nodes_and_plugs_activation += 1

        debug = getattr(self, '_debug_activations', None)
        if debug:
            debug = open(debug, 'w')
            print(self.definition, file=debug)

        # Initialization : deactivate all nodes and their plugs
        for node in self.all_nodes():
            node.activated = False
            for plug_name, plug in node.plugs.items():
                plug.activated = False

        # Forward activation : try to activate nodes (and their input plugs)
        # and propagate activations neighbours of activated plugs

        # Starts iterations with all nodes
        nodes_to_check = set(self.all_nodes())
        iteration = 1
        while nodes_to_check:
            new_nodes_to_check = set()
            for node in nodes_to_check:
                node_activated = node.activated
                for plug_name, plug in self._check_local_node_activation(node):
                    if debug:
                        print('%d+%s:%s' % (
                            iteration, node.full_name, plug_name), file=debug)
                    for nn, pn, n, p, weak_link in \
                            plug.links_to.union(plug.links_from):
                        if not weak_link and p.enabled:
                            new_nodes_to_check.add(n)
                if (not node_activated) and node.activated:
                    if debug:
                        print('%d+%s' % (iteration, node.full_name),
                              file=debug)
            nodes_to_check = new_nodes_to_check
            iteration += 1

        # Backward deactivation : deactivate plugs that should not been
        # activated and propagate deactivation to neighbouring plugs
        nodes_to_check = set(self.all_nodes())
        iteration = 1
        while nodes_to_check:
            new_nodes_to_check = set()
            for node in nodes_to_check:
                node_activated = node.activated
                # Test plugs deactivation according to their input/output
                # state
                test = self._check_local_node_deactivation(node)
                if test:
                    for plug_name, plug in test:
                        if debug:
                            print('%d-%s:%s' % (
                                iteration, node.full_name, plug_name),
                                file=debug)
                        for nn, pn, n, p, weak_link in \
                                plug.links_from.union(plug.links_to):
                            if p.activated:
                                new_nodes_to_check.add(n)
                    if not node.activated:
                        # If the node has been deactivated, force deactivation
                        # of all plugs that are still active and propagate
                        # this deactivation to neighbours
                        if node_activated and debug:
                            print('%d-%s' % (iteration, node.full_name),
                                  file=debug)
                        for plug_name, plug in node.plugs.items():
                            if plug.activated:
                                plug.activated = False
                                if debug:
                                    print('%d=%s:%s' % (
                                        iteration, node.full_name, plug_name),
                                        file=debug)
                                for nn, pn, n, p, weak_link in \
                                        plug.links_from.union(plug.links_to):
                                    if p.activated:
                                        new_nodes_to_check.add(n)
            nodes_to_check = new_nodes_to_check
            iteration += 1

        # Refresh views relying on plugs and nodes selection
        for node in self.all_nodes():
            if isinstance(node, Pipeline):
                node.selection_changed.fire()

        self._disable_update_nodes_and_plugs_activation -= 1

    def workflow_graph(self, remove_disabled_steps=True,
                       remove_disabled_nodes=True):
        """ Generate a workflow graph

        Returns
        -------
        graph: topological_sort.Graph
            graph representation of the workflow from the current state of
            the pipeline
        remove_disabled_steps: bool (optional)
            When set, disabled steps (and their children) will not be included
            in the workflow graph.
            Default: True
        remove_disabled_nodes: bool (optional)
            When set, disabled nodes will not be included in the workflow
            graph.
            Default: True
        """

        def insert(pipeline, node_name, node, plug, dependencies, plug_name,
                   links, output=None):
            """ Browse the plug links and add the correspondings edges
            to the node.
            """

            if output is None:
                process = getattr(node, 'process', node)
                field = process.field(plug_name)
                output = field.is_output()

            # Main loop
            for (dest_node_name, dest_plug_name, dest_node, dest_plug,
                 weak_link) in plug.links_to:

                # Ignore the link if it is pointing to a node in a
                # sub-pipeline or in the parent pipeline
                if pipeline.nodes.get(dest_node_name) is not dest_node:
                    continue

                # Plug need to be activated
                if dest_node.activated:

                    # If plug links to an inert node (switch...), we need to
                    # address the node plugs
                    if isinstance(dest_node, Process):
                        dependencies.add((node_name, dest_node_name))
                        if output:
                            links.setdefault(dest_node, {})[dest_plug_name] \
                                = (node, plug_name)
                    elif isinstance(dest_node, Switch):
                        conn = dest_node.connections()
                        for c in conn:
                            if c[0] == dest_plug_name:
                                insert(pipeline, node_name, node,
                                       dest_node.plugs[c[1]],
                                       dependencies, plug_name, links, output)
                                break
                    else:
                        for switch_plug in dest_node.plugs.values():
                            insert(pipeline, node_name, node, switch_plug,
                                   dependencies, plug_name, links, output)

        # Create a graph and a list of graph node edges
        graph = Graph()
        dependencies = set()
        links = {}

        if remove_disabled_steps:
            steps = getattr(self, 'pipeline_steps', Controller())
            disabled_nodes = set()
            for step_field in steps.fields():
                if not getattr(steps, step_field.name, None):
                    disabled_nodes.update(
                        [self.nodes[node]
                         for node in step_field.nodes])

        # Add activated Process nodes in the graph
        for node_name, node in self.nodes.items():

            # Do not consider the pipeline node
            if node_name == '':
                continue

            # Select only active Process nodes
            if (node.activated or not remove_disabled_nodes) \
                    and isinstance(node, Process) \
                    and (not remove_disabled_steps
                         or node not in disabled_nodes):

                # If a Pipeline is found: the meta graph node parameter
                # contains a sub Graph
                if isinstance(node, Pipeline):
                    gnode = GraphNode(
                        node_name, node.workflow_graph(False))
                    gnode.meta.pipeline = node
                    graph.add_node(gnode)

                # If a Process or an iterative node is found: the meta graph
                # node parameter contains a list with one process node or
                # a dynamic structure that cannot be processed yet.
                else:
                    graph.add_node(GraphNode(node_name, [node]))

                # Add node edges
                for plug_name, plug in node.plugs.items():

                    # Consider only active pipeline node plugs
                    if plug.activated:
                        insert(self, node_name, node, plug, dependencies,
                               plug_name, links)

        # Add edges to the graph
        for d in dependencies:
            if graph.find_node(d[0]) and graph.find_node(d[1]):
                graph.add_link(d[0], d[1])

        graph.param_links = links

        return graph

    def workflow_ordered_nodes(self, remove_disabled_steps=True):
        """ Generate a workflow: list of process node to execute

        Returns
        -------
        workflow_list: list of Process
            an ordered list of Processes to execute
        remove_disabled_steps: bool (optional)
            When set, disabled steps (and their children) will not be included
            in the workflow graph.
            Default: True
        """
        # Create a graph and a list of graph node edges
        graph = self.workflow_graph(remove_disabled_steps)

        # Start the topologival sort
        ordered_list = graph.topological_sort()

        def walk_workflow(wokflow, workflow_list):
            """ Recursive function to go through pipelines' graphs
            """
            # Go through all the workflows
            for sub_workflow in wokflow:

                # If we have already a flatten graph structure just add it
                if isinstance(sub_workflow[1], list):
                    workflow_list.extend(sub_workflow[1])

                # Otherwise we need to call the topological sort in order to
                # sort the graph and than flat the graph structure
                else:
                    flat_structure = sub_workflow[1].topological_sort()
                    walk_workflow(flat_structure, workflow_list)

        # Generate the final workflow by flattenin graphs structures
        workflow_list = []
        walk_workflow(ordered_list, workflow_list)

        return workflow_list

    def set_temporary_file_names(self):
        """ Check temporary outputs and allocate files for them.

        Temporary files or directories will be appended to the temp_files list,
        and the node parameters will be set to temp file names.
        """
        for node in self.nodes.values():
            prefix = f'!{{tmp}}/{node.full_name}'
            if isinstance(node, NipypeProcess):
                #nipype processes do not use temporaries, they produce output
                # file names
                return

            for plug_name, plug in node.plugs.items():
                value = getattr(node, plug_name, undefined)
                if not plug.activated or not plug.enabled:
                    continue
                field = node.field(plug_name)
                if not field.is_output():
                    continue
                if field.is_list() and field.has_path():
                    if len([x for x in value if x in ('', undefined)]) == 0:
                        continue
                elif value not in (undefined, '') \
                        or (field.path_type is None
                            or len(plug.links_to) == 0):
                    continue
                # check that it is really temporary: not exported
                # to the main pipeline
                for n, pn in self.get_linked_items(node, plug_name, in_sub_pipelines=False, process_only=False):
                    if n is self:
                        continue
                    continue
                # if we get here, we are a temporary.
                e = field.metadata('extensions')
                if e:
                    suffix = e[0]
                else:
                    suffix = ''
                if isinstance(value, list):
                    new_value = []
                    for i in range(len(value)):
                        if value[i] in ('', undefined):
                            tmp = f'{prefix}.{plug_name}{suffix}'
                            new_value.append(tmp)
                        else:
                            new_value.append(value[i])
                else:
                    new_value = f'{prefix}.{plug_name}{suffix}'
                node.set_plug_value(plug_name, new_value)
                self.dispatch_value(node, plug_name, new_value)
            if node is not self and isinstance(node, Pipeline):
                node.set_temporary_file_names()
 

    def find_empty_parameters(self):
        """ Find internal File/Directory parameters not exported to the main
        input/output parameters of the pipeline with empty values. This is
        meant to track parameters which should be associated with temporary
        files internally.

        Returns
        -------
        list
            Each element is a list with 3 values: node, parameter_name,
            optional
        """
        empty_params = []
        # walk all activated nodes, recursively
        nodes = [(node_name, node)
                 for node_name, node in self.nodes.items()
                 if node_name != '' and node.enabled and node.activated]
        while nodes:
            node_name, node = nodes.pop(0)
            if hasattr(node, 'process'):
                process = node
                if isinstance(process, Pipeline):
                    nodes += [(cnode_name, cnode)
                        for cnode_name, cnode in process.nodes.items()
                        if cnode_name != '' and cnode.enabled
                        and cnode.activated]
            else:
                process = node
            # check output plugs; input ones don't work with generated
            # temporary files (unless they are connected with an output one,
            # which will do the job)
            for plug_name, plug in node.plugs.items():
                if not plug.enabled or not plug.output or \
                        (not plug.activated and plug.optional):
                    continue
                parameter = process.field(plug_name)
                if parameter.is_list():
                    if not parameter.has_path():
                        continue
                elif not parameter.is_path() \
                        or parameter.is_output():
                    # a file with its filename as an output is OK
                    continue
                value = getattr(process, plug_name, undefined)
                if isinstance(value, list):
                    if len(value) == 0 \
                            or len([item for item in value
                                    if item in ('', undefined)]) == 0:
                        continue # non-empty list or all values non-empty
                    # here we have null values
                elif value != '' and value is not undefined:
                    continue # non-null value: not an empty parameter.
                optional = process.field(parameter).optional
                valid = True
                links = list(plug.links_from.union(plug.links_to))
                if len(links) == 0:
                    if optional:
                        # an optional, non-connected output can stay empty
                        continue
                # check where this plug is linked
                while links:
                    link = links.pop(0)
                    oplug = link[3]
                    if link[0] == '':
                        if link[2] == self.nodes['']:
                            # linked to the main node: keep it as is
                            valid = False
                            break
                        if isinstance(link[2], Process):
                            lproc = link[2]
                            lfield = lproc.field(link[1])
                            if lfield.is_output():
                                # connected to an output file which filename
                                # is actually an output: it will be generated
                                # by the process, thus is not a temporary
                                valid = False
                                break
                        # linked to an output plug of an intermediate pipeline:
                        # needed only if this pipeline plug is used later,
                        # or mandatory
                        if oplug.optional:
                            links += oplug.links_to
                    optional &= bool(oplug.optional)
                if valid:
                    empty_params.append((node, plug_name, optional))
        return empty_params

    def count_items(self):
        """ Count pipeline items to get its size.

        Returns
        -------
        items: tuple
            (nodes_count, processes_count, plugs_count, params_count,
            links_count, enabled_nodes_count, enabled_procs_count,
            enabled_links_count)
        """
        nodes = list(self.nodes.values())
        plugs_count = 0
        params_count = len([param
            for param in self.fields()
            if param.name not in ('nodes_activation', 'selection_changed')])
        nodes_count = 0
        links_count = 0
        procs = set()
        nodeset = set()
        enabled_nodes_count = 0
        enabled_procs_count = 0
        enabled_links_count = 0
        while nodes:
            node = nodes.pop(0)
            nodeset.add(node)
            nodes_count += 1
            if node.enabled and node.activated:
                enabled_nodes_count += 1
            plugs_count += len(node.plugs)
            links_count += sum([len(plug.links_to) + len(plug.links_from)
                for plug in node.plugs.values()])
            enabled_links_count += sum(
                [len([pend for pend in plug.links_to
                        if pend[3].enabled and pend[3].activated])
                    + len([pend for pend in plug.links_from
                        if pend[3].enabled and pend[3].activated])
                    for plug in node.plugs.values()
                    if plug.enabled and plug.activated])
            if hasattr(node, 'nodes'):
                sub_nodes = [sub_node
                    for sub_node in node.nodes.values()
                    if sub_node not in nodeset and sub_node not in nodes]
                nodes += sub_nodes
            elif hasattr(node, 'execute'):
                if node in procs:
                    continue
                procs.add(node)
                if node.enabled and node.activated:
                    enabled_procs_count += 1
                params_count += len([param
                    for param
                    in node.fields()
                    if param.name not in (
                        'nodes_activation', 'selection_changed')])
                if hasattr(node, 'nodes'):
                    sub_nodes = [sub_node
                        for sub_node in node.nodes.values()
                        if sub_node not in nodeset and sub_node not in nodes]
                    nodes += sub_nodes
            else:
                params_count += len([param
                    for param in node.fields()
                    if param.name not in (
                        'nodes_activation', 'selection_changed', 'activated',
                        'enabled', 'name')])
        return nodes_count, len(procs), plugs_count, params_count, \
            links_count, enabled_nodes_count, enabled_procs_count, \
            enabled_links_count

    def pipeline_state(self):
        """ Return an object composed of basic Python objects that contains
        the whole structure and state of the pipeline. This object can be
        given to compare_to_state method in order to get the differences with
        a previously stored state. This is typically used in tests scripts.

        Returns
        -------
        pipeline_state: dictionary
            todo
        """
        result = {}
        for node in self.all_nodes():
            plugs_list = []
            node_dict = dict(name=node.name,
                             enabled=node.enabled,
                             activated=node.activated,
                             plugs=plugs_list)
            result[node.full_name] = node_dict
            for plug_name, plug in node.plugs.items():
                links_to_dict = {}
                links_from_dict = {}
                plug_dict = dict(enabled=plug.enabled,
                                 activated=plug.activated,
                                 output=plug.output,
                                 optional=plug.optional,
                                 has_default_value=plug.has_default_value,
                                 links_to=links_to_dict,
                                 links_from=links_from_dict)
                plugs_list.append((plug_name, plug_dict))
                for nn, pn, n, p, weak_link in plug.links_to:
                    link_name = '%s:%s' % (n.full_name, pn)
                    links_to_dict[link_name] = weak_link
                for nn, pn, n, p, weak_link in plug.links_from:
                    link_name = '%s:%s' % (n.full_name, pn)
                    links_from_dict[link_name] = weak_link
        return result

    def compare_to_state(self, pipeline_state):
        """ Returns the differences between this pipeline and a previously
        recorded state.

        Returns
        -------
        differences: list
            each element is a human readable string explaining one difference
            (e.g. 'node "my_process" is missing')
        """
        result = []
        
        def compare_dict(ref_dict, other_dict):
            for ref_key, ref_value in ref_dict.items():
                if ref_key not in other_dict:
                    yield '%s = %s is missing' % (ref_key, repr(ref_value))
                else:
                    other_value = other_dict.pop(ref_key)
                    if ref_value != other_value:
                        yield '%s = %s differs from %s' % (ref_key,
                                                           repr(ref_value),
                                                           repr(other_value))
            for other_key, other_value in other_dict.items():
                yield '%s=%s is new' % (other_key, repr(other_value))

        pipeline_state = deepcopy(pipeline_state)
        for node in self.all_nodes():
            node_name = node.full_name
            node_dict = pipeline_state.pop(node_name, None)
            if node_dict is None:
                result.append('node "%s" is missing' % node_name)
            else:
                plugs_list = node_dict.pop('plugs')
                result.extend('in node "%s": %s' % (node_name, i) for i in
                              compare_dict(dict(name=node.name,
                                                enabled=node.enabled,
                                                activated=node.activated),
                                           node_dict))
                ref_plug_names = list(node.plugs)
                other_plug_names = [i[0] for i in plugs_list]
                if ref_plug_names != other_plug_names:
                    if sorted(ref_plug_names) == sorted(other_plug_names):
                        result.append('in node "%s": plugs order = %s '
                                      'differs from %s' %
                                      (node_name, repr(ref_plug_names),
                                       repr(other_plug_names)))
                    else:
                        result.append('in node "%s": plugs list = %s '
                                      'differs from %s' %
                                      (node_name, repr(ref_plug_names),
                                       repr(other_plug_names)))
                        # go to next node
                        continue
                for plug_name, plug in node.plugs.items():
                    plug_dict = plugs_list[0][1]
                    del plugs_list[0]
                    links_to_dict = plug_dict.pop('links_to')
                    links_from_dict = plug_dict.pop('links_from')
                    result.extend('in plug "%s:%s": %s' %
                        (node_name,plug_name,i) for i in
                        compare_dict(dict(enabled=plug.enabled,
                                          activated=plug.activated,
                                          output=plug.output,
                                          optional=plug.optional,
                                          has_default_value=
                                              plug.has_default_value),
                                          plug_dict))
                    for nn, pn, n, p, weak_link in plug.links_to:
                        link_name = '%s:%s' % (n.full_name, pn)
                        if link_name not in links_to_dict:
                            result.append('in plug "%s:%s": missing link to %s'
                                          % (node_name, plug_name, link_name))
                        else:
                            other_weak_link = links_to_dict.pop(link_name)
                            if weak_link != other_weak_link:
                                result.append('in plug "%s:%s": link to %s is'
                                              '%sweak' % (node_name, plug_name,
                                                          link_name, (' not'
                                                          if weak_link else 
                                                          '')))
                    for link_name, weak_link in links_to_dict.items():
                        result.append('in plug "%s:%s": %slink to %s is new' %
                            (node_name,plug_name, (' weak' if weak_link else 
                            ''),link_name))
                    for nn, pn, n, p, weak_link in plug.links_from:
                        link_name = '%s:%s' % (n.full_name, pn)
                        if link_name not in links_from_dict:
                            result.append('in plug "%s:%s": missing link from '
                                          '%s' % (node_name,
                                                  plug_name, link_name))
                        else:
                            other_weak_link = links_from_dict.pop(link_name)
                            if weak_link != other_weak_link:
                                result.append('in plug "%s:%s": link from %s '
                                              'is%sweak' % (node_name, 
                                                            plug_name,
                                                            link_name,(' not'
                                                            if weak_link else
                                                            '')))
                    for link_name, weak_link in links_from_dict.items():
                        result.append('in plug "%s:%s": %slink from %s is new'
                                      % (node_name,plug_name,(' weak' if
                                          weak_link else ''),link_name))

        for node_name in pipeline_state:
            result.append('node "%s" is new' % node_name)
        return result

    def define_pipeline_steps(self, steps):
        '''Define steps in the pipeline.
        Steps are pipeline portions that form groups, and which can be enabled
        or disabled on a runtime basis (when building workflows).

        Once steps are defined, their activation may be accessed through the
        "step" attribute, which has one boolean property for each step:

        Ex:

        ::

            steps = OrderedDict()
            steps['preprocessings'] = [
                'normalization',
                'bias_correction',
                'histo_analysis']
            steps['brain_extraction'] = [
                'brain_segmentation',
                'hemispheres_split']
            pipeline.define_pipeline_steps(steps)

        >>> print(pipeline.pipeline_steps.preprocessings)
        True

        >>> pipeline.pipeline_steps.brain_extraction = False

        See also add_pipeline_step()

        Parameters
        ----------
        steps: dict or preferably OrderedDict or SortedDictionary (mandatory)
            The steps dict keys are steps names, the values are lists of nodes
            names forming the step.
        '''
        for step_name, nodes in steps.items():
            self.add_pipeline_step(step_name, nodes)

    def add_pipeline_step(self, step_name, nodes, enabled=True):
        '''Add a step definition to the pipeline (see also define_steps).

        Steps are groups of pipeline nodes, which may be disabled at runtime.
        They are normally defined in a logical order regarding the workflow
        streams. They are different from pipelines in that steps are purely
        virtual groups, they do not have parameters.

        Disabling a step acts differently as the pipeline node activation: 
        other nodes are not inactivated according to their dependencies.
        Instead, those steps are not run.

        Parameters
        ----------
        step_name: string (mandatory)
            name of the new step
        nodes: list or sequence
            nodes contained in the step (Node instances)
        enabled: bool (optional)
            initial state of the step
        '''
        if not self.field('pipeline_steps'):
            super().add_field(
                'pipeline_steps',
                Controller, doc=
                    'Steps are groups of pipeline nodes, which may be '
                    'disabled at runtime. They are normally defined in a '
                    'logical order regarding the workflow streams. They are '
                    'different from sub-pipelines in that steps are purely '
                    'virtual groups, they do not have parameters. To activate '
                    'or diasable a step, just do:\n'
                    'pipeline.steps.my_step = False\n'
                    '\n'
                    'To get the nodes list in a step:\n'
                    'pipeline.get_step_nodes("my_step")',
                expanded = False,
                default_factory = lambda: Controller())
        self.pipeline_steps.add_field(step_name, bool, nodes=nodes)
        setattr(self.pipeline_steps, step_name, enabled)

    def remove_pipeline_step(self, step_name):
        '''Remove the given step
        '''
        if self.pipeline_steps.field('pipeline_steps'):
            self.pipeline_steps.remove_field(step_name)

    def disabled_pipeline_steps_nodes(self):
        '''List nodes disabled for runtime execution

        Returns
        -------
        disabled_nodes: list
            list of pipeline nodes (Node instances) which will not run in
            a workflow created from this pipeline state.
        '''
        steps = getattr(self, 'pipeline_steps', Controller())
        disabled_nodes = []
        for field in steps.fields():  # noqa: F402
            if not getattr(steps, field.name, True):
                # disabled step
                nodes = field.nodes
                disabled_nodes.extend([self.nodes[node] for node in nodes])
        return disabled_nodes

    def get_pipeline_step_nodes(self, step_name):
        '''Get the nodes in the given pipeline step
        '''
        return self.pipeline_steps.field(step_name).nodes

    def enable_all_pipeline_steps(self):
        '''Set all defined steps (using add_step() or define_steps()) to be
        enabled. Useful to reset the pipeline state after it has been changed.
        '''
        steps = getattr(self, 'pipeline_steps', Controller())
        for field in steps.fields():  # noqa: F402
            setattr(steps, field.name, True)

    def _change_processes_selection(self, selection_group, _, selection_name):
        self.delay_update_nodes_and_plugs_activation()
        for group, processes in \
                self.processes_selection[selection_name].items():
            enabled = (group == selection_group)
            for node_name in processes: 
                self.nodes[node_name].enabled = enabled
        self.restore_update_nodes_and_plugs_activation()

    def add_processes_selection(self, selection_parameter, selection_groups,
                                value=None):
        '''Add a processes selection switch definition to the pipeline.

        Selectors are a "different" kind of switch: one pipeline node set in a
        group is enabled, the others are disabled.

        The selector has 2 levels:

        selection_parameter selects a group.

        A group contains a set of nodes which will be activated together.
        Groups are mutually exclusive.

        Parameters
        ----------
        selection_parameter: string (mandatory)
            name of the selector parameter: the parameter is added in the
            pipeline, and its value is the name of the selected group.
        selection_groups: dict or OrderedDict
            nodes groups contained in the selector : {group_name: [Node names]}
        value: str (optional)
            initial state of the selector (default: 1st group)
        '''
        group_names = tuple(selection_groups.keys())
        self.add_field(selection_parameter, Literal[group_names],
                       default=group_names[0])
        self.nodes[''].plugs[selection_parameter].has_default_value = True
        self.processes_selection = getattr(self, 'processes_selection', {})
        self.processes_selection[selection_parameter] = selection_groups
        self.on_attribute_change.add(self._change_processes_selection,
                                     selection_parameter)
        self._change_processes_selection(
            getattr(self, selection_parameter), None, selection_parameter)
        if value is not None:
            setattr(self, selection_parameter, value)

    def get_processes_selections(self):
        '''Get process_selection groups names (corresponding to selection
        parameters on the pipeline)
        '''
        if not hasattr(self, 'processes_selection'):
            return []
        return list(self.processes_selection.keys())

    def get_processes_selection_groups(self, selection_parameter):
        '''Get groups names involved in a processes selection switch
        '''
        return self.processes_selection[selection_parameter]

    def get_processes_selection_nodes(self, selection_parameter, group):
        '''Get nodes names involved in a processes selection switch with
        value group
        '''
        return self.processes_selection.get(selection_parameter, {}).get(group)

    def define_groups_as_steps(self, exclusive=True):
        ''' Define parameters groups according to which steps they are
        connected to.

        Parameters
        ----------
        exclusive: bool (optional)
            if True, a parameter is assigned to a single group, the first step
            it is connected to. If False, a parameter is assigned all steps
            groups it is connected to.
        '''
        steps = getattr(self, 'pipeline_steps', None)
        if not steps:
            return
        inv_steps = {}
        steps_priority = {}
        p = 0
        for step_field in steps.fields():
            nodes = step_field.nodes
            steps_priority[step_field.name] = p
            p += 1
            for node in nodes:
                inv_steps[node] = step_field.name

        if not self.field('visible_groups'):
            # add a field without a plug
            Controller.add_field(self, 'visible_groups', set)
        plugs = self.plugs
        for field in self.fields():  # noqa: F402
            plug = plugs.get(field.name)
            if not plug:
                continue
            if field.is_output():
                links = plug.links_from
            else:
                links = plug.links_to
            groups = []
            for link in links:
                node_name = link[0]
                step = inv_steps.get(node_name)
                if step and step not in groups:
                    groups.append(step)
            if groups:
                groups = sorted(groups, key=lambda x: steps_priority[x])
                if exclusive:
                    groups = [groups[0]]
                field.groups = groups

    def check_requirements(self, environment='global', message_list=None):
        '''
        Reimplementation for pipelines of
        :meth:`capsul.process.process.Process.check_requirements <Process.check_requirements>`

        A pipeline will return a list of unique configuration values.
        '''
        # start with pipeline-level requirements
        conf = super(Pipeline, self).check_requirements(
            environment, message_list=message_list)
        if conf is None:
            return None
        confs = []
        if conf:
            confs.append(conf)
        from capsul.pipeline import pipeline_tools
        success = True
        for key, node in self.nodes.items():
            if node is self:
                continue
            if pipeline_tools.is_node_enabled(self, key, node):
                conf = node.check_requirements(
                    environment,
                    message_list=message_list)
                if conf is None:
                    # requirement failed
                    if message_list is None:
                        # return immediately
                        return None
                    else:
                        success = False
                else:
                    if conf != {} and conf not in confs:
                        if isinstance(conf, list):
                            confs += [c for c in conf if c not in confs]
                        else:
                            confs.append(conf)
        if success:
            return confs
        else:
            return None

    def rename_node(self, old_node_name, new_node_name):
        '''
        Change the name of the selected node and updates the pipeline.

        Parameters
        ----------
        old_node_name: str
            old node name
        new_node_name: str
            new node name
        '''
        if new_node_name in list(self.nodes.keys()):
            raise ValueError("Node name already in pipeline")

        else:

            node = self.nodes[old_node_name]

            # Removing links of the selected node and copy
            # the origin/destination
            links_to_copy = []
            for parameter, plug in node.plugs.items():
                if plug.output:
                    for (dest_node_name, dest_parameter, dest_node, dest_plug,
                        weak_link) in plug.links_to:
                        slinks = dest_plug.links_from
                        slinks.remove((old_node_name, parameter, node, plug,
                                      weak_link))
                        slinks.add((new_node_name, parameter, node, plug,
                                    weak_link))

                else:
                    for (dest_node_name, dest_parameter, dest_node, dest_plug,
                        weak_link) in plug.links_from:
                        slinks = dest_plug.links_to
                        slinks.remove((old_node_name, parameter, node, plug,
                                      weak_link))
                        slinks.add((new_node_name, parameter, node, plug,
                                    weak_link))

            # change the node entry with the new name and delete the former
            self.nodes[new_node_name] = node
            del self.nodes[old_node_name]

            # look for the node in the pipeline_steps, if any
            steps = getattr(self, 'pipeline_steps', None)
            if steps:
                for field in steps.fields():  # noqa: F402
                    nodes = field.nodes
                    if old_node_name in nodes:
                        field.nodes = \
                            [n if n != old_node_name
                            else new_node_name
                            for n in nodes]

            # nodes positions and dimensions
            if old_node_name in getattr(self, 'node_position', {}):
                self.node_position[new_node_name] \
                    = self.node_position[old_node_name]
                del self.node_position[old_node_name]
            if old_node_name in getattr(self, 'node_dimension', {}):
                self.node_dimension[new_node_name] \
                    = self.node_dimension[old_node_name]
                del self.node_dimension[old_node_name]

    def get_connections_through(self, plug_name, single=False):
        if not self.activated or not self.enabled:
            return []

        plug = self.plugs[plug_name]
        if plug.output:
            links = plug.links_from
        else:
            links = plug.links_to
        dest_plugs = []
        for link in links:
            done = False
            if not link[2].activated or not link[2].enabled:
                continue  # skip disabled nodes
            if link[2] is self:
                # other side of the pipeline
                if link[3].output:
                    more_links = link[3].links_to
                else:
                    more_links = link[3].links_from
                if not more_links:
                    # going outside the pipeline which seems to be top-level:
                    # keep it
                    dest_plugs.append((link[2], link[1], link[3]))
                    if single:
                        done = True
                for other_link in more_links:
                    other_end = other_link[2].get_connections_through(
                        other_link[1], single)
                    dest_plugs += other_end
                    if other_end and single:
                        done = True
                        break
            else:
                other_end = link[2].get_connections_through(link[1], single)
                dest_plugs += other_end
                if other_end and single:
                    done = True
            if done:
                break
        return dest_plugs

    def __setattr__(self, name, value):
        result = super().__setattr__(name, value)
        if self.enable_parameter_links and name in self.plugs:
            self.dispatch_value(self, name, value)
        return result
    
    def dispatch_value(self, node, name, value):
        self.enable_parameter_links = False
        done = set()
        stack = list(self.get_linked_items(node, 
            name, 
            in_sub_pipelines=False,
            activated_only=False,
            process_only=False))
        while stack:
            item = stack.pop()
            if item not in done:
                node, plug = item
                setattr(node, plug, value)
                done.add(item)
                stack.extend(self.get_linked_items(node, 
                    plug, 
                    in_sub_pipelines=False,
                    activated_only=False,
                    process_only=False))
        self.enable_parameter_links = True

    def get_linked_items(self, node, plug_name=None, in_sub_pipelines=True, activated_only=True, process_only=True):
        '''Return the real process(es) node and plug connected to the given plug.
        Going through switches and inside subpipelines, ignoring nodes that are
        not activated.
        The result is a generator of pairs (node, plug_name).
        '''
        if plug_name is None:
            stack =[(node, plug) for plug in node.plugs]
        else:
            stack =[(node, plug_name)]
        while stack:
            node, plug_name = stack.pop(0)
            if activated_only and not node.activated:
                continue
            plug = node.plugs.get(plug_name)
            if plug:
                if plug.output ^ isinstance(node, Pipeline):
                    direction = 'links_to'
                else:
                    direction = 'links_from'
                for dest_plug_name, dest_node in (i[1:3] for i in getattr(plug, direction)):
                    if isinstance(dest_node, Pipeline):
                        if in_sub_pipelines:
                            yield from dest_node.get_linked_items(dest_node, dest_plug_name)
                        else:
                            yield (dest_node, dest_plug_name)
                    elif isinstance(dest_node, Process):
                        yield (dest_node, dest_plug_name)
                    elif isinstance(dest_node, Switch):
                        if dest_plug_name == 'switch':
                            if not process_only:
                                yield (dest_node, dest_plug_name)
                        else:
                            for input_plug_name, output_plug_name in dest_node.connections():
                                if plug.output ^ isinstance(node, Pipeline):
                                    if dest_plug_name == input_plug_name:
                                        if not process_only:
                                            yield (dest_node, output_plug_name)
                                        stack.append((dest_node, output_plug_name))
                                else:
                                    if dest_plug_name == output_plug_name:
                                        if not process_only:
                                            yield (dest_node, input_plug_name)
                                        stack.append((dest_node, input_plug_name))

    def json(self):
        if self.definition == 'custom':
            return {
                'type': 'custom_pipeline',
                'definition': self.json_definition(),
                'parameters': super(Process, self).json(),
            }
        else:
            result = super().json()
            result['type'] = 'pipeline'
            return result

    def json_definition(self):
        result = {}

        if hasattr(self, "__doc__"):
            docstr = self.__doc__
            if docstr == Pipeline.__doc__:
                docstr = ''  # don't use the builtin Pipeline help
            else:
                # remove automatically added doc
                splitdoc = docstr.split('\n')
                notepos = [i for i, x in enumerate(splitdoc[:-2])
                              if x.endswith('.. note::')]
                autodocpos = None
                if notepos:
                    for i in notepos:
                        if splitdoc[i+2].find(
                                f"* Type '{self.__class__.__name__}.help()'") != -1:
                            autodocpos = i
                if autodocpos is not None:
                    # strip empty trailing lines
                    while autodocpos >= 1 \
                            and splitdoc[autodocpos - 1].strip() == '':
                        autodocpos -= 1
                    docstr = '\n'.join(splitdoc[:autodocpos]) + '\n'
        else:
            docstr = ''
        if docstr.strip() == '':
            docstr = ''
        result['doc'] = docstr

        for node_name, node in self.nodes.items():
            if node_name == "":
                continue
            if isinstance(node, Switch):
                raise NotImplementedError('Serialization of Switch not implemented')
            elif isinstance(node, Process):
                node_json = node.json()
                result.setdefault('executables', {})[node_name] = node_json
            else:
                raise NotImplementedError(f'Serialization of {type(node)} not implemented')
            if not node.enabled:
                node_json['enabled'] = False
        return result


# This import is at the end because get_process_instance needs Pipeline and
#  Pipeline needs get_process instance
from capsul.process_instance import get_process_instance
