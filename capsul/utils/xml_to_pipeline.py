#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import os
import re
import xmltodict
import inspect

# CAPSUL import
from capsul.pipeline import Pipeline
from capsul.pipeline.pipeline_nodes import Switch
from capsul.pipeline.pipeline_nodes import IterativeNode
from capsul.pipeline.pipeline_nodes import ProcessNode
from capsul.pipeline.pipeline_nodes import PipelineNode

# soma-base import
from collections import OrderedDict

# TRAIT import
from traits.api import Undefined


def title_for(xmlpath_description):
    """ Create a title from an underscore-separated file name.

    Parameters
    ----------
    xmlpath_description: str (mandatory)
        the pipeline file description.

    Returns
    -------
    out: str
        the formated pipeline namestring.
    """
    title = os.path.basename(xmlpath_description).split(".")[0]
    return title.replace("_", " ").title().replace(" ", "")


def parse_pipeline_description(xmlpath_description):
    """ Parse the given xml-like pipeline description.

    Parameters
    ----------
    xmlpath_description: str (mandatory)
        a file containing the xml formated string description of the pipeline
        structure.

    Returns
    -------
    pipeline_desc: dict
        the pipeline structure description.
    """
    # Check that a valid description file has been specified
    if not os.path.isfile(xmlpath_description):
        raise ValueError("The input xml description '{0}' is not a valid "
                         "file.".format(xmlpath_description))

    # Parse the pipeline xml-like file
    with open(xmlpath_description) as open_description:
        pipeline_desc = xmltodict.parse(open_description.read())

    return pipeline_desc


class AutoPipeline(Pipeline):
    """ Dummy pipeline class genereated dynamically.
    """
    def pipeline_definition(self):
        """ Define the pipeline from its description.
        """
        # Add all the pipeline standard processes
        if "standard" in self._parameters["pipeline"]["processes"]:
            for process_description in self.to_list(self._parameters[
                    "pipeline"]["processes"]["standard"]):

                # Parse the force description
                optional_parameters = {}
                hidden_parameters = {}
                to_copy_parameters = []
                to_rm_parameters = []
                if "force" in process_description:
                    for force_description in self.to_list(process_description[
                            "force"]):

                        (to_copy_parameter, to_rm_parameter, hidden_parameter,
                         optional_parameter) = self.eval_force_description(
                            force_description)
                        to_copy_parameters.extend(to_copy_parameter)
                        to_rm_parameters.extend(to_rm_parameter)
                        hidden_parameters.update(hidden_parameter)
                        optional_parameters.update(optional_parameter)

                # Add the new process to the pipeline
                node_name = process_description["@name"]
                self.add_process(
                    process_description["@name"],
                    process_description["module"],
                    make_optional=optional_parameters.keys(),
                    inputs_to_copy=to_copy_parameters,
                    inputs_to_clean=to_rm_parameters)

                # Set the view node
                if ("@processing" in process_description and
                        process_description["@processing"] == "False"):
                    self.nodes[node_name].node_type = "view_node"

                # Set the forced values
                process = self.nodes[node_name].process
                for name, value in optional_parameters.iteritems():
                    process.set_parameter(name, value)
                for name, value in hidden_parameters.iteritems():
                    setattr(process._nipype_interface.inputs, name, value)

        # Add all the pipeline iterative processes
        if "iterative" in self._parameters["pipeline"]["processes"]:
            for process_description in self.to_list(self._parameters[
                    "pipeline"]["processes"]["iterative"]):

                # Parse the force description
                optional_parameters = {}
                hidden_parameters = {}
                to_copy_parameters = []
                to_rm_parameters = []
                if "force" in process_description:
                    for force_description in self.to_list(process_description[
                            "force"]):

                        (to_copy_parameter, to_rm_parameter, hidden_parameter,
                         optional_parameter) = self.eval_force_description(
                            force_description)
                        to_copy_parameters.extend(to_copy_parameter)
                        to_rm_parameters.extend(to_rm_parameter)
                        hidden_parameters.update(hidden_parameter)
                        optional_parameters.update(optional_parameter)

                # Get the iterative items
                iterative_parameters = []
                if "iter" in process_description:
                    iterative_parameters = self.to_list(
                        process_description["iter"])

                # Add the new iterative process to the pipeline
                self.add_iterative_process(
                    process_description["@name"],
                    process_description["module"],
                    make_optional=optional_parameters.keys(),
                    iterative_plugs=iterative_parameters,
                    inputs_to_copy=to_copy_parameters,
                    inputs_to_clean=to_rm_parameters,
                    **optional_parameters)

        # Add the pipeline switches
        if "switch" in self._parameters["pipeline"]["processes"]:
            for process_description in self.to_list(self._parameters[
                    "pipeline"]["processes"]["switch"]):
                kwargs = {}
                if "@export_switch" in process_description:
                    value = bool(int(process_description["@export_switch"]))
                    kwargs["export_switch"] = value
                switch_name = process_description["@name"]
                self.add_switch(
                    switch_name,
                    process_description["input"],
                    process_description["output"],
                    **kwargs)
                if "switch_value" in process_description:
                    self.nodes[switch_name].switch = \
                        process_description["switch_value"]

        # Export pipeline input and output parameters
        for tag, sub_tag, plug in [("inputs", "input", "@dest"),
                                   ("outputs", "output", "@src")]:
            if tag in self._parameters["pipeline"]:
                for export_description in self.to_list(self._parameters[
                        "pipeline"][tag][sub_tag]):
                    process, parameter = export_description[plug].split(".")
                    if "@name" in export_description:
                        parameter_name = export_description["@name"]
                    else:
                        parameter_name = parameter
                    if "@optional" in export_description:
                        optional = export_description["@optional"]
                    else:
                        optional = None
                    if "@enabled" in export_description:
                        enabled = export_description["@enabled"]
                    else:
                        enabled = None
                    if "@weak_link" in export_description:
                        weak_link = export_description["@weak_link"]
                    else:
                        weak_link = None
                    self.export_parameter(
                        process, parameter,
                        pipeline_parameter=parameter_name,
                        is_optional=optional,
                        is_enabled=enabled,
                        weak_link=weak_link)

        # Add all the pipeline links
        if "links" in self._parameters["pipeline"]:
            for link_description in self.to_list(self._parameters["pipeline"][
                    "links"]["link"]):
                link = "{0}->{1}".format(
                    link_description["@src"],
                    link_description["@dest"])
                weak_link = False
                if "@weak_link" in link_description:
                    weak_link = bool(int(link_description["@weak_link"]))
                self.add_link(link, weak_link=weak_link)

        # Set the pipeline node positions
        self.node_position = {}
        if "positions" in self._parameters["pipeline"]:
            for node_description in self.to_list(self._parameters[
                    "pipeline"]["positions"]["position"]):
                self.node_position[node_description["@process"]] = (
                    float(node_description["@x"]),
                    float(node_description["@y"]))

        # Set the scene scale
        if "scale" in self._parameters["pipeline"]:
            self.scene_scale_factor = float(
                self._parameters["pipeline"]["scale"]["@factor"])

    def to_list(self, value):
        """ Guarantee to return a list.
        """
        if not isinstance(value, list):
            return [value]
        return value

    def eval_force_description(self, force_description):
        """ Parse the parameter force description.

        Parameters
        ----------
        force_description: dict
            the description of the parameter to force representation.

        Returns
        -------
        to_copy_parameter: list
            a list containing the element if it needs to be copied.
        to_rm_parameter: list
            a list containing the element if it is a temporary parameter.
        hidden_parameter, optional_parameter: dict
            a dictionary containing the parameter default value.
        """
        # Initialize output parameters
        to_copy_parameter = []
        to_rm_parameter = []
        hidden_parameter = {}
        optional_parameter = {}

        # Case force copy
        if "@copyfile" in force_description:
            if force_description["@copyfile"] in [
                    "True", "Temp"]:
                to_copy_parameter = [force_description["@name"]]
            if force_description["@copyfile"] == "Temp":
                to_rm_parameter = [force_description["@name"]]

        # Pipeline parameters to be set
        else:
            # Argument coarse typing
            try:
                value = eval(force_description["@value"])
            except:
                value = force_description["@value"]

            # Case of hidden nipype interface parameters: trick
            # to be removed when all 'usedefault' nipype input
            # spec trait will be set properly
            if ("@usedefault" in force_description and
               force_description["@usedefault"] == "True"):

                hidden_parameter[force_description["@name"]] = value
            # Case of process parameters
            optional_parameter[force_description["@name"]] = value

        return (to_copy_parameter, to_rm_parameter, hidden_parameter,
                optional_parameter)


def class_factory(xmlpath_description, destination_module_globals):
    """ Dynamically create a process instance from a function

    In order to make the class publicly accessible, we assign the result of
    the function to a variable dynamically using globals().

    .. warning::

        The rst external reference synthax has been change since the
        '<target>' is reserved for xml token. Use '[target]' instead.

    Parameters
    ----------
    xmlpath_description: str (mandatory)
        a file containing the xml formated string description of the pipeline
        structure.
    """
    # Create the pipeline class name
    class_name = title_for(xmlpath_description)

    # Get the pipeline prototype
    pipeline_proto = parse_pipeline_description(xmlpath_description)

    # Get the pipeline raw description
    with open(xmlpath_description) as openfile:
        pipeline_desc = openfile.readlines()

    if "@class_name" in pipeline_proto["pipeline"]:
        class_name = str(pipeline_proto["pipeline"]["@class_name"])

    # Get the pipeline docstring
    docstring = pipeline_proto["pipeline"]["docstring"]
    for link in re.findall(r":ref:`.*?\[.*?\]`", docstring, flags=re.DOTALL):
        docstring = docstring.replace(link,
                                      link.replace("[", "<").replace("]", ">"))

    # Define the pipeline class parameters
    class_parameters = {
        "__doc__": docstring,
        "__module__": destination_module_globals["__name__"],
        "_parameters": pipeline_proto,
        "_pipeline_desc": pipeline_desc
    }

    # Get the pipeline instance associated to the prototype
    destination_module_globals[class_name] = (
        type(class_name, (AutoPipeline, ), class_parameters))


def register_pipelines(xmlpipelines, destination_module_globals=None):
    """ Register a number of new processes from function.

    Parameters
    ----------
    xmlpipelines: list of str (mandatory)
        a list of file containing xml formated string description of pipeline
        structures.
    """
    # Get the caller module globals parameter
    if destination_module_globals is None:
        destination_module_globals = inspect.stack()[1][0].f_globals

    # Go through all function and create/register the corresponding process
    for xmlfname in xmlpipelines:
        class_factory(xmlfname, destination_module_globals)


def pipeline_to_xmldict(pipeline):
    """ Generates a XML description of the pipeline structure

    Parameters
    ----------
    pipeline: Pipeline instance (mandatory)

    Returns
    -------
    XML description of the pipeline, in a dictionary. This description is
    compatible with the xmltodict module.
    """
    def _switch_description(node):
        descr = OrderedDict([("@name", node.name), ("@export_switch", "0")])
        inputs = []
        outputs = []
        descr["input"] = inputs
        descr["output"] = outputs
        for plug_name, plug in node.plugs.iteritems():
            if plug.output:
                outputs.append(plug_name)
            else:
                name_parts = plug_name.split("_switch_")
                if len(name_parts) == 2 \
                        and name_parts[0] not in inputs:
                    inputs.append(name_parts[0])
        descr["switch_value"] = node.switch
        return descr

    def _write_processes(pipeline, pipeline_dict):
        proc_dict = pipeline_dict.setdefault("processes", OrderedDict())
        for node_name, node in pipeline.nodes.iteritems():
            if node_name == "":
                continue
            if isinstance(node, Switch):
                switches = proc_dict.setdefault("switch", [])
                switch_descr = _switch_description(node)
                switches.append(switch_descr)
            elif isinstance(node, IterativeNode):
                iternodes = proc_dict.setdefault("iterative", [])
                iterative.append({"@name": node.name})
            else:
                procnodes = proc_dict.setdefault("standard", [])
                proc = node.process
                mod = proc.__module__
                classname = proc.__class__.__name__
                procitem = {"@name": node.name}
                procitem["module"] = "%s.%s" % (mod, classname)
                procnodes.append(procitem)

    def _write_params(pipeline, pipeline_dict):
        exported = set()
        for plug_name, plug in pipeline.pipeline_node.plugs.iteritems():
            param_descr = OrderedDict([("@name", plug_name)])
            if not plug.enabled:
                param_descr["@enabled"] = "0"
            if plug.optional:
                param_descr["@optional"] = "1"
            if plug.output:
                if len(plug.links_from) == 0:
                    # FIXME: maybe don't completely ignore the plug ?
                    continue
                params = pipeline_dict.setdefault(
                    "outputs", OrderedDict()).setdefault("output", [])
                link = ".".join(list(plug.links_from)[0][:2])
                param_descr["@src"] = link
                if link[-1]:
                    param_descr["@weak_link"] = "1"
                exported.add(link)
            else:
                if len(plug.links_to) == 0:
                    # FIXME: maybe don't completely ignore the plug ?
                    continue
                params = pipeline_dict.setdefault(
                    "inputs", OrderedDict()).setdefault("input", [])
                link = ".".join(list(plug.links_to)[0][:2])
                param_descr["@dest"] = link
                exported.add(link)
            params.append(param_descr)
        return exported

    def _write_links(pipeline, pipeline_dict, exported):
        links_list = pipeline_dict.setdefault(
            "links", OrderedDict()).setdefault("link", [])
        for node_name, node in pipeline.nodes.iteritems():
            for plug_name, plug in node.plugs.iteritems():
                if (node_name == "" and not plug.output) \
                        or (node_name != "" and plug.output):
                    links = plug.links_to
                    for link in links:
                        if node_name == "":
                            src = plug_name
                        else:
                            src = "%s.%s" % (node_name, plug_name)
                            if src in exported and link[0] == "":
                                continue  # already done in exportation section
                        if link[0] == "":
                            dst = link[1]
                        else:
                            dst = "%s.%s" % (link[0], link[1])
                            if dst in exported and link[0] == "":
                                continue  # already done in exportation section
                        link_def = OrderedDict([("@src", src), ("@dest", dst)])
                        if link[-1]:
                            link_def["@weak_link"] = "1"
                        links_list.append(link_def)

    def _write_nodes_positions(pipeline, pipeline_dict):
        if hasattr(pipeline, "node_position"):
            positions = pipeline_dict.setdefault(
                "positions", OrderedDict()).setdefault("position", [])
            for node_name, pos in pipeline.node_position.iteritems():
                node_pos = OrderedDict([("@process", node_name),
                                        ("@x", unicode(pos[0])),
                                        ("@y", unicode(pos[1]))])
                positions.append(node_pos)


    pipeline_dict = OrderedDict([("@class_name", pipeline.__class__.__name__)])
    xml_dict = OrderedDict([("pipeline", pipeline_dict)])
    # FIXME: pipeline name ?

    if hasattr(pipeline, "__doc__"):
        pipeline_dict["docstring"] = pipeline.__doc__
    _write_processes(pipeline, pipeline_dict)
    exported = _write_params(pipeline, pipeline_dict)
    _write_links(pipeline, pipeline_dict, exported)
    _write_nodes_positions(pipeline, pipeline_dict)

    if hasattr(pipeline, "scene_scale_factor"):
        pipeline_dict["scale"] = {
            "@factor": unicode(pipeline.scene_scale_factor)}

    return xml_dict


def pipeline_to_xml(pipeline, output=None):
    """ Generates a XML description of the pipeline structure

    Parameters
    ----------
    pipeline: Pipeline instance (mandatory)
    output: file object (optional)
        file to write XML in. If not specified, return the XML as a string, as
        does the xmltodict module.

    Returns
    -------
    if output is specified: None
    if output is not specified: XML description of the pipeline, in a unicode
    string.
    """
    xml_dict = pipeline_to_xmldict(pipeline)
    return xmltodict.unparse(xml_dict, full_document=False, pretty=True,
                             indent="    ", output=output)

