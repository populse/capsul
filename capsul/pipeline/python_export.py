"""
Pipeline exportation function as a python source code file.

Functions
=========
:func:`save_py_pipeline`
------------------------
"""

import os
import sys

from soma.controller import Controller, undefined


def save_py_pipeline(pipeline, py_file):
    """
    Save a pipeline in an Python source file

    Parameters
    ----------
    pipeline: Pipeline instance
        pipeline to save
    py_file: str
        .py file to save the pipeline in
    """
    # imports are done locally to avoid circular imports
    from capsul.api import Pipeline, Process
    from capsul.application import executable
    from capsul.pipeline.pipeline_nodes import Switch
    from capsul.pipeline.process_iteration import ProcessIteration
    from capsul.process.process import NipypeProcess

    def get_repr_value(value):
        # TODO: handle None/undefined in lists/dicts etc
        if value is undefined:
            repvalue = "undefined"
        elif value is None:
            repvalue = "None"
        elif isinstance(value, Controller):
            repvalue = repr(dict(value.export_to_dict()))
        else:
            repvalue = repr(value)
        return repvalue

    def _write_process(process, pyf, name, enabled, skip_invalid):
        if isinstance(process, NipypeProcess):
            mod = process._nipype_interface.__module__
            classname = process._nipype_interface.__class__.__name__
        else:
            mod = process.__module__
            # if process is a function with XML decorator, we need to
            # retrieve the original function name.
            func = getattr(process, "_function", None)
            if func:
                classname = func.__name__
            else:
                classname = process.__class__.__name__
        procname = ".".join((mod, classname))
        proc_copy = executable(procname)
        make_opt = []
        for field in proc_copy.fields():
            fname = field.name
            if process.field(fname).metadata("optional", False) and not field.metadata(
                "optional", False
            ):
                make_opt.append(fname)
        node_options = ""
        if len(make_opt) != 0:
            node_options += f", make_optional={make_opt!r}"
        if skip_invalid:
            node_options += ", skip_invalid=True"
        print(
            f'        self.add_process("{name}", "{procname}"{node_options})',
            file=pyf,
        )

        # check that sub-nodes enable and plugs optional states are the
        # expected ones
        todo = [(f'self.nodes["{name}"]', process, proc_copy)]
        while todo:
            self_str, snode, cnode = todo.pop(0)
            if not snode.enabled:
                print(f"        {self_str}.enabled = False", file=pyf)

            # if the node is a (sub)pipeline, and this pipeline has additional
            # exported traits compared to the its base module/class instance
            # (proc_copy),  then we must use explicit exports/links inside it
            if isinstance(snode, Pipeline):
                for field in snode.user_fields():
                    param_name = field.name
                    optional = None
                    if cnode.field(param_name) is None:
                        # param added, not in the original process
                        is_input = not field.output
                        if (is_input and snode.plugs[param_name].links_to) or (
                            not is_input and snode.plugs[param_name].links_from
                        ):
                            if is_input:
                                for link in snode.plugs[param_name].links_to:
                                    print(
                                        f'        {self_str}.process.add_link("{param_name}->{link[0]}.{link[1]}", allow_export=True)\n',
                                        file=pyf,
                                    )
                            else:
                                for link in snode.plugs[param_name].links_from:
                                    print(
                                        f'        {self_str}.process.add_link("{link[0]}.{link[1]}->{param_name}", allow_export=True)\n',
                                        file=pyf,
                                    )

            for param_name, plug in snode.plugs.items():
                field = snode.field(param_name)
                cfield = cnode.field(param_name)
                optional = None
                if param_name not in cnode.plugs or field.optional != cfield.optional:
                    optional = field.optional
                if optional is not None:
                    print(
                        f'        {self_str}.field("{param_name}").optional = {optional}\n',
                        file=pyf,
                    )
                    print(
                        f'        {self_str}.plugs["{param_name}"].optional = {optional}\n',
                        file=pyf,
                    )
                if getattr(snode, param_name, undefined) != getattr(
                    cnode, param_name, undefined
                ):
                    # splug = snode.plugs[param_name]
                    # if splug.output and len(splug.links_to) == 0 \
                    # or not splug.output and len(splug.links_from) == 0:
                    ## unconnected with non-default value
                    print(
                        f"        {self_str}.{param_name} =",
                        get_repr_value(getattr(snode, param_name, undefined)),
                        file=pyf,
                    )

            if isinstance(snode, Pipeline):
                sself_str = '%s.nodes["%s"]' % (self_str, "%s")
                for node_name, _ in snode.nodes.items():
                    scnode = cnode.nodes[node_name]

                    if node_name == "":
                        continue
                    todo.append((sself_str % node_name, snode, scnode))

        # if isinstance(process, NipypeProcess):
        ## WARNING: not sure I'm doing the right things for nipype. To be
        ## fixed if needed.
        # for param in process.inputs_to_copy:
        # elem = ET.SubElement(procnode, 'nipype')
        # elem.set('name', param)
        # if param in process.inputs_to_clean:
        # elem.set('copyfile', 'discard')
        # else:
        # elem.set('copyfile', 'true')
        # np_input = getattr(process._nipype_interface.inputs, param)
        # if np_input:
        # use_default = getattr(np_input, 'usedefault', False) # is it that?
        # if use_default:
        # elem.set('use_default', 'true')
        # for param, np_input in \
        # process._nipype_interface.inputs.__dict__.items():
        # use_default = getattr(np_input, 'usedefault', False) # is it that?
        # if use_default and param not in process.inputs_to_copy:
        # elem = ET.SubElement(procnode, 'nipype')
        # elem.set('name', param)
        # elem.set('use_default', 'true')

    def _write_custom_node(node, pyf, name, enabled):
        mod = node.__module__
        classname = node.__class__.__name__
        nodename = ".".join((mod, classname))
        if hasattr(node, "configured_controller"):
            c = node.configured_controller()
            params = dict(
                (p, v) for p, v in c.asdict().items() if v not in (None, undefined)
            )
            print(
                f'        self.add_custom_node("{name}", "{nodename}", {get_repr_value(params)})',
                file=pyf,
            )
        else:
            print(f'        self.add_custom_node("{name}", "{nodename}")', file=pyf)
        # optional plugs
        for plug_name, plug in node.plugs.items():
            if plug.optional:
                print(
                    f'        self.nodes["{name}"].plugs["{plug_name}"].optional = True',
                    file=pyf,
                )
        # non-default: values of unconnected plugs
        for plug_name, plug in node.plugs.items():
            if (
                len(plug.links_from) == 0
                and len(plug.links_to) == 0
                and node.field(plug_name) is not None
                and getattr(node, plug_name, undefined)
                != node.field(plug_name).default_value()
            ):
                value = getattr(node, plug_name, undefined)
                print(
                    f'        self.nodes["{name}"].{plug_name} = {get_repr_value(value)}',
                    file=pyf,
                )

    def _write_iteration(process_iter, pyf, name, enabled):
        process = process_iter.process
        if isinstance(process, NipypeProcess):
            mod = process._nipype_interface.__module__
            classname = process._nipype_interface.__class__.__name__
        else:
            mod = process.__module__
            # if process is a function with XML decorator, we need to
            # retrieve the original function name.
            func = getattr(process, "_function", None)
            if func:
                classname = func.__name__
            else:
                classname = process.__class__.__name__
        procname = ".".join((mod, classname))

        iteration_params = ", ".join(process_iter.iterative_parameters)
        # TODO: optional plugs, non-exported plugs...
        print(
            f'        self.add_iterative_process("{name}", "{procname}", '
            f"iterative_plugs={process_iter.iterative_parameters})",
            file=pyf,
        )

    def _write_switch(switch, pyf, name):
        options = {}
        for option_name in switch._switch_values:
            option_content = {}
            for output in switch._outputs:
                link_from = None
                for node, plug_name in switch.pipeline.get_linked_items(
                    switch, option_name, in_sub_pipelines=False, activated_only=True
                ):
                    link_from = f"{node.name}.{plug_name}"
                    break
                if link_from is not None:
                    option_content[output] = link_from
            options[option_name] = option_content

        inputs_set = set()
        inputs = []
        outputs = []
        optional = []
        for plug_name, plug in switch.plugs.items():
            if plug.output:
                outputs.append(plug_name)
                if plug.optional:
                    optional.append(plug_name)
            else:
                name_parts = plug_name.split("_switch_")
                if len(name_parts) == 2 and name_parts[0] not in inputs_set:
                    inputs_set.add(name_parts[0])
                    inputs.append(name_parts[0])
        optional_p = ""
        if len(optional) != 0:
            optional_p = f", make_optional={optional!r}"

        # print(
        #     f'        self.create_switch({repr(name)}, {repr(options)}, '
        #     f'switch_value={repr(switch.switch)}, export_switch=False)',
        #     file=pyf
        # )
        print(
            f"        self.add_switch({name!r}, {inputs!r}, "
            f"{outputs!r}{optional_p}, export_switch=False)",
            file=pyf,
        )

    def _write_processes(pipeline, pyf):
        print("        # nodes", file=pyf)
        nodes = []
        proc_nodes = []
        # sort nodes, processes first
        for node_name, node in pipeline.nodes.items():
            if node_name == "":
                continue
            if isinstance(node, Process):
                proc_nodes.append((node_name, node))
            else:
                nodes.append((node_name, node))
        for node_name, node in proc_nodes + nodes:
            if isinstance(node, Switch):
                _write_switch(node, pyf, node_name)
            elif isinstance(node, Process) and isinstance(node, ProcessIteration):
                _write_iteration(node, pyf, node_name, node.enabled)
            elif isinstance(node, Process):
                _write_process(
                    node,
                    pyf,
                    node_name,
                    node.enabled,
                    node_name in pipeline._skip_invalid_nodes,
                )
            else:
                # custom node
                _write_custom_node(node, pyf, node_name, node.enabled)

    def _write_processes_selections(pipeline, pyf):
        selection_parameters = []
        if hasattr(pipeline, "processes_selection"):
            print("\n        # processes selection", file=pyf)
            for selector_name, groups in pipeline.processes_selection.items():
                print(
                    f'        self.add_processes_selection("{selector_name}", {groups!r})',
                    file=pyf,
                )
        return selection_parameters

    def _write_export(pipeline, pyf, param_name):
        plug = pipeline.plugs[param_name]
        field = pipeline.field(param_name)
        if plug.output:
            link = list(plug.links_from)[0]
        else:
            link = list(plug.links_to)[0]
        node_name, plug_name = link[:2]
        if param_name == plug_name:
            param_name = ""
        else:
            param_name = f', "{param_name}"'
        weak_link = ""
        if link[-1]:
            weak_link = ", weak_link=True"
        is_optional = f", is_optional={field.optional!r}"
        print(
            f'        self.export_parameter("{node_name}", "{plug_name}"{param_name}{weak_link}{is_optional})',
            file=pyf,
        )
        return node_name, plug_name

    def _write_links(pipeline, pyf):
        exported = set()
        print("\n        # links", file=pyf)
        for node_name, node in pipeline.nodes.items():
            for plug_name, plug in node.plugs.items():
                if (node_name == "" and not plug.output) or (
                    node_name != "" and plug.output
                ):
                    links = plug.links_to
                    for link in links:
                        exported_plug = None
                        if node_name == "":
                            src = plug_name
                            if src not in exported:
                                exported_plug = _write_export(pipeline, pyf, src)
                                exported.add(src)
                        else:
                            src = f"{node_name}.{plug_name}"
                        if link[0] == "":
                            dst = link[1]
                            if dst not in exported:
                                exported_plug = _write_export(pipeline, pyf, dst)
                                exported.add(dst)
                        else:
                            dst = f"{link[0]}.{link[1]}"
                        if not exported_plug or ".".join(exported_plug) not in (
                            src,
                            dst,
                        ):
                            weak_link = ""
                            if link[-1]:
                                weak_link = ", weak_link=True"
                            print(
                                f'        self.add_link("{src}->{dst}"{weak_link})',
                                file=pyf,
                            )

    def _write_param_order(pipeline, pyf):
        user_fields = list(pipeline.user_fields())
        if len(user_fields) == 0:
            return
        print("\n        # parameters order", file=pyf)
        names = [
            f'"{n.name}"'
            for n in user_fields
            if n.name not in ("nodes_activation", "pipeline_steps", "visible_groups")
        ]
        print(
            "\n        self.reorder_fields((%s))" % ",\n            ".join(names),
            file=pyf,
        )

    def _write_steps(pipeline, pyf):
        steps = pipeline.field("pipeline_steps")
        if steps and getattr(pipeline, "pipeline_steps", None):
            print("\n        # pipeline steps", file=pyf)
            for step in pipeline.pipeline_steps.fields():
                step_name = step.name
                enabled = getattr(pipeline.pipeline_steps, step_name, None)
                enabled_str = ""
                if not enabled:
                    enabled_str = ", enabled=false"
                nodes = step.metadata("nodes", set())
                print(
                    f'        self.add_pipeline_step("{step_name}", {nodes!r}{enabled_str})',
                    file=pyf,
                )

    def _write_nodes_positions(pipeline, pyf):
        node_position = getattr(pipeline, "node_position", None)
        if node_position:
            print("\n        # nodes positions", file=pyf)
            print("        self.node_position = {", file=pyf)
            for node_name, pos in pipeline.node_position.items():
                if not isinstance(pos, (list, tuple)):
                    # pos is probably a QPointF
                    pos = (pos.x(), pos.y())
                print(f'            "{node_name}": {pos!r},', file=pyf)
            print("        }", file=pyf)
        if hasattr(pipeline, "scene_scale_factor"):
            print(
                f"        self.scene_scale_factor = {pipeline.scene_scale_factor!r}",
                file=pyf,
            )

    ########### add by Irmage OM #########################
    def _write_nodes_dimensions(pipeline, pyf):
        node_dimension = getattr(pipeline, "node_dimension", None)
        if node_dimension:
            print("\n        # nodes dimensions", file=pyf)
            print("        self.node_dimension = {", file=pyf)
            for node_name, dim in pipeline.node_dimension.items():
                if not isinstance(dim, (list, tuple)):
                    dim = (dim.width(), dim.height())
                print(f'            "{node_name}": {dim!r},', file=pyf)
            print("        }", file=pyf)

    ######################################################

    def _write_doc(pipeline, pyf):
        if hasattr(pipeline, "__doc__"):
            docstr = pipeline.__doc__
            if docstr is None or docstr == Pipeline.__doc__:
                docstr = ""  # don't use the builtin Pipeline help
            else:
                # remove automatically added doc
                splitdoc = docstr.split("\n")
                notepos = [
                    i for i, x in enumerate(splitdoc[:-2]) if x.endswith(".. note::")
                ]
                autodocpos = None
                if notepos:
                    for i in notepos:
                        if (
                            splitdoc[i + 2].find(
                                f"* Type '{pipeline.__class__.__name__}.help()'"
                            )
                            != -1
                        ):
                            autodocpos = i
                if autodocpos is not None:
                    # strip empty trailing lines
                    while autodocpos >= 1 and splitdoc[autodocpos - 1].strip() == "":
                        autodocpos -= 1
                    docstr = "\n".join(splitdoc[:autodocpos]) + "\n"
            if docstr.strip() == "":
                docstr = ""
            if docstr:
                doc = docstr.split("\n")
                docstr = "\n".join([repr(x)[1:-1] for x in doc])
                print(f'    """{docstr}    """', file=pyf)

    def _write_values(pipeline, pyf):
        first = True
        for field in pipeline.fields():
            param_name = field.name
            if param_name not in pipeline.plugs:
                continue
            value = getattr(pipeline, param_name, undefined)
            if value != field.default_value() and value not in (None, "", undefined):
                if isinstance(value, Controller):
                    value_repr = repr(dict(value.asdict()))
                else:
                    value_repr = repr(value)
                try:
                    eval(value_repr)
                except Exception:
                    print(f"warning, value of parameter {param_name} cannot be saved")
                    continue
                if first:
                    first = False
                    print("\n        # default and initial values", file=pyf)
                print(f"        self.{param_name} = {value_repr}", file=pyf)

    class_name = type(pipeline).__name__
    if class_name == "Pipeline":
        # don't accept the base Pipeline class
        class_name = os.path.basename(py_file)
        if "." in class_name:
            class_name = class_name[: class_name.index(".")]
        class_name = class_name[0].upper() + class_name[1:]

    with open(py_file, "w") as pyf:
        print("from capsul.api import Pipeline", file=pyf)
        print("from soma.controller import undefined", file=pyf)
        print(file=pyf)
        print(file=pyf)
        print(f"class {class_name}(Pipeline):", file=pyf)

        _write_doc(pipeline, pyf)

        print(file=pyf)
        print("    def pipeline_definition(self):", file=pyf)

        _write_processes(pipeline, pyf)
        _write_links(pipeline, pyf)
        _write_param_order(pipeline, pyf)
        _write_processes_selections(pipeline, pyf)
        _write_steps(pipeline, pyf)
        _write_values(pipeline, pyf)
        _write_nodes_positions(pipeline, pyf)
        _write_nodes_dimensions(pipeline, pyf)  # add by Irmage OM

        print("\n        self.do_autoexport_nodes_parameters = False", file=pyf)
