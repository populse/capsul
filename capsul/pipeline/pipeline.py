# -*- coding: utf-8 -*-
''' Pipeline main class module

Classes
=======
:class:`Pipeline`
-----------------
'''

from __future__ import print_function
from __future__ import absolute_import

# System import
import logging
from copy import deepcopy
import tempfile
import os
import shutil
import sys
import six
from soma.utils.weak_proxy import weak_proxy, get_ref
from six.moves import range
from six.moves import zip
from collections import OrderedDict

# Define the logger
logger = logging.getLogger(__name__)

# Trait import
try:
    import traits.api as traits
    from traits.api import (File, Enum, Bool,
                            Event, Directory, Trait, List, Set)
except ImportError:
    import enthought.traits.api as traits
    from enthought.traits.api import (File, Enum, Bool,
                                      Event, Directory, Trait, List, Set)

# Capsul import
from capsul.process.process import Process, NipypeProcess
from .topological_sort import GraphNode
from .topological_sort import Graph
from .pipeline_nodes import Plug
from .pipeline_nodes import ProcessNode
from .pipeline_nodes import PipelineNode
from .pipeline_nodes import Switch
from .pipeline_nodes import OptionalOutputSwitch

# Soma import
from soma.controller import Controller
from soma.controller import ControllerTrait
from soma.controller.trait_utils import relax_exists_constraint
from soma.sorted_dictionary import SortedDictionary
from soma.utils.functiontools import SomaPartial

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

    * process nodes (:py:class:`pipeline_nodes.ProcessNode`) are the leaf nodes
      which represent actual processing bricks.
    * pipeline nodes (:py:class:`pipeline_nodes.PipelineNode`) are
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
    #add_trait
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
    
    # By default nodes_activation trait is hidden in user interface. Changing
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
        # Inheritance
        super(Pipeline, self).__init__(**kwargs)
        super(Pipeline, self).add_trait(
            'nodes_activation',
            ControllerTrait(Controller(), hidden=self.hide_nodes_activation))

        # Class attributes
        # this one is only useful to maintain subprocesses/subpipelines life
        self.list_process_in_pipeline = []
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
        
        
        ###############add by Irmage OM ######################### 
        node_dimension = getattr(self,'node_dimension', None)
        if node_dimension:
            self.node_dimension = node_dimension.copy()
        else:
            self.node_dimension = {}
        #########################################################
            
            
        self.pipeline_node = PipelineNode(self, '', self)
        self.nodes[''] = self.pipeline_node
        self.do_not_export = set()
        self.parent_pipeline = None
        self._disable_update_nodes_and_plugs_activation = 1
        self._must_update_nodes_and_plugs_activation = False
        self.pipeline_definition()

        self.workflow_repr = ""
        self.workflow_list = []

        if autoexport_nodes_parameters is None:
            autoexport_nodes_parameters = self.do_autoexport_nodes_parameters
        if autoexport_nodes_parameters:
            self.autoexport_nodes_parameters()

        # Refresh pipeline activation
        self._disable_update_nodes_and_plugs_activation -= 1
        self.update_nodes_and_plugs_activation()

    ##############
    # Methods    #
    ##############

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
        for node_name, node in six.iteritems(self.nodes):
            if node_name == "":
                    continue
            for parameter_name, plug in six.iteritems(node.plugs):
                if parameter_name in ("nodes_activation", "selection_changed"):
                    continue
                if (((node_name, parameter_name) not in self.do_not_export and
                    ((plug.output and not plug.links_to) or
                     (not plug.output and not plug.links_from)) and
                    (include_optional
                     or (plug.output and isinstance(node, Switch))
                     or not self.nodes[node_name].get_trait(
                          parameter_name).optional))):

                    self.export_parameter(node_name, parameter_name)

    def add_trait(self, name, trait):
        """ Add a trait to the pipeline

        Parameters
        ----------
        name: str (mandatory)
            the trait name
        trait: trait instance (mandatory)
            the trait we want to add
        """
        # Add the trait
        super(Pipeline, self).add_trait(name, trait)
        #self.get(name)

        # If we insert a user trait, create the associated plug
        if getattr(self, 'pipeline_node', False) and self.is_user_trait(trait):
            output = bool(trait.output)
            optional = bool(trait.optional)
            plug = Plug(output=output, optional=optional)
            self.pipeline_node.plugs[name] = plug
            plug.on_trait_change(self.update_nodes_and_plugs_activation,
                                 'enabled')

    def remove_trait(self, name):
        """ Remove a trait to the pipeline

        Parameters
        ----------
        name: str (mandatory)
            the trait name
        """
        if name in self.traits():
            trait = self.traits()[name]

        # If we remove a user trait, clear/remove the associated plug
            if (self.is_user_trait(trait) and
              name in self.pipeline_node.plugs):
                plug = self.pipeline_node.plugs[name]
                links_to_remove = []
            # use intermediary links_to_remove to avoid modifying the links set
            # while iterating on it...
                for link in plug.links_to:
                    dst = '%s.%s' % (link[0], link[1])
                    links_to_remove.append('%s->%s' % (name, dst))
                for link in plug.links_from:
                    src = '%s.%s' % (link[0], link[1])
                    links_to_remove.append('%s->%s' % (src, name))
                for link in links_to_remove:    
                    self.remove_link(link)
                del self.pipeline_node.plugs[name]

        # Remove the trait
        super(Pipeline, self).remove_trait(name)

    def reorder_traits(self, names):
        """ Reimplementation of :class:`~soma.controller.controller.Controller`
        method :meth:`~~soma.controller.controller.Controller.reorder_traits`
        so that we also reorder the pipeline node plugs.
        """
        pnames = names
        if 'nodes_activation' not in names:
            # keep nodes_activation first since it's normally the first added
            pnames = ['nodes_activation'] + list(names)
        super(Pipeline, self).reorder_traits(pnames)
        old_keys = self.pipeline_node.plugs.sortedKeys
        self.pipeline_node.plugs.sortedKeys \
            = [k for k in names if k in old_keys] \
              + [k for k in old_keys if k not in names]

    def _make_subprocess_context_name(self, name):
        ''' build full contextual name on process instance
        '''
        pipeline_name = getattr(self, 'context_name', None)
        if pipeline_name is None:
            pipeline_name = self.name
        context_name = '.'.join([pipeline_name, name])
        return context_name

    def _set_subprocess_context_name(self, process, name):
        ''' set full contextual name on process instance
        '''
        pipeline_name = getattr(self, 'context_name', None)
        if pipeline_name is None:
            pipeline_name = self.name
        process.context_name = '.'.join([pipeline_name, name])
        # do it recursively if process is a pipeline
        if isinstance(process, Pipeline):
            todo = [process]
            while todo:
                cur_proc = todo.pop(0)
                for nname, node in six.iteritems(cur_proc.nodes):
                    if nname == '':
                        continue
                    sub_proc = getattr(node, 'process', None)
                    if sub_proc is not None:
                        sub_proc.context_name \
                            = '.'.join([cur_proc.context_name, nname])
                        if isinstance(sub_proc, Pipeline):
                            todo.append(sub_proc)

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

        # It is necessary not to import study_config.process_instance at 
        # the module level because there are circular dependencies between
        # modules. For instance, Pipeline class needs get_process_instance
        # which needs create_xml_pipeline which needs Pipeline class.
        from capsul.study_config.process_instance import get_process_instance
        if skip_invalid:
            self._skip_invalid_nodes.add(name)
        # Create a process node
        try:
            process = get_process_instance(process,
                                           study_config=self.study_config,
                                           **kwargs)
        except Exception:
            if skip_invalid:
                process = None
                self._invalid_nodes.add(name)
                return
            else:
                raise
        # set full contextual name on process instance
        self._set_subprocess_context_name(process, name)

        # Update the kwargs parameters values according to process
        # default values
        for k, v in six.iteritems(process.default_values):
            kwargs.setdefault(k, v)

        # Update the list of files item to copy
        if inputs_to_copy is not None and hasattr(process, "inputs_to_copy"):
            process.inputs_to_copy.extend(inputs_to_copy)
        if inputs_to_clean is not None and hasattr(process, "inputs_to_clean"):
            process.inputs_to_clean.extend(inputs_to_clean)

        # Create the pipeline node
        if isinstance(process, Pipeline):
            node = process.pipeline_node
            node.name = name
            node.pipeline = self
            process.parent_pipeline = weak_proxy(self)
        else:
            node = ProcessNode(self, name, process)
        self.nodes[name] = node

        # If a default value is given to a parameter, change the corresponding
        # plug so that it gets activated even if not linked
        for parameter_name in kwargs:
            if parameter_name in process.traits():
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
                node.plugs[parameter_name].optional = True
                process = getattr(node, 'process')
                if process is not None:
                    process.trait(parameter_name).optional = True
            # forbid_completion
            if process.trait(parameter_name).forbid_completion:
                self.propagate_metadata(node, parameter_name,
                                        {'forbid_completion': True})

        # Create a trait to control the node activation (enable property)
        self.nodes_activation.add_trait(name, Bool)
        setattr(self.nodes_activation, name, node.enabled)

        # Observer
        self.nodes_activation.on_trait_change(self._set_node_enabled, name)

        # Add new node in pipeline process list to keep its life
        self.list_process_in_pipeline.append(process)

    def remove_node(self, node_name):
        """ Remove a node from the pipeline
        """
        node = self.nodes[node_name]
        for plug_name, plug in six.iteritems(node.plugs):
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
        if hasattr(node, 'process'):
            self.list_process_in_pipeline.remove(node.process)
            self.nodes_activation.on_trait_change(
                self._set_node_enabled, node_name, remove=True)
            self.nodes_activation.remove_trait(node_name)

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
            # It is necessary not to import study_config.process_instance at
            # the module level because there are circular dependencies between
            # modules. For instance, Pipeline class needs get_process_instance
            # which needs create_xml_pipeline which needs Pipeline class.
            from capsul.study_config.process_instance \
                import get_process_instance
            process = get_process_instance(process)
        if iterative_plugs is None:
            forbidden = set(['nodes_activation', 'selection_changed',
                             'pipeline_steps', 'visible_groups'])
            iterative_plugs = [pname for pname in process.user_traits()
                               if pname not in forbidden]

        from .process_iteration import ProcessIteration
        context_name = self._make_subprocess_context_name(name)
        self.add_process(
            name,
            ProcessIteration(process, iterative_plugs,
                              study_config=self.study_config,
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
        return getattr(self.nodes[process_name].process, method)(*args,
                                                                 **kwargs)
    
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
        output_types: sequence of traits (optional)
            If given, this sequence should have the same size as outputs. It
            will specify each switch output parameter type (as a standard
            trait). Input parameters for each input block will also have this
            type.
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

        self._set_subprocess_context_name(node, name)
        study_config = getattr(self, 'study_config', None)
        if study_config:
            node.set_study_config(study_config)

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

        self._set_subprocess_context_name(node, name)
        study_config = getattr(self, 'study_config', None)
        if study_config:
            node.set_study_config(study_config)

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
        # It is necessary not to import study_config.process_instance at
        # the module level because there are circular dependencies between
        # modules. For instance, Pipeline class needs get_process_instance
        # which needs create_xml_pipeline which needs Pipeline class.
        from capsul.study_config.process_instance import get_node_instance
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
                trait = node.trait(parameter_name)
                if trait is not None:
                    trait.optional = True

            # Do not export plug
            if (parameter_name in do_not_export or
                    parameter_name in make_optional):
                self.do_not_export.add((name, parameter_name))

        study_config = getattr(self, 'study_config', None)
        if study_config:
            node.set_study_config(study_config)

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
            six.reraise(*err)

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
        nodes = name.split('.')
        plug_name = nodes[-1]
        nodes.pop(-1)

        node = self.pipeline_node
        node_name = ''
        for pnode in nodes:
            node = node.process.nodes.get(pnode)
            node_name = pnode
            if node is None:
                if node_name in self._invalid_nodes:
                    node = None
                    plug = None
                    break
                else:
                    raise ValueError("{0} is not a valid node name".format(
                                    node_name))

        # Check if plug exists
        plug = None
        if node is not None:
            if plug_name not in node.plugs:
                if plug_name not in node.invalid_plugs:
                    # adhoc search: look for an invalid node which is the
                    # beginning of the plug name: probably an auto_exported one
                    # from an invalid node
                    err = True
                    if hasattr(node, 'process') \
                            and hasattr(node.process, '_invalid_nodes'):
                        invalid = node.process._invalid_nodes
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

    def add_link(self, link, weak_link=False, allow_export=False, value=None):
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
        value: any
            if given, set this value instead of the source plug value
        """
        check = True
        if allow_export:
            check = False
        if isinstance(link, six.string_types):
            # Parse the link
            (source_node_name, source_plug_name, source_node,
            source_plug, dest_node_name, dest_plug_name, dest_node,
            dest_plug) = self.parse_link(link, check=check)
        else:
            (source_node, source_plug_name, dest_node, dest_plug_name) = link
            source_plug = source_node.plugs[source_plug_name]
            dest_plug = dest_node.plugs[dest_plug_name]
            source_node_name = [k for k, n in six.iteritems(self.nodes)
                                if n is source_node][0]
            dest_node_name = [k for k, n in six.iteritems(self.nodes)
                              if n is dest_node][0]

        if allow_export:
            if source_plug is None:
                source_node.process.export_parameter(
                    dest_node_name, dest_plug_name, source_plug_name)
                return
            elif dest_plug is None:
                dest_node.process.export_parameter(
                    source_node_name, source_plug_name, dest_plug_name)
                return

        if source_node is None \
                or dest_node is None or source_plug is None \
                or dest_plug is None:
            # link from/to an invalid node
            return

        # Assure that pipeline plugs are not linked
        if (not source_plug.output and source_node is not self.pipeline_node):
              raise ValueError(
                  "Cannot link from an input plug: {0}".format(link))
        if (source_plug.output and source_node is self.pipeline_node):
            raise ValueError("Cannot link from a pipeline output "
                             "plug: {0}".format(link))
        if (dest_plug.output and dest_node is not self.pipeline_node):
            raise ValueError("Cannot link to an output plug: {0}".format(link))
        if (not dest_plug.output and dest_node is self.pipeline_node):
            raise ValueError("Cannot link to a pipeline input "
                             "plug: {0}".format(link))

        # the destination of the link should not expect an already existing
        # file value, since it will come as an output from the source.
        trait = dest_node.get_trait(dest_plug_name)
        relax_exists_constraint(trait)

        # Propagate the plug value from source to destination
        if value is None:
            value = source_node.get_plug_value(source_plug_name)
        if value is not None:
            dest_node.set_plug_value(dest_plug_name, value)

        # Update plugs memory of the pipeline
        source_plug.links_to.add((dest_node_name, dest_plug_name, dest_node,
                                  dest_plug, weak_link))
        dest_plug.links_from.add((source_node_name, source_plug_name,
                                  source_node, source_plug, weak_link))

        # Set a connected_output property
        if (isinstance(dest_node, ProcessNode) and
                isinstance(source_node, ProcessNode)):
            source_trait = source_node.process.trait(source_plug_name)
            dest_trait = dest_node.process.trait(dest_plug_name)
            if source_trait.output and not dest_trait.output:
                dest_trait.connected_output = True

        # Propagate the description in case of destination switch node
        if isinstance(dest_node, Switch):
            source_trait = source_node.get_trait(source_plug_name)
            dest_trait = dest_node.trait(dest_plug_name)
            dest_trait.desc = source_trait.desc
            dest_node._switch_changed(getattr(dest_node, "switch"),
                                      getattr(dest_node, "switch"))

        # if completion is forbidden on source or dest, propagate the other
        # side
        forbid_completion \
            = source_node.get_trait(source_plug_name).forbid_completion
        if forbid_completion:
            self.propagate_metadata(source_node, source_plug_name,
                                    {'forbid_completion': True})
        elif trait.forbid_completion:
            self.propagate_metadata(dest_node, dest_plug_name,
                                    {'forbid_completion': True})

        # Observer
        source_node.connect(source_plug_name, dest_node, dest_plug_name)
        dest_node.connect(dest_plug_name, source_node, source_plug_name)

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
        if isinstance(link, six.string_types):
            # Parse the link
            (source_node_name, source_plug_name, source_node,
            source_plug, dest_node_name, dest_plug_name, dest_node,
            dest_plug) = self.parse_link(link)
        else:
            (source_node, source_plug_name, dest_node, dest_plug_name) = link
            source_plug = source_node.plugs[source_plug_name]
            dest_plug = dest_node.plugs[dest_plug_name]
            source_node_name = [k for k, n in six.iteritems(self.nodes)
                                if n is source_node][0]
            dest_node_name = [k for k, n in six.iteritems(self.nodes)
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
        if (isinstance(dest_node, ProcessNode) and
                isinstance(source_node, ProcessNode)):
            dest_trait = dest_node.process.trait(dest_plug_name)
            if dest_trait.connected_output:
                dest_trait.connected_output = False  # FIXME

        # Observer
        source_node.disconnect(source_plug_name, dest_node, dest_plug_name)
        dest_node.disconnect(dest_plug_name, source_node, source_plug_name)

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
            **FIXME:** what does it exactly mean ?
            the plug information may not be generated.
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
            self.pipeline_node.invalid_plugs.add(pipeline_parameter)
            return

        # Make a copy of the trait
        source_trait = node.get_trait(plug_name)

        # Check if the plug name is valid
        if source_trait is None:
            raise ValueError("Node {0} ({1}) has no parameter "
                             "{2}".format(node_name, node.name, plug_name))

        # Check the pipeline parameter name is not already used
        if (pipeline_parameter in self.user_traits() and
                                               not allow_existing_plug is True):
            raise ValueError(
                "Parameter '{0}' of node '{1}' cannot be exported to pipeline "
                "parameter '{2}'".format(
                    plug_name, node_name or 'pipeline_node',
                    pipeline_parameter))

        trait = self._clone_trait(source_trait)

        # Set user enabled parameter only if specified
        # Important because this property is automatically set during
        # the nipype interface wrappings
        if is_enabled is not None:
            trait.enabled = bool(is_enabled)

        # Change the trait optional property
        if is_optional is not None:
            trait.optional = bool(is_optional)

        # Now add the parameter to the pipeline
        if not pipeline_parameter in self.user_traits():
            self.add_trait(pipeline_parameter, trait)

        # Propagate the parameter value to the new exported one
        try:
            self.set_parameter(pipeline_parameter,
                               node.get_plug_value(plug_name))
        except traits.TraitError:
            pass

        # Do not forget to link the node with the pipeline node

        if trait.output:
            link_desc = "{0}.{1}->{2}".format(
                node_name, plug_name, pipeline_parameter)
            self.add_link(link_desc,  weak_link)
        else:
            link_desc = "{0}->{1}.{2}".format(
                pipeline_parameter, node_name, plug_name)
            self.add_link(link_desc, weak_link)

    def _set_node_enabled(self, node_name, is_enabled):
        """ Method to enable or disabled a node

        Parameters
        ----------
        node_name: str (mandatory)
            the node name
        is_enabled: bool (mandatory)
            the desired property
        """
        node = self.nodes.get(node_name)
        if node:
            node.enabled = is_enabled

    def propagate_metadata(self, node, param, metadata):
        """
        Set metadata on a node parameter, and propagate these values to the
        connected plugs.

        Typically needed to propagate the "forbid_completion" metadata to avoid
        manuyally set values to be overridden by completion.

        node may be a Node instance or a node name
        """
        if isinstance(node, str):
            node = self.nodes[node]
        todo = [(node, param, True)]
        done = set()
        while todo:
            node, param, force = todo.pop(0)
            done.add((node, param))

            # set metadata on node param trait
            trait = node.get_trait(param)
            modif = False
            for k, v in six.iteritems(metadata):
                if getattr(trait, k) != v:
                    setattr(trait, k, v)
                    modif = True

            if modif or force:
                # get connected plugs
                plug = node.plugs[param]
                for link in list(plug.links_from) + list(plug.links_to):
                    nn, pn, n, p, weak_link = link
                    if (n, pn) not in done:
                        todo.append((n, pn, False))

    def all_nodes(self):
        """ Iterate over all pipeline nodes including sub-pipeline nodes.

        Returns
        -------
        nodes: Generator of Node
            Iterates over all nodes
        """
        for node in six.itervalues(self.nodes):
            yield node
            if (isinstance(node, PipelineNode) and
               node is not self.pipeline_node):
                for sub_node in node.process.all_nodes():
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
            if node is self.pipeline_node:
                # For the top-level pipeline node, all enabled plugs
                # are activated
                for plug_name, plug in six.iteritems(node.plugs):
                    if plug.enabled:
                        if not plug.activated:
                            plug.activated = True
                            plugs_activated.append((plug_name, plug))
            else:
                # Look for input plugs that can be activated
                for plug_name, plug in six.iteritems(node.plugs):
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
                for plug_name, plug in six.iteritems(node.plugs):
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
                [plug for plug in six.itervalues(node.plugs)
                 if plug.output])
            for plug_name, plug in six.iteritems(node.plugs):
                # Check all activated plugs
                try:
                    if plug.activated:
                        # A plug with a default value is always activated
                        if plug.has_default_value:
                            continue
                        output = plug.output
                        if (isinstance(node, PipelineNode) and
                          node is not self.pipeline_node and output):
                            plug_activated = (
                                check_plug_activation(plug, plug.links_to) and
                                check_plug_activation(plug, plug.links_from))
                        else:
                            if node is self.pipeline_node:
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
                                    node is self.pipeline_node):
                                node.activated = False
                                break
                finally:
                    # this must be done even if break or continue has been
                    # encountered
                    if plug.output and plug.activated:
                        deactivate_node = False
            if deactivate_node:
                node.activated = False
                for plug_name, plug in six.iteritems(node.plugs):
                    if plug.activated:
                        plug.activated = False
                        plugs_deactivated.append((plug_name, plug))
        return plugs_deactivated

    def delay_update_nodes_and_plugs_activation(self):
        if self.parent_pipeline is not None:
            # Only the top level pipeline can manage activations
            self.parent_pipeline.delay_update_nodes_and_plugs_activation()
            return
        if self._disable_update_nodes_and_plugs_activation == 0:
            self._must_update_nodes_and_plugs_activation = False
        self._disable_update_nodes_and_plugs_activation += 1

    def restore_update_nodes_and_plugs_activation(self):
        if self.parent_pipeline is not None:
            # Only the top level pipeline can manage activations
            self.parent_pipeline.restore_update_nodes_and_plugs_activation()
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
        if not hasattr(self, 'parent_pipeline'):
            # self is being initialized (the call comes from self.__init__).
            return
        if self.parent_pipeline is not None:
            # Only the top level pipeline can manage activations
            self.parent_pipeline.update_nodes_and_plugs_activation()
            return
        if self._disable_update_nodes_and_plugs_activation:
            self._must_update_nodes_and_plugs_activation = True
            return

        self._disable_update_nodes_and_plugs_activation += 1

        debug = getattr(self, '_debug_activations', None)
        if debug:
            debug = open(debug, 'w')
            print(self.id, file=debug)

        # Remember all links that are inactive (i.e. at least one of the two
        # plugs is inactive) in order to execute a callback if they become
        # active (see at the end of this method)
        inactive_links = []
        for node in self.all_nodes():
            for source_plug_name, source_plug in six.iteritems(node.plugs):
                for nn, pn, n, p, weak_link in source_plug.links_to:
                    if not source_plug.activated or not p.activated:
                        inactive_links.append((node, source_plug_name,
                                               source_plug, n, pn, p))

        # Initialization : deactivate all nodes and their plugs
        for node in self.all_nodes():
            node.activated = False
            for plug_name, plug in six.iteritems(node.plugs):
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
                        for plug_name, plug in six.iteritems(node.plugs):
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

        # Denis 2020/01/03: I don't understand the reason for hiding
        # parameters of inactive plugs: they still get a value (default or
        # forced). So I comment the following out until we make it clear why
        # this was done this way.
        #
        ## Update processes to hide or show their traits according to the
        ## corresponding plug activation
        #for node in self.all_nodes():
            #if isinstance(node, ProcessNode):
                #traits_changed = False
                #for plug_name, plug in six.iteritems(node.plugs):
                    #trait = node.process.trait(plug_name)
                    #if plug.activated:
                        #if getattr(trait, "hidden", False):
                            #trait.hidden = False
                            #traits_changed = True
                    #else:
                        #if not getattr(trait, "hidden", False):
                            #trait.hidden = True
                            #traits_changed = True
                #if traits_changed:
                    #node.process.user_traits_changed = True

        # Execute a callback for all links that have become active.
        for node, source_plug_name, source_plug, n, pn, p in inactive_links:
            if (source_plug.activated and p.activated):
                value = node.get_plug_value(source_plug_name)
                node._callbacks[(source_plug_name, n, pn)](value)

        # Refresh views relying on plugs and nodes selection
        for node in self.all_nodes():
            if isinstance(node, PipelineNode):
                node.process.selection_changed = True

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
                trait = process.trait(plug_name)
                output = trait.output
                if output:
                    if isinstance(trait.trait_type, (File, Directory)) \
                            and trait.input_filename is not False:
                        output = False
                    elif isinstance(trait.trait_type, List) \
                            and isinstance(trait.inner_traits[0],
                                          (File, Directory)) \
                            and trait.input_filename is not False:
                        output = False

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
                    if isinstance(dest_node, ProcessNode):
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
                        for switch_plug in six.itervalues(dest_node.plugs):
                            insert(pipeline, node_name, node, switch_plug,
                                   dependencies, plug_name, links, output)

        # Create a graph and a list of graph node edges
        graph = Graph()
        dependencies = set()
        links = {}

        if remove_disabled_steps:
            steps = getattr(self, 'pipeline_steps', Controller())
            disabled_nodes = set()
            for step, trait in six.iteritems(steps.user_traits()):
                if not getattr(steps, step):
                    disabled_nodes.update(
                        [self.nodes[node] for node in trait.nodes])

        # Add activated Process nodes in the graph
        for node_name, node in six.iteritems(self.nodes):

            # Do not consider the pipeline node
            if node_name == "":
                continue

            # Select only active Process nodes
            if (node.activated or not remove_disabled_nodes) \
                    and isinstance(node, ProcessNode) \
                    and (not remove_disabled_steps
                         or node not in disabled_nodes):

                # If a Pipeline is found: the meta graph node parameter
                # contains a sub Graph
                if isinstance(node.process, Pipeline):
                    gnode = GraphNode(
                        node_name, node.process.workflow_graph(False))
                    gnode.meta.pipeline = node.process
                    graph.add_node(gnode)

                # If a Process or an iterative node is found: the meta graph
                # node parameter contains a list with one process node or
                # a dynamic structure that cannot be processed yet.
                else:
                    graph.add_node(GraphNode(node_name, [node]))

                # Add node edges
                for plug_name, plug in six.iteritems(node.plugs):

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

        # Generate the output workflow representation
        self.workflow_repr = "->".join([x[0] for x in ordered_list])
        logger.debug("Workflow: {0}". format(self.workflow_repr))

        # Generate the final workflow by flattenin graphs structures
        workflow_list = []
        walk_workflow(ordered_list, workflow_list)

        return workflow_list

    def _check_temporary_files_for_node(self, node, temp_files):
        """ Check temporary outputs and allocate files for them.

        Temporary files or directories will be appended to the temp_files list,
        and the node parameters will be set to temp file names.

        This internal function is called by the sequential execution,
        _run_process() (also used through __call__()).
        The pipeline state will be restored at the end of execution using
        _free_temporary_files().

        Parameters
        ----------
        node: Node
            node to check temporary outputs on
        temp_files: list
            list of temporary files for the pipeline execution. The list will
            be modified (completed).
        """
        process = getattr(node, 'process', None)
        if process is not None and isinstance(process, NipypeProcess):
            #nipype processes do not use temporaries, they produce output
            # file names
            return

        for plug_name, plug in six.iteritems(node.plugs):
            value = node.get_plug_value(plug_name)
            if not plug.activated or not plug.enabled:
                continue
            trait = node.get_trait(plug_name)
            if not trait.output:
                continue
            if hasattr(trait, 'input_filename') \
                    and trait.input_filename is False:
                continue
            if hasattr(trait, 'inner_traits') \
                    and len(trait.inner_traits) != 0 \
                    and isinstance(trait.inner_traits[0].trait_type,
                                   (traits.File, traits.Directory)):
                if len([x for x in value if x in ('', traits.Undefined)]) == 0:
                    continue
            elif value not in (traits.Undefined, '') \
                    or ((not isinstance(trait.trait_type, traits.File)
                          and not isinstance(trait.trait_type, traits.Directory))
                         or len(plug.links_to) == 0):
                continue
            # check that it is really temporary: not exported
            # to the main pipeline
            if self.pipeline_node in [link[2]
                                      for link in plug.links_to]:
                # it is visible out of the pipeline: not temporary
                continue
            # if we get here, we are a temporary.
            if isinstance(value, list):
                if trait.inner_traits[0].trait_type is traits.Directory:
                    new_value = []
                    tmpdirs = []
                    for i in range(len(value)):
                        if value[i] in ('', traits.Undefined):
                            tmpdir = tempfile.mkdtemp(suffix='capsul_run')
                            new_value.append(tmpdir)
                            tmpdirs.append(tmpdir)
                        else:
                            new_value.append(value[i])
                    temp_files.append((node, plug_name, tmpdirs, value))
                    node.set_plug_value(plug_name, new_value)
                else:
                    new_value = []
                    tmpfiles = []
                    if trait.inner_traits[0].allowed_extensions:
                        suffix = 'capsul' + trait.allowed_extensions[0]
                    else:
                        suffix = 'capsul'
                    for i in range(len(value)):
                        if value[i] in ('', traits.Undefined):
                            tmpfile = tempfile.mkstemp(suffix=suffix)
                            tmpfiles.append(tmpfile[1])
                            os.close(tmpfile[0])
                            new_value.append(tmpfile[1])
                        else:
                            new_value.append(value[i])
                    node.set_plug_value(plug_name, new_value)
                    temp_files.append((node, plug_name, tmpfiles, value))
            else:
                if trait.trait_type is traits.Directory:
                    tmpdir = tempfile.mkdtemp(suffix='capsul_run')
                    temp_files.append((node, plug_name, tmpdir, value))
                    node.set_plug_value(plug_name, tmpdir)
                else:
                    if trait.allowed_extensions:
                        suffix = 'capsul' + trait.allowed_extensions[0]
                    else:
                        suffix = 'capsul'
                    tmpfile = tempfile.mkstemp(suffix=suffix)
                    node.set_plug_value(plug_name, tmpfile[1])
                    os.close(tmpfile[0])
                    temp_files.append((node, plug_name, tmpfile[1], value))

    def _free_temporary_files(self, temp_files):
        """ Delete and reset temp files after the pipeline execution.

        This internal function is called at the end of _run_process()
        (sequential execution)
        """
        #
        for node, plug_name, tmpfiles, value in temp_files:
            node.set_plug_value(plug_name, value)
            if not isinstance(tmpfiles, list):
                tmpfiles = [tmpfiles]
            for tmpfile in tmpfiles:
                if os.path.isdir(tmpfile):
                    try:
                        shutil.rmtree(tmpfile)
                    except OSError:
                        pass
                else:
                    try:
                        os.unlink(tmpfile)
                    except OSError:
                        pass
                # handle additional files (.hdr, .minf...)
                # TODO
                if os.path.exists(tmpfile + '.minf'):
                    try:
                        os.unlink(tmpfile + '.minf')
                    except OSError:
                        pass

    def _run_process(self):
        '''
        Pipeline execution is managed by StudyConfig class.
        This method must not be called.
        '''
        raise NotImplementedError('Pipeline execution is managed by '
            'StudyConfig class. This method must not be called.')

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
                 for node_name, node in six.iteritems(self.nodes)
                 if node_name != '' and node.enabled and node.activated]
        while nodes:
            node_name, node = nodes.pop(0)
            if hasattr(node, 'process'):
                process = node.process
                if isinstance(process, Pipeline):
                    nodes += [(cnode_name, cnode)
                        for cnode_name, cnode in six.iteritems(process.nodes)
                        if cnode_name != '' and cnode.enabled
                        and cnode.activated]
            else:
                process = node
            # check output plugs; input ones don't work with generated
            # temporary files (unless they are connected with an output one,
            # which will do the job)
            for plug_name, plug in six.iteritems(node.plugs):
                if not plug.enabled or not plug.output or \
                        (not plug.activated and plug.optional):
                    continue
                parameter = process.trait(plug_name)
                if hasattr(parameter, 'inner_traits') \
                        and len(parameter.inner_traits) != 0:
                    # list trait
                    t = parameter.inner_traits[0]
                    if not isinstance(t.trait_type, (File, Directory)):
                        continue
                elif not isinstance(parameter.trait_type, (File, Directory)) \
                        or (parameter.output
                            and parameter.input_filename is False):
                    # a file with its filename as an output is OK
                    continue
                value = getattr(process, plug_name)
                if isinstance(value, list):
                    if len(value) == 0 \
                            or len([item for item in value
                                    if item in ('', traits.Undefined)]) == 0:
                        continue # non-empty list or all values non-empty
                    # here we have null values
                elif value != '' and value is not traits.Undefined:
                    continue # non-null value: not an empty parameter.
                optional = bool(parameter.optional)
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
                        if hasattr(link[2], 'process'):
                            lproc = link[2].process
                            ltrait = lproc.trait(link[1])
                            if ltrait.output \
                                    and ltrait.input_filename is False:
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
            for param_name, param in six.iteritems(self.user_traits())
            if param_name not in ('nodes_activation', 'selection_changed')])
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
                for plug in six.itervalues(node.plugs)])
            enabled_links_count += sum(
                [len([pend for pend in plug.links_to
                        if pend[3].enabled and pend[3].activated])
                    + len([pend for pend in plug.links_from
                        if pend[3].enabled and pend[3].activated])
                    for plug in six.itervalues(node.plugs)
                    if plug.enabled and plug.activated])
            if hasattr(node, 'nodes'):
                sub_nodes = [sub_node
                    for sub_node in node.nodes.values()
                    if sub_node not in nodeset and sub_node not in nodes]
                nodes += sub_nodes
            elif hasattr(node, 'process'):
                if node.process in procs:
                    continue
                procs.add(node.process)
                if node.enabled and node.activated:
                    enabled_procs_count += 1
                params_count += len([param
                    for param_name, param
                    in six.iteritems(node.process.user_traits())
                    if param_name not in (
                        'nodes_activation', 'selection_changed')])
                if hasattr(node.process, 'nodes'):
                    sub_nodes = [sub_node
                        for sub_node in node.process.nodes.values()
                        if sub_node not in nodeset and sub_node not in nodes]
                    nodes += sub_nodes
            elif hasattr(node, 'user_traits'):
                params_count += len([param
                    for param_name, param in six.iteritems(node.user_traits())
                    if param_name not in (
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
            for plug_name, plug in six.iteritems(node.plugs):
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
            for ref_key, ref_value in six.iteritems(ref_dict):
                if ref_key not in other_dict:
                    yield '%s = %s is missing' % (ref_key, repr(ref_value))
                else:
                    other_value = other_dict.pop(ref_key)
                    if ref_value != other_value:
                        yield '%s = %s differs from %s' % (ref_key,
                                                           repr(ref_value),
                                                           repr(other_value))
            for other_key, other_value in six.iteritems(other_dict):
                yield '%s=%s is new' % (other_key, repr(other_value))

        pipeline_state = deepcopy(pipeline_state)
        for node in self.all_nodes():
            node_name = node.full_name
            node_dict = pipeline_state.pop(node_name, None)
            if node_dict is None:
                result.append('node "%s" is missing' % node_name)
            else:
                plugs_list = OrderedDict(node_dict.pop('plugs'))
                result.extend('in node "%s": %s' % (node_name, i) for i in
                              compare_dict(dict(name=node.name,
                                                enabled=node.enabled,
                                                activated=node.activated),
                                           node_dict))
                ref_plug_names = list(node.plugs)
                other_plug_names = list(plugs_list.keys())
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
                for plug_name, plug in six.iteritems(node.plugs):
                    plug_dict = plugs_list[plug_name]
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
                    for link_name, weak_link in six.iteritems(links_to_dict):
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
                    for link_name, weak_link in six.iteritems(links_from_dict):
                        result.append('in plug "%s:%s": %slink from %s is new'
                                      % (node_name,plug_name,(' weak' if
                                          weak_link else ''),link_name))

        for node_name in pipeline_state:
            result.append('node "%s" is new' % node_name)
        return result

    def install_links_debug_handler(self, log_file=None, handler=None,
                                    prefix=''):
        """ Set callbacks when traits value change, and follow plugs links to
        debug links propagation and problems in it.

        Parameters
        ----------
        log_file: str (optional)
            file-like object to write links propagation in.
            If none is specified, a temporary file will be created for it.
        handler: function (optional)
            Callback to be processed for debugging. If none is specified, the
            default pipeline debugging function will be used. This default
            handler prints traits changes and links to be processed in the
            log_file.
            The handler function will receive a prefix string, a node,
            and traits parameters, namely the object (process) owning the
            changed value, the trait name and value in this object.
        prefix: str (optional)
            prefix to be prepended to traits names, typically the parent
            pipeline full name

        Returns
        -------
        log_file: the file object where events will be written in
        """

        if log_file is None:
            log_file_s = tempfile.mkstemp()
            class AutodeDelete(object):
                def __init__(self, file_object):
                    self.file_object = file_object
                def __del__(self):
                    try:
                        self.file_object.close()
                    except IOError:
                        pass
                    try:
                        os.unlink(self.file_object.name)
                    except Exception:
                        pass
            os.close(log_file_s[0])
            log_file = open(log_file_s[1], 'w')
            self._log_file_del = AutodeDelete(log_file)

        self._link_debugger_file = log_file
        if prefix != '' and not prefix.endswith('.'):
            prefix = prefix + '.'
        # install handler on nodes
        for node_name, node in six.iteritems(self.nodes):
            node_prefix = prefix + node_name
            if node_prefix != '' and not node_prefix.endswith('.'):
                node_prefix += '.'
            if handler is None:
                custom_handler = node._value_callback_with_logging
            else:
                custom_handler = handler
            sub_process = None
            sub_pipeline = False
            if hasattr(node, 'process'):
                sub_process = node.process
            if hasattr(sub_process, 'nodes') and sub_process is not self:
                sub_pipeline = sub_process
            if sub_pipeline:
                sub_pipeline.install_links_debug_handler(
                    log_file=log_file,
                    handler=handler,
                    prefix=node_prefix)
            else:
                # replace all callbacks
                callbacks = list(node._callbacks.items())
                for element, callback in callbacks:
                    source_plug_name, dest_node, dest_plug_name = element
                    value_callback = SomaPartial(
                        custom_handler, log_file, node_prefix,
                        source_plug_name,
                        dest_node, dest_plug_name)
                    node.remove_callback_from_plug(source_plug_name, callback)
                    node._callbacks[element] = value_callback
                    node.set_callback_on_plug(source_plug_name, value_callback)

        return log_file

    def uninstall_links_debug_handler(self):
        """ Remove links debugging callbacks set by install_links_debug_handler
        """

        for node_name, node in six.iteritems(self.nodes):
            sub_process = None
            sub_pipeline = False
            if hasattr(node, 'process'):
                sub_process = node.process
            if hasattr(sub_process, 'nodes') and sub_process is not self:
                sub_pipeline = sub_process
            if sub_pipeline:
                sub_pipeline.uninstall_links_debug_handler()
            else:
                for element, callback in list(node._callbacks.items()):
                    source_plug_name, dest_node, dest_plug_name = element
                    value_callback = SomaPartial(
                        node._value_callback, source_plug_name,
                        dest_node, dest_plug_name)
                    node.remove_callback_from_plug(source_plug_name, callback)
                    node._callbacks[element] = value_callback
                    node.set_callback_on_plug(source_plug_name, value_callback)

        if hasattr(self, '_link_debugger_file'):
            del self._link_debugger_file
        if hasattr(self, '_log_file_del'):
            del self._log_file_del

    def define_pipeline_steps(self, steps):
        '''Define steps in the pipeline.
        Steps are pipeline portions that form groups, and which can be enabled
        or disabled on a runtime basis (when building workflows).

        Once steps are defined, their activation may be accessed through the
        "step" trait, which has one boolean property for each step:

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
        for step_name, nodes in six.iteritems(steps):
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
        if 'pipeline_steps' not in self.user_traits():
            super(Pipeline, self).add_trait(
                'pipeline_steps',
                ControllerTrait(Controller(), desc=
                    'Steps are groups of pipeline nodes, which may be '
                    'disabled at runtime. They are normally defined in a '
                    'logical order regarding the workflow streams. They are '
                    'different from sub-pipelines in that steps are purely '
                    'virtual groups, they do not have parameters. To activate '
                    'or diasable a step, just do:\n'
                    'pipeline.steps.my_step = False\n'
                    '\n'
                    'To get the nodes list in a step:\n'
                    'pipeline.get_step_nodes("my_step")'))
            self.trait('pipeline_steps').expanded = False
            self.pipeline_steps = Controller()
        self.pipeline_steps.add_trait(step_name, Bool(nodes=nodes))
        trait = self.pipeline_steps.trait(step_name)
        setattr(self.pipeline_steps, step_name, enabled)

    def remove_pipeline_step(self, step_name):
        '''Remove the given step
        '''
        if 'pipeline_steps' in self.user_traits():
            self.pipeline_steps.remove_trait(step_name)

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
        for step, trait in six.iteritems(steps.user_traits()):
            if not getattr(steps, step, True):
                # disabled step
                nodes = trait.nodes
                disabled_nodes.extend([self.nodes[node] for node in nodes])
        return disabled_nodes

    def get_pipeline_step_nodes(self, step_name):
        '''Get the nodes in the given pipeline step
        '''
        return self.pipeline_steps.trait(step_name).nodes

    def enable_all_pipeline_steps(self):
        '''Set all defined steps (using add_step() or define_steps()) to be
        enabled. Useful to reset the pipeline state after it has been changed.
        '''
        steps = getattr(self, 'pipeline_steps', Controller())
        for step, trait in six.iteritems(steps.user_traits()):
            setattr(steps, step, True)

    def _change_processes_selection(self, selection_name, selection_group):
        self.delay_update_nodes_and_plugs_activation()
        for group, processes in \
                six.iteritems(self.processes_selection[selection_name]):
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
        self.add_trait(selection_parameter, Enum(*selection_groups))
        self.nodes[''].plugs[selection_parameter].has_default_value = True
        self.user_traits_changed = True
        self.processes_selection = getattr(self, 'processes_selection', {})
        self.processes_selection[selection_parameter] = selection_groups
        self.on_trait_change(self._change_processes_selection,
                             selection_parameter)
        self._change_processes_selection(selection_parameter,
                                         getattr(self, selection_parameter))
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

    def set_study_config(self, study_config):
        ''' Set a StudyConfig for the process.
        Note that it can only be done once: once a non-null StudyConfig has
        been assigned to the process, it should not change.
        '''
        super(Pipeline, self).set_study_config(study_config)
        for node_name, node in six.iteritems(self.nodes):
            if node_name != "":
                node.set_study_config(study_config)

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
        for step, trait in six.iteritems(steps.user_traits()):
            nodes = trait.nodes
            steps_priority[step] = p
            p += 1
            for node in nodes:
                inv_steps[node] = step

        if not self.trait('visible_groups'):
            # add a trait without a plug
            Controller.add_trait(self, 'visible_groups', Set())
        plugs = self.pipeline_node.plugs
        for param, trait in six.iteritems(self.user_traits()):
            plug = plugs.get(param)
            if not plug:
                continue
            if trait.output:
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
                trait.groups = groups

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
        for key, node in six.iteritems(self.nodes):
            if node is self.pipeline_node:
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
            for parameter, plug in six.iteritems(node.plugs):
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
                for step, trait in six.iteritems(steps.user_traits()):
                    if old_node_name in trait.nodes:
                        trait.nodes = [n if n != old_node_name
                                          else new_node_name
                                       for n in trait.nodes]

            # nodes positions and dimensions
            if old_node_name in getattr(self, 'node_position', {}):
                self.node_position[new_node_name] \
                    = self.node_position[old_node_name]
                del self.node_position[old_node_name]
            if old_node_name in getattr(self, 'node_dimension', {}):
                self.node_dimension[new_node_name] \
                    = self.node_dimension[old_node_name]
                del self.node_dimension[old_node_name]
