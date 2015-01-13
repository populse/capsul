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
import xmltodict
import inspect

# CAPSUL import
from capsul.pipeline import Pipeline


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
        a file containing the xml formated string describtion of the pipeline
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
                optional_parameters = []
                if "force" in process_description:
                    for force_description in self.to_list(process_description[
                            "force"]):
                        optional_parameters.append(force_description["@name"])
                self.add_process(
                    process_description["@name"],
                    process_description["module"],
                    make_optional=optional_parameters)

        # Add all the pipeline iterative processes
        if "iterative" in self._parameters["pipeline"]["processes"]:
            for process_description in self.to_list(self._parameters[
                    "pipeline"]["processes"]["iterative"]):
                optional_parameters = []
                if "force" in process_description:
                    for force_description in self.to_list(process_description[
                            "force"]):
                        optional_parameters.append(force_description["@name"])
                iterative_parameters = []
                if "iter" in process_description:
                    iterative_parameters = self.to_list(
                        process_description["iter"])            
                self.add_iterative_process(
                    process_description["@name"],
                    process_description["module"],
                    make_optional=optional_parameters,
                    iterative_plugs=iterative_parameters)

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
                    self.export_parameter(
                        process, parameter, pipeline_parameter=parameter_name)

        # Add all the pipeline links
        for link_description in self._parameters["pipeline"]["links"]["link"]:
            link = "{0}->{1}".format(
                link_description["@src"],
                link_description["@dest"])
            self.add_link(link)

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


def class_factory(xmlpath_description, destination_module_globals):
    """ Dynamically create a process instance from a function

    In order to make the class publicly accessible, we assign the result of
    the function to a variable dynamically using globals().

    Parameters
    ----------
    xmlpath_description: str (mandatory)
        a file containing the xml formated string describtion of the pipeline
        structure.
    """
    # Create the pipeline class name
    class_name = title_for(xmlpath_description)

    # Get the pipeline prototype
    pipeline_proto = parse_pipeline_description(xmlpath_description)

    # Get the pipeline docstring
    docstring = pipeline_proto["pipeline"]["docstring"]

    # Define the pipeline class parameters
    class_parameters = {
        "__doc__": docstring,
        "__module__": destination_module_globals["__name__"],
        "_parameters": pipeline_proto
    }

    # Get the pipeline instance associated to the prototype
    destination_module_globals[class_name] = (
        type(class_name, (AutoPipeline, ), class_parameters))


def register_pipelines(xmlpipelines, destination_module_globals=None):
    """ Register a number of new processes from function.

    Parameters
    ----------
    xmlpipelines: list of str (mandatory)
        a list of file containing xml formated string describtion of pipeline
        structures.
    """
    # Get the caller module globals parameter
    if destination_module_globals is None:
        destination_module_globals = inspect.stack()[1][0].f_globals

    # Go through all function and create/register the corresponding process
    for xmlfname in xmlpipelines:
        class_factory(xmlfname, destination_module_globals)