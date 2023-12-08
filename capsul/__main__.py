import argparse
from datetime import datetime
import json
import re
import sys

from .api import Capsul
from .config.configuration import ApplicationConfiguration
from soma.controller import undefined


def executable_parser(executable):
    parser = argparse.ArgumentParser(
        prog=f"{sys.executable} -m capsul run {executable.definition}",
        description=f"Documentation of process {executable.definition}",
    )
    for field in executable.user_fields():
        help = f"{field.type_str()}"
        parser.add_argument(f"--{field.name}", dest=field.name, nargs="?", help=help)
    return parser


def set_executable_cmd_args(executable, args):
    done = set()
    kwargs = {}
    names = None
    for arg in args:
        m = re.match(r"^\s*([\w_]+)\s*=\s*(.*)$", arg)
        if m:
            name = m.group(1)
            value = m.group(2)
        else:
            if names is None:
                names = [field.name for field in executable.user_fields()]
                index = 0
            while index < len(names):
                if names[index] in done:
                    index += 1
                else:
                    break
            if index < len(names):
                name = names[index]
                value = arg
            else:
                raise ValueError("Too many arguments")
        field = executable.field(name)
        done.add(name)
        if field.type is int:
            if value == "None" or value == "null" or value == "undefined":
                value = undefined
            else:
                value = int(value)
        elif field.type is float:
            if value == "None" or value == "null" or value == "undefined":
                value = undefined
            else:
                value = float(value)
        elif field.type is str or field.is_path():
            if value == "None" or value == "null" or value == "undefined":
                value = undefined
            elif value and value[0] == '"':
                value = json.loads(value)
        else:
            value = json.loads(value)
        if value is None:
            value = undefined
        kwargs[name] = value
    executable.import_dict(kwargs)


parser = argparse.ArgumentParser(
    prog=f"{sys.executable} -m capsul", description="Capsul main command"
)
subparsers = parser.add_subparsers(title="Subcommands", dest="subcommand")

configure_parser = subparsers.add_parser(
    "configure", help="Configure capsul environment"
)

run_parser = subparsers.add_parser("run", help="Execute a Capsul process or pipeline")
run_parser.add_argument(
    "--non-persistent",
    dest="non_persistent",
    action="store_true",
    help="use a non-persistent config: database and server will be disposed at"
    " the end of the execution, accessing logs will not be possible "
    "afterwards",
)
run_parser.add_argument(
    "--print-report",
    action="store_true",
    help="print the execution report before exiting",
)
run_parser.add_argument("executable")

run_parser = subparsers.add_parser(
    "view", help="Display an executable in pipeline developer view"
)
run_parser.add_argument("executable")

help_parser = subparsers.add_parser(
    "help", help="Get help about a command or a process"
)
help_parser.add_argument("command_or_executable")

options, args = parser.parse_known_args()

db_path = None
if options.subcommand == "run" and options.non_persistent:
    db_path = ""
capsul = Capsul(database_path=db_path)

if options.subcommand == "configure":
    # Other commands must be able to work without PyQt installed
    from soma.qt_gui.qt_backend import QtGui, Qt
    from .qt_gui.widgets.settings_editor import SettingsEditor

    app_config = ApplicationConfiguration("global_config")
    QtGui.QApplication.setAttribute(Qt.Qt.AA_ShareOpenGLContexts, True)
    app = QtGui.QApplication(sys.argv)
    w = SettingsEditor(capsul.config)
    w.show()
    app.exec_()
    del w
elif options.subcommand == "run":
    executable = Capsul.executable(options.executable)
    set_executable_cmd_args(executable, args)

    with capsul.engine() as ce:
        # print('engine config:', ce.config.json())
        # print('Workers count', ce.config.start_workers.get('count'))
        ce.assess_ready_to_start(executable)
        execution_id = ce.start(executable)
        try:
            ce.wait(execution_id)
            ce.raise_for_status(execution_id)
            report = ce.execution_report(execution_id)
            if options.print_report:
                ce.print_execution_report(report, file=sys.stdout)

        finally:
            ce.dispose(execution_id)
    now = datetime.now()
    if not options.print_report:
        for job in sorted(
            report["jobs"],
            key=lambda j: (j.get("start_time") if j.get("start_time") else now),
        ):
            stdout = job.get("stdout")
            stderr = job.get("stderr")
            if stdout:
                print(stdout, end="")
            if stderr:
                print(stderr, end="")
elif options.subcommand == "view":
    # Other commands must be able to work without PyQt installed
    from soma.qt_gui.qt_backend import Qt
    from capsul.qt_gui.widgets import PipelineDeveloperView

    # WARNING: QApplication should always be instantiated before aims PluginLoader
    # has been called otherwise another QCoreApplication is instantiated
    # that can conflict with the QApplication created.
    Qt.QApplication.setAttribute(Qt.Qt.AA_ShareOpenGLContexts, True)
    app = Qt.QApplication(sys.argv)

    executable = Capsul.executable(options.executable)
    set_executable_cmd_args(executable, args)
    view = PipelineDeveloperView(
        executable, allow_open_controller=True, show_sub_pipelines=True
    )
    view.show()
    app.exec_()
    del view

elif options.subcommand == "help":
    if options.command_or_executable in ("configure", "run", "help"):
        parser.parse_args([options.command_or_executable, "-h"])
    else:
        executable = Capsul.executable(options.command_or_executable)
        parser = executable_parser(executable)
        parser.parse_args(["-h"])
else:
    parser.parse_args(["-h"])
