from datetime import datetime
from functools import partial
from pathlib import Path
from pprint import pformat

from soma.qt_gui.qt_backend import Qt, loadUi, QtGui

execution_widget_ui = Path(__file__).parent / 'execution_widget.ui'

def execution_widget(database, execution_id):
    global execution_widget_ui
    widget = loadUi(execution_widget_ui)
    update_execution_widget(widget, database, execution_id)
    update_callback = partial(update_execution_widget, widget, database, execution_id)
    job_callback = partial(show_job, widget=widget, database=database)
    widget._keep_ref= (update_callback, job_callback)
    widget.update.clicked.connect(update_callback)
    widget.jobs.currentItemChanged.connect(job_callback)
    return widget

def update_execution_widget(widget, database, execution_id):
    report = database.execution_report(execution_id)
    widget.date.setText(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    status = report['status']
    if status == 'running':
        status = '🏃'
    elif report['error']:
        status = '❌'
    else:
        status = '✅'
    title = f'{status} {report["label"]}'
    widget.setWindowTitle(title)
    widget.title.setText(title)
    widget.waiting.setText(str(len(report['waiting'])))
    widget.ready.setText(str(len(report['ready'])))
    widget.ongoing.setText(str(len(report['ongoing'])))
    widget.done.setText(str(len(report['done'])))
    widget.failed.setText(str(len(report['failed'])))
    text = ('<html><body>'
        f'<b>status</b>: {report["status"]}<br>'
        f'<b>start time</b>: {report["start_time"]}<br>'
        f'<b>end time</b>: {report["end_time"]}<br>'
        f'<b>execution_id</b>: {report["execution_id"]}<br>'
        'execution context:<pre>\n'
        f'{pformat(report["execution_context"].asdict(), indent=4)}\n<pre>')
    if report['error']:
        text += ('<p style="color: red">'
            f'ERROR: {report["error"]}')
        if report['error_detail']:
            text += '<hr><pre>\n{report["error_detail"]}\n</pre>'
        text += '</p>'
    text += '</body></html>'
    widget.global_text.setText(text)
    widget.jobs.clear()

    status_map = {
        'ongoing': '🏃',
        'done': '✅',
        'failed': '❌',
    }
    jobs = report['jobs']

    # job_tree = {}
    # for job in jobs:
    #     p = job['parameters_location']


    widget._jobs = {job['uuid']: job for job in jobs}
    now = datetime.now()
    count = 0
    for job in sorted(jobs, key=lambda j: (j.get('start_time') if j.get('start_time') else now)):
            job_uuid = job['uuid']
            process_definition = job.get('process', {}).get('definition')
            status = job['status']

            parameters = report['workflow_parameters']
            if parameters:
                for index in job.get('parameters_location', []):
                    if index.isnumeric():
                        index = int(index)
                    parameters = parameters[index]

            item = Qt.QTreeWidgetItem([status_map.get(status, status), process_definition])
            item.execution_id = execution_id
            item.job_uuid = job_uuid
            widget.jobs.insertTopLevelItem(count, item)
            count += 1

def show_job(item, widget, database):
    if not item:
        text = ''
    else:
        execution_id = item.execution_id
        job_uuid = item.job_uuid
        job = widget._jobs[job_uuid]
        text = ('<html><body>'
            f'<b>job_uuid</b>: {job["uuid"]}<br>'
            f'<b>process</b>: {job.get("process", {}).get("definition")}<br>'
            f'<b>pipeline node</b>: {".".join(i for i in job.get("parameters_location", "") if i != "nodes")}<br>'
            f'<b>return code</b>: {job.get("returncode")}<br>'
            f'<b>start time</b>: {job.get("start_time")}<br>'
            f'<b>end time</b>: {job.get("end_time")}<br>'
            f'<b>wait for</b>: {job.get("wait_for", [])}<br>'
            f'<b>waited by</b>: {job.get("waited_by", [])}<br>'
        )
        parameters = database.workflow_parameters(execution_id)
        if parameters:
            for index in job.get('parameters_location', []):
                if index.isnumeric():
                    index = int(index)
                parameters = parameters[index]
        if parameters:
            text += f'parameters:<pre>{pformat(parameters.no_proxy(), indent=4)}</pre>'
        else:
            text += 'parameters: none<br>'
        stdout = job.get('stdout')
        stderr = job.get('stderr')
        if stdout:
            text += f'<br><pre>{stdout}</pre>'
        if stderr:
            text += f'<br><pre style="color: red">{stderr}</pre>'
    widget.job.setText(text)
