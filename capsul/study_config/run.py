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
import operator
import logging
import time
import tempfile
import copy
import json
import multiprocessing

# CAPSUL import
import capsul
from capsul.study_config.memory import Memory
from capsul.study_config.memory import get_process_signature
from capsul.process import IProcess
from .utils import split_name
from .memory import CapsulResultEncoder

# TRAIT import
from traits.api import Undefined


# Define the logger for this file
multiprocessing.log_to_stderr(logging.CRITICAL)
logger = logging.getLogger(__file__)

# Define scheduler constant messages
FLAG_ALL_DONE = b"WORK_FINISHED"
FLAG_WORKER_FINISHED_PROCESSING = b"WORKER_FINISHED_PROCESSING"


def run_process(output_dir, process_instance, cachedir=None,
                generate_logging=False, verbose=1, **kwargs):
    """ Execute a capsul process in a specific directory.

    Parameters
    ----------
    output_dir: str (mandatory)
        the folder where the process will write results.
    process_instance: Process (madatory)
        the capsul process we want to execute.
    cachedir: str (optional, default None)
        save in the cache the current process execution.
        If None, no caching is done.
    generate_logging: bool (optional, default False)
        if True save the log stored in the process after its execution.
    verbose: int
        if different from zero, print console messages.

    Returns
    -------
    returncode: ProcessResult
        contains all execution information.
    output_log_file: str
        the path to the process execution log file.
    """
    # Guarantee that the output directory exists
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    # Update the output directory folder if necessary
    if output_dir is Undefined:
        output_dir = os.getcwd()

    # Set the current directory directory if necessary
    if hasattr(process_instance, "_nipype_interface"):
        if "spm" in process_instance._nipype_interface_name:
            process_instance._nipype_interface.mlab.inputs.prescript += [
                "cd('{0}');".format(output_dir)]

    # Update the instance output directory trait before execution
    if "output_directory" in process_instance.user_traits():
        process_instance.output_directory = output_dir

    # Setup the process log file
    output_log_file = None
    if generate_logging:
        output_log_file = os.path.join(
            os.path.basename(output_dir),
            os.path.dirname(output_dir) + ".json")
        process_instance.log_file = output_log_file

    # Create a memory object
    mem = Memory(cachedir)
    proxy_instance = mem.cache(process_instance, verbose=verbose)

    # Execute the proxy process
    returncode = proxy_instance(**kwargs)

    # Save the process log
    if generate_logging:
        process_instance.save_log(returncode)

    return returncode, output_log_file


def scheduler(pbox, cpus=1, outputdir=None, cachedir=None, log_file=None,
              verbose=1):
    """ Execute a pbox using a schedule.

    Use a FIFO strategy to deal with available nodes and resources.
    The INFO or INFO and DEBUG logging message can be displayed in the console
    while the INFO and DEBUG logging message are redirected in a file if the
    'log_file' parameter is specified.

    Parameters
    ----------
    pbox: Pipeline (mandatory)
        a pipeline to execute with the scheduler.
    cpus: int (optional, default 1)
        the number of cpus to use.
    outputdir: str (optional, default None)
        the folder where the pipeline will write results.
    cachedir: string (optional, default None)
        the directory in which the smart-caching will work. If None, no cache
        is generated.
    log_file: str (optional, default None)
        location where the log messages are redirected: INFO and DEBUG.
    verbose: int (optional, default 1)
        0 - display no log in console,
        1 - display information log in console,
        !=1 - display debug log in console.
    """
    # If someone tried to log something before basicConfig is called,
    # Python creates a default handler that goes to the console and
    # will ignore further basicConfig calls: we need to remove the
    # handlers if there is one.
    while len(logging.root.handlers) > 0:
        logging.root.removeHandler(logging.root.handlers[-1])

    # Remove console and file handlers if already created
    while len(logger.handlers) > 0:
        logger.removeHandler(logger.handlers[-1])

    # Create console handler.
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    if verbose != 0:
        console_handler = logging.StreamHandler()
        if verbose == 1:
            logger.setLevel(logging.INFO)
            console_handler.setLevel(logging.INFO)
        else:
            logger.setLevel(logging.DEBUG)
            console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # Create a file handler if requested
    if log_file is not None:
        file_handler = logging.FileHandler(log_file, mode="a")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.setLevel(logging.DEBUG)
        logger.info("Processing information will be logged in file "
                    "'{0}'.".format(log_file))

    # Information
    start_time = time.time()
    logger.info("Using 'capsul' version '{0}'.".format(capsul.__version__))
    exit_rules = [
        "For exitcode values:",
        "    = 0 - no error was produced.",
        "    > 0 - the process had an error, and exited with that code.",
        "    < 0 - the process was killed with a signal of -1 * exitcode."]
    logger.info("\n".join(exit_rules))
    logger.info("\n{0}\n[Scheduler] Calling {1}...\n{2}".format(
                80 * "_", pbox.id, get_process_signature(
                    pbox, pbox.get_inputs())))

    # Create an execution graph
    exec_graph, _, _ = pbox._create_graph(pbox, filter_inactive=True)

    # Get the machine available cpus
    nb_cpus = multiprocessing.cpu_count() - 1
    nb_cpus = nb_cpus or 1
    if max(cpus, nb_cpus) == cpus:
        cpus = nb_cpus

    # The worker function of a capsul.Pocess, invoked in a
    # multiprocessing.Process
    def bbox_worker(workers_bbox, workers_returncode, outputdir=None,
                    cachedir=None, verbose=1):
        """ The worker.

        Parameters
        ----------
        workers_bbox, workers_returncode: multiprocessing.Queue
            the input and output queues.
        outputdir: str (optional, default None)
            the folder where the pipeline will write results through the
            'output_directory' pipeline control.
        cachedir: string
            the directory in which the smart-caching will work.
        verbose: int
            if different from zero, print console messages.
        """
        import traceback
        from socket import getfqdn
        from capsul.study_config.memory import Memory
        from capsul.process.loader import get_process_instance
        from capsul.study_config.utils import split_name

        mem = Memory(cachedir)
        while True:
            inputs = workers_bbox.get()
            if inputs == FLAG_ALL_DONE:
                workers_returncode.put(FLAG_WORKER_FINISHED_PROCESSING)
                break
            (process_name, box_funcdesc, bbox_inputs, box_copy,
             box_clean) = inputs
            bbox_returncode = {}
            bbox_returncode[process_name] = {}
            bbox_item = bbox_returncode[process_name]
            bbox_item["info"] = {}
            bbox_item["debug"] = {}
            try:
                # Create the box
                bbox = get_process_instance(box_funcdesc)
    
                # Decorate and configure the box
                proxy_bbox = mem.cache(bbox, verbose=verbose)
                for control_name, value in bbox_inputs.items():
                    proxy_bbox.set_parameter(control_name, value)
                if box_copy is not None:
                    bbox.inputs_to_copy = box_copy
                if box_clean is not None:
                    bbox.inputs_to_clean = box_clean

                # Create a valid process working directory if possible
                if outputdir is not None:
                    (identifier, box_name, box_exec_name, box_iter_name,
                     iteration) = split_name(process_name)
                    if box_iter_name is not None:
                        process_outputdir = os.path.join(
                            outputdir, box_exec_name,
                            box_name.replace(box_exec_name, "")[1:])
                    else:
                        process_outputdir = os.path.join(outputdir, box_name)
                    if not os.path.isdir(process_outputdir):
                        os.makedirs(process_outputdir)

                    # Update the instance output directory accordingly if
                    # necessary
                    if "output_directory" in bbox.user_traits():                   
                        bbox.output_directory = process_outputdir

                # Execurte the box
                process_result = proxy_bbox()
                for key in ["start_time", "cwd", "end_time", "hostname",
                            "environ", "versions"]:
                    bbox_item["debug"][key] = process_result.runtime[key]
                bbox_item["info"]["inputs"] = process_result.inputs
                bbox_item["info"]["outputs"] = process_result.outputs
                bbox_item["debug"]["returncode"] = process_result.returncode          
                bbox_item["info"]["exitcode"] = "0"
            except:
                bbox_item["info"]["inputs"] = bbox_inputs
                bbox_item["info"]["outputs"] = {}
                bbox_item["debug"]["hostname"] = getfqdn()
                bbox_item["debug"]["environ"] = copy.deepcopy(os.environ.data)
                bbox_item["info"]["exitcode"] = (
                    "1 - '{0}'".format(traceback.format_exc()))
            workers_returncode.put(bbox_returncode)

    # Create the workers
    workers = []
    workers_bbox = multiprocessing.Queue()
    workers_returncode = multiprocessing.Queue()
    for index in range(cpus):
        process = multiprocessing.Process(
            target=bbox_worker, args=(workers_bbox, workers_returncode,
                                      outputdir, cachedir))
        process.deamon = True
        process.start()
        workers.append(process)

    # Execute the boxes respecting the graph order
    # Use a FIFO strategy to deal with multiple boxes
    iter_map = {}
    box_map = {}
    pbox._update_graph(exec_graph, iter_map, box_map)
    toexec_box_names = available_boxes(exec_graph)
    inexec_box_names = {}
    returncode = {}
    global_counter = 1
    workers_finished = 0
    try:
        # Assert something has to be executed
        if len(toexec_box_names) == 0:
            raise Exception("Nothing to execute.")

        # Loop until all the jobs are finished
        while True:

            # Add nnil boxes to the input queue
            if toexec_box_names is not None:
                for box_name in toexec_box_names:
                    process_name = "{0}-{1}".format(global_counter, box_name)
                    inexec_box_names[box_name] = process_name
                    box = exec_graph.find_node(box_name).meta
                    global_counter += 1
                    box_inputs = {}
                    for control_name in box.traits(output=False):
                        box_inputs[control_name] = box.get_parameter(control_name)
                    box_copy = None
                    box_clean = None
                    if (hasattr(box, "inputs_to_copy") and
                            hasattr(box, "inputs_to_clean")):
                        box_copy = box.inputs_to_copy
                        box_clean = box.inputs_to_clean
                    workers_bbox.put((process_name, box.desc, box_inputs,
                                      box_copy, box_clean))

            # Collect the box returncodes
            wave_returncode = workers_returncode.get()
            if wave_returncode == FLAG_WORKER_FINISHED_PROCESSING:
                workers_finished += 1
                if workers_finished == cpus:
                    break
                continue
            returncode.update(wave_returncode)

            # Update the called box outputs and the graph
            process_name = list(wave_returncode.keys())[0]
            (identifier, box_name, box_exec_name,
             box_iter_name, iteration) = split_name(process_name)
            box = exec_graph.find_node(box_name).meta
            exec_graph.remove_node(box_name)
            for name, value in wave_returncode[process_name]["info"][
                    "outputs"].items():
                box.set_parameter(name, value)

            # Update the iterative mapping, update the graph and IProcess
            # if an iterative job is done
            if box_iter_name in iter_map:
                position = iter_map[box_iter_name].index(box_name)
                iter_map[box_iter_name].pop(position)
                if len(iter_map[box_iter_name]) == 0:
                    ibox = exec_graph.find_node(box_iter_name).meta
                    ibox.update_iteroutputs(box_map.pop(box_iter_name))
                    iter_map.pop(box_iter_name)
                    exec_graph.remove_node(box_iter_name)

            # Information
            for key, value in wave_returncode[process_name]["info"].items():
                logger.info("{0}.{1} = {2}".format(
                    process_name, key, value))
            for key, value in wave_returncode[process_name]["debug"].items():
                logger.debug("{0}.{1} = {2}".format(
                    process_name, key, value))

            # Update nnil boxes list
            if toexec_box_names is not None:
                pbox._update_graph(exec_graph, iter_map, box_map)
                new_toexec_box_names = set(available_boxes(exec_graph))
                inexec_box_names.pop(box_name)
                toexec_box_names = new_toexec_box_names - set(inexec_box_names)

                # Stop iteration: no more job
                if len(exec_graph._nodes) == 0:
                    toexec_box_names = None

                    # Add poison pills to stop the remote workers
                    for index in range(cpus):
                        workers_bbox.put(FLAG_ALL_DONE)
    except:
        # Stop properly all the workers before raising the exception
        for process in workers:
            process.terminate()
            process.join()
        raise

    # Print exit information message
    duration = time.time() - start_time
    msg = "{0:.1f}s, {1:.1f}min".format(duration, duration / 60.)
    logger.info("\n" + max(0, (80 - len(msg))) * '_' + msg)

    # Save processing status to ease the generated data interpretation if the
    # 'outputdir' is not None
    if outputdir is not None:
        exitcodes = {}
        parameters = {}
        for process_name, process_returncode  in returncode.items():
            (identifier, box_name, box_exec_name, box_iter_name,
             iteration) = split_name(process_name)
            parameters[box_name] = {}
            parameters[box_name]["inputs"] = process_returncode["info"]["inputs"]
            parameters[box_name]["outputs"] = process_returncode["info"]["outputs"]
            exitcodes[box_name] = int(process_returncode["info"]["exitcode"].split(
                " - ")[0])
        parameters_file = os.path.join(outputdir, "parameters_status.json")
        with open(parameters_file, "w") as open_file:
            json.dump(parameters, open_file, indent=4, sort_keys=True,
                      cls=CapsulResultEncoder)
        exitcodes_file = os.path.join(outputdir, "exitcodes_status.json")
        with open(exitcodes_file, "w") as open_file:
            json.dump(exitcodes, open_file, indent=4, sort_keys=True)



def available_boxes(graph):
    """ List the boxes that have no incoming link.

    Reject IProcess box.

    Parameters
    ----------
    graph: Graph
        a graph.

    Returns
    -------
    avalible_boxes: list of str
        a list of boxes ready for execution.
    """
    return sorted([node.name for node in graph.available_nodes()
                  if not isinstance(node.meta, IProcess)])
