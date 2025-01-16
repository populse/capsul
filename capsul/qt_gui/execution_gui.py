from datetime import datetime
from functools import partial
from pathlib import Path
from pprint import pformat

from soma.qt_gui.qt_backend import Qt, QtGui, loadUi

execution_widget_ui = Path(__file__).parent / "execution_widget.ui"


def execution_widget(database, engine_id, execution_id):
    global execution_widget_ui
    widget = loadUi(execution_widget_ui)
    widget.current_job = None
    update_execution_widget(widget, database, engine_id, execution_id)
    update_callback = partial(
        update_execution_widget, widget, database, engine_id, execution_id
    )
    job_callback = partial(show_job, widget=widget, database=database)
    widget._keep_ref = (update_callback, job_callback)
    widget.update.clicked.connect(update_callback)
    widget.jobs.currentItemChanged.connect(job_callback)
    return widget


def update_execution_widget(widget, database, engine_id, execution_id):
    report = database.execution_report(engine_id, execution_id)
    widget.date.setText(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    current_job = widget.current_job
    status = report["status"]
    if status == "running":
        status = "🏃"
    elif report["error"]:
        status = "❌"
    else:
        status = "✅"
    title = f"{status} {report['label']}"
    widget.setWindowTitle(title)
    widget.title.setText(title)
    widget.waiting.setText(str(len(report["waiting"])))
    widget.ready.setText(str(len(report["ready"])))
    widget.ongoing.setText(str(len(report["ongoing"])))
    widget.done.setText(str(len(report["done"])))
    widget.failed.setText(str(len(report["failed"])))
    text = (
        "<html><body>"
        f"<b>status</b>: {report['status']}<br>"
        f"<b>start time</b>: {report['start_time']}<br>"
        f"<b>end time</b>: {report['end_time']}<br>"
        f"<b>engine_id</b>: {report['engine_id']}<br>"
        f"<b>execution_id</b>: {report['execution_id']}<br>"
        "execution context:<pre>\n"
        f"{pformat(report['execution_context'].asdict(), indent=4)}\n<pre>"
    )
    if report["error"]:
        text += f'<p style="color: red">ERROR: {report["error"]}'
        if report["error_detail"]:
            text += '<hr><pre>\n{report["error_detail"]}\n</pre>'
        text += "</p>"
    text += "</body></html>"
    widget.global_text.setText(text)
    widget.jobs.clear()

    status_map = {
        "ongoing": "🏃",
        "done": "✅",
        "failed": "❌",
        "ready": "⏳",
        "waiting": "⏳",
    }
    jobs = report["jobs"]

    widget._jobs = {job["uuid"]: job for job in jobs}

    items = {}
    count = 0
    for job in jobs:
        path = []
        parameters = job["parameters_location"]
        i = 0
        while i < len(parameters):
            if parameters[i] in ("nodes", "_iterations"):
                path.append(parameters[i + 1])
                i += 2
            else:
                raise ValueError(f"Cannot parse parameters_location: {parameters[i]}")
        path = tuple(path)
        pp = None
        parent_item = None
        for i in range(1, len(path)):
            p = path[:i]
            parent_item = items.get(p)
            if parent_item is None:
                parent_item = Qt.QTreeWidgetItem(pp, ["", p[-1]])
                parent_item.engine_id = None
                parent_item.execution_id = None
                parent_item.job_uuid = None
                if pp is None:
                    widget.jobs.insertTopLevelItem(count, parent_item)
                    count += 1
                items[p] = parent_item
            pp = parent_item
        job_uuid = job["uuid"]
        process_definition = job.get("process", {}).get("definition")
        status = job["status"]
        status = status_map.get(status, status)
        item = items.get(path)
        if item:
            item.setText(0, status)
            item.setText(1, process_definition)
        else:
            item = Qt.QTreeWidgetItem(
                parent_item, [status_map.get(status, status), process_definition]
            )
            items[path] = item
        item.engine_id = engine_id
        item.execution_id = execution_id
        item.job_uuid = job_uuid
        if parent_item is None:
            widget.jobs.insertTopLevelItem(count, item)
            count += 1
        else:
            if status == "❌":
                parent_item.setText(0, "❌")
            elif status == "🏃":
                if parent_item.text(0) != "❌":
                    parent_item.setText(0, "🏃")
            elif status == "⏳":
                if parent_item.text(0) not in ("❌", "🏃"):
                    parent_item.setText(0, "⏳")
            else:
                if parent_item.text(0) == "":
                    parent_item.setText(0, "✅")

        if job_uuid == current_job:
            widget.jobs.setCurrentItem(item)

    # now = datetime.now()
    # count = 0
    # for job in sorted(jobs, key=lambda j: (j.get('start_time') if j.get('start_time') else now)):
    #         job_uuid = job['uuid']
    #         process_definition = job.get('process', {}).get('definition')
    #         status = job['status']

    #         parameters = report['workflow_parameters']
    #         if parameters:
    #             for index in job.get('parameters_location', []):
    #                 if index.isnumeric():
    #                     index = int(index)
    #                 parameters = parameters[index]

    #         item = Qt.QTreeWidgetItem([status_map.get(status, status), process_definition])
    #         item.execution_id = execution_id
    #         item.job_uuid = job_uuid
    #         widget.jobs.insertTopLevelItem(count, item)
    #         count += 1


def show_job(item, widget, database):
    if not item or not item.execution_id:
        text = ""
    else:
        engine_id = item.engine_id
        execution_id = item.execution_id
        job_uuid = item.job_uuid
        widget.current_job = job_uuid
        job = widget._jobs[job_uuid]
        text = (
            "<html><body>"
            f"<b>job_uuid</b>: {job['uuid']}<br>"
            f"<b>process</b>: {job.get('process', {}).get('definition')}<br>"
            f"<b>pipeline node</b>: {'.'.join(i for i in job.get('parameters_location', '') if i != 'nodes')}<br>"
            f"<b>return code</b>: {job.get('return_code')}<br>"
            f"<b>start time</b>: {job.get('start_time')}<br>"
            f"<b>end time</b>: {job.get('end_time')}<br>"
            f"<b>wait for</b>: {job.get('wait_for', [])}<br>"
            f"<b>waited by</b>: {job.get('waited_by', [])}<br>"
        )
        parameters = database.workflow_parameters(engine_id, execution_id)
        if parameters:
            for index in job.get("parameters_location", []):
                if index.isnumeric():
                    index = int(index)
                parameters = parameters[index]
        if parameters:
            text += f"parameters:<pre>{pformat(parameters.no_proxy(), indent=4)}</pre>"
        else:
            text += "parameters: none<br>"
        stdout = job.get("stdout")
        stderr = job.get("stderr")
        if stdout:
            text += f"<br><pre>{stdout}</pre>"
        if stderr:
            text += f'<br><pre style="color: red">{stderr}</pre>'
    widget.job.setText(text)
