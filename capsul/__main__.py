# -*- coding: utf-8 -*-
import argparse
from datetime import datetime
import json
import re
import sys

from .api import Capsul
from .config.configuration import ApplicationConfiguration


def executable_parser(executable):
    parser = argparse.ArgumentParser(
        prog=f'{sys.executable} -m capsul run {executable.definition}',
        description=f'Documentation of process {executable.definition}')
    for field in executable.user_fields():
        help = f'{field.type_str()}'
        parser.add_argument(
            f'--{field.name}',
            dest=field.name,
            nargs='?',
            help=help
        )
    return parser


parser = argparse.ArgumentParser(
    prog=f'{sys.executable} -m capsul',
    description='Capsul main command')
subparsers = parser.add_subparsers(title="Subcommands",
                                   dest="subcommand")

configure_parser = subparsers.add_parser('configure', help='Configure capsul environment')

run_parser = subparsers.add_parser('run', help='Execute a Capsul process or pipeline')
run_parser.add_argument('executable')

help_parser = subparsers.add_parser('help', help='Get help about a command or a process')
help_parser.add_argument('command_or_executable')

print('???')
options, args = parser.parse_known_args()

if options.subcommand == 'configure':
    # Other commands must be able to work without PyQt installed
    from soma.qt_gui.qt_backend import QtGui
    from .qt_gui.widgets.settings_editor import SettingsEditor

    app_config = ApplicationConfiguration('global_config')
    app = QtGui.QApplication(sys.argv)
    capsul = Capsul()
    w = SettingsEditor(capsul.engine())
    w.show()
    app.exec_()
    del w
elif options.subcommand == 'run':
    executable = Capsul.executable(options.executable)
    done = set()
    kwargs = {}
    names = None
    for arg in args:
        m = re.match(r'^\s*([\w_]+)\s*=\s*(.*)$', arg)
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
                raise ValueError('Too many arguments')
        field = executable.field(name)
        done.add(name)
        if field.type is int:
            value = int(value)
        elif field.type is float:
            value = float(value)
        elif field.type is str:
            if value and value[0] == '"':
                value = json.loads(value)
        else:
            value = json.loads(value)
        kwargs[name] = value
    executable.import_dict(kwargs)
    with Capsul().engine() as ce:
        ce.assess_ready_to_start(executable)
        execution_id = ce.start(executable)
        try:
            ce.wait(execution_id)
            ce.raise_for_status(execution_id)
            report = ce.execution_report(execution_id)
        finally:
            ce.dispose(execution_id)
    now = datetime.now()
    for job in sorted(report['jobs'], key=lambda j: (j.get('start_time') if j.get('start_time') else now)):
        stdout = job.get('stdout')
        stderr = job.get('stderr')
        if stdout:
            print(stdout, end='')
        if stderr:
            print(stderr, end='')

            
elif options.subcommand == 'help':
    if options.command_or_executable in ('configure',
                                         'run',
                                         'help'):
        parser.parse_args([options.command_or_executable, '-h'])
    else:
        executable = Capsul.executable(options.command_or_executable)
        parser = executable_parser(executable)
        parser.parse_args(['-h'])
else:
    parser.parse_args(['-h'])
