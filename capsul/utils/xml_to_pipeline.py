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
import json
import inspect

# CAPSUL import
from .description_utils import load_xml_description
from .description_utils import title_for
from .description_utils import is_io_control
from capsul.pipeline import Pipeline
from capsul.pipeline.pipeline_nodes import Switch
from capsul.pipeline.pipeline_nodes import ProcessNode
from capsul.pipeline.pipeline_nodes import PipelineNode
from capsul.pipeline.process_iteration import ProcessIteration

# TRAIT import
from traits.api import Enum
from traits.api import Undefined


class AutoPipeline(Pipeline):
    """ Dummy pipeline class genereated dynamically.
    """
    xml_tag = "pipeline"
    box_tag = "units"
    box_names = ["unit", "switch"]
    unit_attributes = ["name", "module", "set", "iterinput", "iteroutput", "qc"]
    unit_set = ["name", "value", "copyfile", "usedefault"]
    unit_iter = ["name"]
    switch_attributes = ["name", "path"]
    switch_path = ["name", "unit"]
    link_tag = "links"
    link_attributes = ["source", "destination"]
    zoom_tag = "zoom"
    zoom_attributes = ["level"]
    position_tag = "positions"
    position_attributes = ["unit", "x", "y"]

    def __init__(self, **kwargs):
        """ Initialize the AutoPipeline class.
        """
        self._switches = {}
        super(AutoPipeline, self).__init__(
            autoexport_nodes_parameters=False, **kwargs)

    def pipeline_definition(self):
        """ Define the pipeline from its description.
        """
        # Add boxes to the pipeline
        if self.box_tag not in self.proto:
            raise Exception(
                "Box defined in '{0}' has no '<{1}>' declared.".format(
                    self._xmlfile, self.box_tag))
        switch_descs = []
        for box_item in self.proto[self.box_tag]:
            for box_type in box_item.keys():

                # Create processing boxes (can be iterative)
                if box_type == self.box_names[0]:
                    for boxdesc in box_item[box_type]:
                        self._add_box(boxdesc)
                # Create switch boxes
                elif box_type == self.box_names[1]:
                    for switchdesc in box_item[box_type]:
                        switch_descs.append(switchdesc)
                # Unrecognize box type
                else:
                    raise ValueError(
                        "Box structure: '{0}' defined in '{1}' is not "
                        "supported. Supported boxes are '{2}'.".format(
                            json.dumps(box_item, indent=2), self._xmlfile,
                            self.box_names))

        # Add switch to the pipeline
        for switchdesc in switch_descs:
            self._add_switch(switchdesc)

        # Add links between boxes
        if self.link_tag not in self.proto:
            raise Exception(
                "Box defined in '{0}' has no '<{1}>' declared.".format(
                    self._xmlfile, self.link_tag))
        for link_item in self.proto[self.link_tag]:
            inner_tag = self.link_tag[:-1]
            for linkdesc in link_item[inner_tag]:
                if is_io_control(linkdesc[self.link_attributes[0]]):
                    linktype = "input"
                elif is_io_control(linkdesc[self.link_attributes[1]]):
                    linktype = "output"
                else:
                    linktype = "link"
                self._add_link(linkdesc, linktype)

        # Set the pipeline node positions
        self.node_position = {}
        if self.position_tag in self.proto:
            inner_tag = self.position_tag[:-1]
            for positiondesc in self.proto[self.position_tag][0][inner_tag]:
                self.node_position[positiondesc[self.position_attributes[0]]] = (
                    float(positiondesc[self.position_attributes[1]]),
                    float(positiondesc[self.position_attributes[2]]))

        # Set the scene scale
        if self.zoom_tag in self.proto:
            self.scene_scale_factor = float(
                self.proto[self.zoom_tag][0][self.zoom_attributes[0]])

    def _add_switch(self, switchdesc):
        """ Add a switch in the pipeline from its description.

        Parameters
        ----------
        switchdesc: dict
            the description of the switch we want to insert in the pipeline.
        """
        # Check switch definition parameters
        switch_attributes = list(switchdesc.keys())
        if not set(switch_attributes).issubset(self.switch_attributes):
            raise ValueError(
                "Switch definition: '{0}' defined in '{1}' is not supported. "
                "Supported switch parameters are '{2}'.".format(
                    json.dumps(switchdesc, indent=2), self._xmlfile,
                    self.switch_attributes))
        for mandatory_parameter in self.switch_attributes[:2]:
            if mandatory_parameter not in switch_attributes:
                raise ValueError(
                    "A '{0}' parameter is required in switch definition: "
                    "'{1}' defined in '{2}'.".format(
                        mandatory_parameter, json.dumps(switchdesc, indent=2),
                        self._xmlfile))

        # Check the name of the switch is not already reserved
        switch_name = switchdesc[self.switch_attributes[0]][0]
        if switch_name in self._switches:
            raise ValueError(
                "The switch name '{0}' defined in '{1}' is "
                "already used.".format(switch_name, self._xmlfile))

        # Create the switch control
        switch_paths = {}
        for pathdesc in switchdesc[self.switch_attributes[1]]:
            path_name = pathdesc[self.switch_path[0]][0]
            path_boxes = [box[self.unit_attributes[0]]
                          for box in pathdesc[self.switch_path[1]]]
            switch_paths[path_name] = path_boxes
        self.switch(switch_name, switch_paths)

    def switch(self, switch_name, switch_paths):
        """ Generate a Switch Node

        Parameters
        ----------
        switch_name: str (mandatory)
            the switch node name.
        switch_paths: dict
            a dict with the switch path description.
        """
        # Get the switch structure
        switch_values = switch_paths.keys()
        switch_boxes = []
        for key, value in switch_paths.items():
            switch_boxes.extend(value)

        # Add a switch enum trait to select the path
        self.add_trait(switch_name, Enum(optional=False, output=False,
                                         *switch_values))
        self._switches[switch_name] = (switch_paths, switch_boxes)

        # Activate the switch
        self._anytrait_changed(switch_name, switch_values[0], switch_values[0])

    def _anytrait_changed(self, name, old, new):
        """ Add an event to the switch trait that enables us to select
        the desired option.

        Parameters
        ----------
        old: str (mandatory)
            the old option
        new: str (mandatory)
            the new option
        """
        if hasattr(self, "_switches") and name in self._switches:

            # Select switch
            switch_paths, switch_boxes = self._switches[name]

            # Disable all the boxes in the switch structure
            for box_name in switch_boxes:
                self.nodes[box_name].enabled = False

            # Activate only the selected path
            for box_name in switch_paths[new]:
                self.nodes[box_name].enabled = True

            # Update the activation
            self.update_nodes_and_plugs_activation()

    def _add_box(self, boxdesc):
        """ Add a box in the pipeline from its description.

        Parameters
        ----------
        boxdesc: dict
            the description of the box we want to insert in the pipeline.
        """
        # Check box definition parameters
        box_attributes = list(boxdesc.keys())
        if not set(box_attributes).issubset(self.unit_attributes):
            raise ValueError(
                "Box definition: '{0}' defined in '{1}' is not supported. "
                "Supported box parameters are '{2}'.".format(
                    json.dumps(boxdesc, indent=2), self._xmlfile,
                    self.unit_attributes))
        for mandatory_parameter in self.unit_attributes[:2]:
            if mandatory_parameter not in box_attributes:
                raise ValueError(
                    "A '{0}' parameter is required in box definition: '{1}' "
                    "defined in '{2}'.".format(
                        mandatory_parameter, json.dumps(boxdesc, indent=2),
                        self._xmlfile))

        # Check the name of the new box is not already reserved
        box_name = boxdesc[self.unit_attributes[0]][0]
        if box_name in self.nodes:
            raise ValueError("The box name '{0}' defined in '{1}' is already "
                             "used.".format(box_name, self._xmlfile))

        # Instanciate the new box
        box_module = boxdesc[self.unit_attributes[1]][0]
        iterinputs = boxdesc.get(self.unit_attributes[3], [])
        iteroutputs = boxdesc.get(self.unit_attributes[4], [])

        # > parse the 'set' description
        optional_parameters = {}
        hidden_parameters = {}
        to_copy_parameters = []
        to_rm_parameters = []
        set_tag = self.unit_attributes[2]
        if set_tag in box_attributes:
            for box_defaults in boxdesc[set_tag]:
                (to_copy_parameter, to_rm_parameter, hidden_parameter,
                 optional_parameter) = self.eval_force_description(
                    box_defaults)
                to_copy_parameters.extend(to_copy_parameter)
                to_rm_parameters.extend(to_rm_parameter)
                hidden_parameters.update(hidden_parameter)
                optional_parameters.update(optional_parameter)

        # > add the new process to the pipeline
        if iterinputs == []:
            self.add_process(
                box_name,
                box_module,
                make_optional=optional_parameters.keys(),
                inputs_to_copy=to_copy_parameters,
                inputs_to_clean=to_rm_parameters)

        # > add the new iterative process to the pipeline
        else:
            self.add_iterative_process(
                box_name,
                box_module,
                make_optional=optional_parameters.keys(),
                iterative_plugs=iterinputs,
                inputs_to_copy=to_copy_parameters,
                inputs_to_clean=to_rm_parameters,
                **optional_parameters)

        # Set the node type
        qc_tag = self.unit_attributes[5]
        if qc_tag in box_attributes and box_attributes[qc_tag] == "True":
            self.nodes[box_name].node_type = "view_node"

        # Set the forced values
        process = self.nodes[box_name].process
        for name, value in optional_parameters.items():
            if value is None:
                value = Undefined
            process.set_parameter(name, value)
        for name, value in hidden_parameters.items():
            if value is None:
                value = Undefined
            setattr(process._nipype_interface.inputs, name, value)

    def _add_link(self, linkdesc, linktype="link"):
        """ Link box parameters.

        A link is always defined from a source control to a destination
        control.

        Parameters
        ----------
        linkdesc: dict
            the description of the link we want to insert in the pipeline.
        linktype: string
            the link type: 'link', 'input' or 'output'.
        """
        # Check the proper lexic has been specified
        link_keys = list(linkdesc.keys())
        issubset = set(link_keys).issubset(self.link_attributes)
        if len(link_keys) != 2 or not issubset:
            raise ValueError(
                "Box attribute definition: '{0}' defined in '{1}' is "
                "not supported. Supported attributes are "
                "'{2}'.".format(
                    json.dumps(list(linkdesc.keys())), self._xmlfile,
                    self.link_attributes))

        # Deal with input/output pipeline link
        # In this case the inner box control is registered as an input/output
        # control of the pipeline
        source = linkdesc[self.link_attributes[0]]
        destination = linkdesc[self.link_attributes[1]]
        linkrep = "{0}->{1}".format(source, destination)
        if linktype == "output":
            box_name, box_pname = source.split(".")
            self.export_parameter(box_name, box_pname,
                                  pipeline_parameter=destination)
        elif linktype == "input":
            box_name, box_pname = destination.split(".")
            if source not in self.user_traits():
                self.export_parameter(box_name, box_pname,
                                      pipeline_parameter=source)
            else:
                self.add_link(linkrep)
        # Deal with inner pipeline link
        elif linktype == "link":
            self.add_link(linkrep)
        else:
            raise ValueError("Unrecognized link type '{0}'.".format(linktype))

    def eval_force_description(self, set_attributes):
        """ Parse the parameter force description.

        Parameters
        ----------
        set_attribute: dict
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
        # Check the proper lexic has been specified
        if not set(set_attributes.keys()).issubset(self.unit_set):
            raise ValueError(
                "Box attribute definition: '{0}' defined in '{1}' is "
                "not supported. Supported attributes are "
                "'{2}'.".format(
                    list(set_attributes.keys()), self._xmlfile,
                    self.unit_set))


        # Initialize output parameters
        to_copy_parameter = []
        to_rm_parameter = []
        hidden_parameter = {}
        optional_parameter = {}
        box_pname = set_attributes[self.unit_set[0]]
        box_pvalue = eval(set_attributes[self.unit_set[1]])

        # Case force copy
        copy_tag = self.unit_attributes[2]
        if copy_tag in set_attributes:
            if set_attribute[copy_tag] in ["True", "Temp"]:
                to_copy_parameter.append(box_pname)
            if set_attribute[copy_tag] == "Temp":
                to_rm_parameter.append(box_pname)

        # Pipeline parameters to be set
        else:
            # Argument coarse typing
            try:
                value = eval(box_pvalue)
            except:
                value = box_pvalue

            # Case of hidden nipype interface parameters: trick
            # to be removed when all 'usedefault' nipype input
            # spec trait will be set properly
            default_tag = self.unit_set[3]
            if (default_tag in set_attributes and
                    set_attributes[default_tag] == "True"):
                hidden_parameter[box_pname] = value
            # Case of process parameters
            optional_parameter[box_pname] = value

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
    basename = os.path.basename(xmlpath_description).split(".")[0]
    class_name = title_for(basename)

    # Get the pipeline prototype
    pipeline_proto = load_xml_description(xmlpath_description)

    # Get the pipeline docstring
    docstring = pipeline_proto["docstring"][0]
    if docstring is None:
        docstring = ""
    for link in re.findall(r":ref:`.*?\[.*?\]`", docstring, flags=re.DOTALL):
        docstring = docstring.replace(link,
                                      link.replace("[", "<").replace("]", ">"))

    # Define the pipeline class parameters
    class_parameters = {
        "__doc__": docstring,
        "__module__": destination_module_globals["__name__"],
        "_xmlfile": xmlpath_description,
        "proto": pipeline_proto
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

