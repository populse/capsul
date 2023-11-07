# -*- coding: utf-8 -*-
from contextlib import contextmanager
from datetime import datetime
import json
import os
import sqlite3
import tempfile
from uuid import uuid4


from . import ExecutionDatabase


class SQliteExecutionDatabase(ExecutionDatabase):
    @property
    def is_ready(self):
        return os.path.exists(self.path)

    def _connect(self):
        sqlite = sqlite3.connect(self.path, isolation_level=None)
        sqlite.execute('BEGIN EXCLUSIVE TRANSACTION')
        try:
            sql = "SELECT COUNT(*) FROM sqlite_schema WHERE type='table' AND name='capsul_engine'"
            if sqlite.execute(sql).fetchone()[0] == 0:
                sqlite.execute(sql)
                sql = ('CREATE TABLE capsul_properties ( '
                        'key TEXT PRIMARY KEY, '
                        'value TEXT )')
                sqlite.execute(sql)
                sql = ('CREATE TABLE capsul_engine ( '
                        'engine_id TEXT PRIMARY KEY, '
                        'label TEXT, '
                        'config TEXT, '
                        'workers TEXT, '
                        'executions TEXT, '
                        'persistent INTEGER, '
                        'connections INTEGER)')
                sqlite.execute(sql)
                sql = 'CREATE UNIQUE INDEX capsul_engine_label ON capsul_engine (label)'
                sqlite.execute(sql)
                sql = ('CREATE TABLE capsul_connection ( '
                        'connection_id TEXT PRIMARY KEY, '
                        'date TEXT )')
                sqlite.execute(sql)
                sql = ('CREATE TABLE capsul_execution ( '
                        'engine_id TEXT, '
                        'execution_id TEXT, '
                        'label TEXT, '
                        'status TEXT, '
                        'tmp TEXT, '
                        'error TEXT, '
                        'error_detail TEXT, '
                        'start_time TEXT, '
                        'end_time TEXT, '
                        'executable TEXT, '
                        'execution_context TEXT, '
                        'workflow_parameters_values TEXT, '
                        'workflow_parameters_dict TEXT, '
                        'waiting TEXT, '
                        'ready TEXT, '
                        'ongoing TEXT, '
                        'done TEXT, '
                        'failed TEXT, '
                        'dispose INTEGER, '
                        'PRIMARY KEY (engine_id, execution_id))')
                sqlite.execute(sql)
                sql = ('CREATE TABLE capsul_job ( '
                        'engine_id TEXT, '
                        'execution_id TEXT, '
                        'job_id TEXT, '
                        'job TEXT, '
                        'PRIMARY KEY (engine_id, execution_id, job_id))')
                sqlite.execute(sql)
            sqlite.execute('COMMIT')
        except Exception:
            sqlite.execute('ROLLBACK')
            raise
        sqlite.execute('PRAGMA busy_timeout=60000')
        return sqlite

    @contextmanager
    def _read(self):
        if os.path.exists(self.path):
            sqlite = self._connect()
            sqlite.execute('BEGIN DEFERRED TRANSACTION')
            try:
                yield sqlite
                sqlite.execute('COMMIT')
            except Exception:
                sqlite.execute('ROLLBACK')
                raise
        else:
            yield None
    
    @contextmanager
    def _read_write(self):
        sqlite = self._connect()
        sqlite.execute('BEGIN EXCLUSIVE TRANSACTION')
        try:
            yield sqlite
            sqlite.execute('COMMIT')
        except Exception:
            sqlite.execute('ROLLBACK')
            raise

    @property
    def is_connected(self):
        return False

    def engine_id(self, label):
        with self._read() as sqlite:
            if sqlite:
                sql = 'SELECT engine_id FROM capsul_engine WHERE label=?'
                cursor = sqlite.execute(sql, [label])
                return cursor.fetchone()[0]

    def _enter(self):
        self.uuid = str(uuid4())

        if self.config['type'] == 'sqlite':
            if self.path is None:
                raise ValueError('Database path is missing in configuration')
            if self.path == '':
                tmp = tempfile.NamedTemporaryFile(delete=False, prefix='capsul_', suffix='.sqlite')
                try:
                    self._path = tmp.name
                    with self._read_write() as sqlite:
                        sql = 'INSERT INTO capsul_properties (key, value) VALUES (?, ?)'
                        sqlite.execute(sql, ['tmp', self.path])
                except Exception:
                    os.remove(tmp.name)
        else:
            raise NotImplementedError(
                f'Invalid SQLite connection type: {self.config["type"]}')
        with self._read_write() as sqlite:
            sql = 'INSERT INTO capsul_connection (connection_id, date) VALUES (?, ?)'
            sqlite.execute(sql, [self.uuid, datetime.now().isoformat()])
    

    def _exit(self):
        with self._read_write() as sqlite:
            sql = "DELETE FROM capsul_connection WHERE connection_id=?"
            sqlite.execute(sql, [self.uuid])
   

    def get_or_create_engine(self, engine, update_database=False):
        with self._read_write() as sqlite:
            sql = 'SELECT engine_id FROM capsul_engine WHERE label=?'
            row = sqlite.execute(sql, [engine.label]).fetchone()
            if row:
                engine_id = row[0]
                if update_database:
                    # Update configuration stored in database
                    sql = "UPDATE capsul_engine SET config=?, persistent=? WHERE engine_id=?"
                    sqlite.execute(sql, [json.dumps(engine.config.json()), engine.config.persistent, engine_id])
            else:
                # Create new engine in database
                engine_id = str(uuid4())
                sql = ('INSERT INTO capsul_engine (engine_id, label, config, '
                       'workers, executions, persistent, connections) VALUES '
                       '(?, ?, ?, ?, ?, ?, ?)')
                sqlite.execute(sql, [
                    engine_id,
                    engine.label,
                    # config: Engine configuration dictionary
                    json.dumps(engine.config.json()),
                    # workers: list of running workers
                    '[]',
                    # executions: list of execution_id
                    '[]',
                    # persistent: 1 if persistent else 0
                    (1 if engine.config.persistent else 0),
                    # connections: number of connections
                    0
                ])
            sql = 'UPDATE capsul_engine SET connections = connections + 1 WHERE engine_id=?'
            sqlite.execute(sql, [engine_id])
            return engine_id
    

    def engine_connections(self, engine_id):
        with self._read() as sqlite:
            if sqlite:
                sql = 'SELECT connections FROM capsul_engine WHERE engine_id=?'
                row = sqlite.execute(sql, [engine_id]).fetchone()
                if row:
                    return row[0]
    

    def engine_config(self, engine_id):
        with self._read() as sqlite:
            if sqlite:
                sql = 'SELECT config FROM capsul_engine WHERE engine_id=?'
                row = sqlite.execute(sql, [engine_id]).fetchone()
                if row:
                    return json.loads(row[0])
        raise ValueError(f'Invalid engine_id: {engine_id}')


    def workers_count(self, engine_id):
        with self._read() as sqlite:
            if sqlite:
                sql = 'SELECT workers FROM capsul_engine WHERE engine_id=?'
                row = sqlite.execute(sql, [engine_id]).fetchone()
                if row:
                    return len(json.loads(row[0]))
        return 0


    def worker_database_config(self, engine_id):
        return self.config


    def worker_started(self, engine_id):
        with self._read_write() as sqlite:
            worker_id = str(uuid4())
            sql = 'SELECT workers FROM capsul_engine WHERE engine_id=?'
            result = sqlite.execute(sql, [engine_id]).fetchone()
            if result:
                workers = json.loads(result[0])
                workers.append(worker_id)
                sql = 'UPDATE capsul_engine SET workers=? WHERE engine_id=?'
                sqlite.execute(sql,[json.dumps(workers), engine_id])
                return worker_id
            raise ValueError(f'Invalid engine_id: {engine_id}')


    def worker_ended(self, engine_id, worker_id):
        with self._read_write() as sqlite:
            sql = 'SELECT workers FROM capsul_engine WHERE engine_id=?'
            row = sqlite.execute(sql, [engine_id]).fetchone()
            if row:
                workers = json.loads(row[0])
                workers.remove(worker_id)
                sql = 'UPDATE capsul_engine SET workers=? WHERE engine_id=?'
                sqlite.execute(sql,[json.dumps(workers), engine_id])
            raise ValueError(f'Invalid engine_id: {engine_id}')


    def persistent(self, engine_id):
        with self._read() as sqlite:
            if sqlite:
                sql = 'SELECT persistent FROM capsul_engine WHERE engine_id=?'
                row = sqlite.execute(sql, [engine_id]).fetchone()
                if row:
                    return bool(row[0])
        return False


    def set_persistent(self, engine_id, persistent):
        with self._read_write() as sqlite:
            sql = 'UPDATE capsul_engine SET persistent=? WHERE engine_id=?'
            sqlite.execute(sql, [(1 if persistent else 0), engine_id])


    def dispose_engine(self, engine_id):
        with self._read_write() as sqlite:
            sql = 'SELECT connections, persistent, executions FROM capsul_engine WHERE engine_id=?'
            row = sqlite.execute(sql, [engine_id]).fetchone()
            if row:
                connections, persistent, executions = row
                connections -= 1
                sql = 'UPDATE capsul_engine SET label=NULL WHERE engine_id=?'
                sqlite.execute(sql, [engine_id])
                if connections == 0 and not persistent:
                    executions = json.loads(executions)
                    # Check if some executions had not been disposed
                    erase = True
                    for execution_id in executions:
                        sql = 'SELECT dispose FROM capsul_execution WHERE engine_id=? AND execution_id=?'
                        row = sqlite.execute(sql, [engine_id, execution_id]).fetchone()
                        if row and not row[0]:
                            erase = False
                            break
                    if erase:
                        # Nothing is ongoing, completely remove engine
                        sql = 'DELETE FROM capsul_execution WHERE engine_id=?'
                        sqlite.execute(sql, [engine_id])
                        sql = 'DELETE FROM capsul_engine WHERE engine_id=?'
                        sqlite.execute(sql, [engine_id])
                        sql = 'DELETE FROM capsul_job WHERE engine_id=?'
                        sqlite.execute(sql, [engine_id])
                else:
                    sql = 'UPDATE capsul_engine SET connections=? WHERE engine_id=?'
                    sqlite.execute(sql, [connections, engine_id])

    def executions_summary(self, engine_id):
        result = []
        with self._read() as sqlite:
            if sqlite:
                sql = 'SELECT label, executions FROM capsul_engine WHERE engine_id=?'
                row = sqlite.execute(sql, [engine_id]).fetchone()
                if row:
                    label, executions = row
                    executions = json.loads(executions)
                    for execution_id in executions:
                        sql = ('SELECT label, status, waiting, ready, ongoing, done, failed '
                            'FROM capsul_execution WHERE engine_id=? AND execution_id=?')
                        row = sqlite.execute(sql, [engine_id, execution_id]).fetchone()
                        if row:
                            info = {
                                'label': row[0],
                                'status': row[1],
                                'waiting': len(json.loads(row[2])),
                                'ready': len(json.loads(row[3])),
                                'ongoing': len(json.loads(row[4])),
                                'done': len(json.loads(row[5])),
                                'failed': len(json.loads(row[6])),
                                'engine_label': label,
                                'execution_id': execution_id,
                            }
                            result.append(info)
        return result



    def store_execution(self,
            engine_id,
            label,
            start_time, 
            executable_json,
            execution_context_json,
            workflow_parameters_values_json,
            workflow_parameters_dict_json,
            jobs,
            ready,
            waiting
        ):
        with self._read_write() as sqlite:
            execution_id = str(uuid4())
            sql = 'SELECT executions FROM capsul_engine WHERE engine_id=?'
            row = sqlite.execute(sql, [engine_id]).fetchone()
            if row:
                executions = json.loads(row[0])
                executions.append(execution_id)
                sql = 'UPDATE capsul_engine SET executions=? WHERE engine_id=?'
                sqlite.execute(sql, [json.dumps(executions), engine_id])
                if ready:
                    status = 'ready'
                    end_time = None
                else:
                    status = 'ended'
                    end_time = start_time
                sql = ('INSERT INTO capsul_execution '
                       '(engine_id, execution_id, label, status, start_time, end_time,'
                       ' executable, execution_context, workflow_parameters_values,'
                       ' workflow_parameters_dict, ready, waiting, ongoing, done, failed)'
                       ' VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)')
                sqlite.execute(sql, [
                    engine_id,
                    execution_id,
                    label,
                    status,
                    start_time,
                    end_time,
                    json.dumps(executable_json),
                    json.dumps(execution_context_json),
                    json.dumps(workflow_parameters_values_json),
                    json.dumps(workflow_parameters_dict_json),
                    json.dumps(ready),
                    json.dumps(waiting),
                    '[]',
                    '[]',
                    '[]',
                ])
                sql = 'INSERT INTO capsul_job (engine_id, execution_id, job_id, job) VALUES (?,?,?,?)'
                sqlite.executemany(sql, [[engine_id, execution_id, job['uuid'], json.dumps(job)]
                                         for job in jobs])
            return execution_id


    def execution_context_json(self, engine_id, execution_id):
        with self._read() as sqlite:
            if sqlite:
                sql = 'SELECT execution_context FROM capsul_execution WHERE engine_id=? AND execution_id=?'
                row = sqlite.execute(sql, [engine_id, execution_id]).fetchone()
                if row:
                    return json.loads(row[0])


    def pop_job_json(self, engine_id, start_time):
        with self._read_write() as sqlite:
            sql = 'SELECT executions FROM capsul_engine WHERE engine_id=?'
            row = sqlite.execute(sql, [engine_id]).fetchone()
            if not row:
                # engine_id does not exist anymore
                # return None to say to workers that they can die
                return None, None
            executions = json.loads(row[0])
            all_disposed = True
            for execution_id in executions:
                sql = 'SELECT dispose, status, ready, ongoing FROM capsul_execution WHERE engine_id=? AND execution_id=?'
                row = sqlite.execute(sql, [engine_id, execution_id]).fetchone()
                dispose, status, ready, ongoing = row
                all_disposed = all_disposed and dispose
                if status == 'ready':
                    sql = 'UPDATE capsul_execution SET status=? WHERE engine_id=? AND execution_id=?'
                    sqlite.execute(sql, ['initialization', engine_id, execution_id])
                    return execution_id, 'start_execution'
                if status == 'running':
                    ready = json.loads(ready)
                    ongoing = json.loads(ongoing)
                    if ready:
                        job_id = ready.pop(0)
                        ongoing.append(job_id)
                        sql = 'UPDATE capsul_execution SET ready=?, ongoing=? WHERE engine_id=? AND execution_id=?'
                        sqlite.execute(sql, [json.dumps(ready), json.dumps(ongoing), engine_id, execution_id])
                        sql = 'SELECT job FROM capsul_job WHERE engine_id=? AND execution_id=? AND job_id=?'
                        row = sqlite.execute(sql, [engine_id, execution_id, job_id]).fetchone()
                        job = json.loads(row[0])
                        job['start_time'] = start_time
                        sql = 'UPDATE capsul_job SET job=? WHERE engine_id=? AND execution_id=? AND job_id=?'
                        sqlite.execute(sql, [json.dumps(job), engine_id, execution_id, job_id])
                        return execution_id, job_id
                if status == 'finalization':
                    return execution_id, 'end_execution'
            if all_disposed:
                # No more active execution, worker can die.
                return None, None
            else:
                # Empty string means "no job ready yet"
                return '', ''


    def job_finished_json(self, engine_id, execution_id, job_id, 
                          end_time, return_code, stdout, stderr):
        with self._read_write() as sqlite:
            sql = 'SELECT job FROM capsul_job WHERE engine_id=? AND execution_id=? AND job_id=?'
            row = sqlite.execute(sql, [engine_id, execution_id, job_id]).fetchone()
            job = json.loads(row[0])
            job['end_time'] = end_time
            job['return_code'] = return_code
            job['stdout'] = stdout
            job['stderr'] = stderr
            sql = 'UPDATE capsul_job SET job=? WHERE engine_id=? AND execution_id=? AND job_id=?'
            sqlite.execute(sql, [json.dumps(job), engine_id, execution_id, job_id])

            sql = 'SELECT ready, ongoing, failed, waiting, done FROM capsul_execution WHERE engine_id=? AND execution_id=?'
            row = sqlite.execute(sql, [engine_id, execution_id]).fetchone()
            ready, ongoing, failed, waiting, done = [json.loads(i) for i in row]
            ongoing.remove(job_id)
            if return_code != 0:
                failed.append(job_id)

                stack = set(job.get('waited_by', []))
                while stack:
                    waiting_id = stack.pop()
                    sql = 'SELECT job FROM capsul_job WHERE engine_id=? AND execution_id=? AND job_id=?'
                    row = sqlite.execute(sql, [engine_id, execution_id, waiting_id]).fetchone()
                    waiting_job = json.loads(row[0])
                    waiting_job['return_code'] = 'Not started because de dependent job failed'
                    sql = 'UPDATE capsul_job SET job=? WHERE engine_id=? AND execution_id=? AND job_id=?'
                    sqlite.execute(sql, [json.dumps(waiting_job), engine_id, execution_id, job_id])
                    waiting.remove(waiting_id)
                    failed.insert(waiting_id)
                    stack.update(waiting_job.get('waited_by', []))
            else:
                done.append(job_id)
                for waiting_id in job.get('waited_by', []):
                    sql = 'SELECT job FROM capsul_job WHERE engine_id=? AND execution_id=? AND job_id=?'
                    row = sqlite.execute(sql, [engine_id, execution_id, waiting_id]).fetchone()
                    waiting_job = json.loads(row[0])
                    ready_to_go = True
                    for waited in waiting_job.get('wait_for', []):
                        if waited not in done:
                            ready_to_go = False
                            break
                    if ready_to_go:
                        waiting.remove(waiting_id)
                        ready.append(waiting_id)

            sql = ('UPDATE capsul_execution SET ready=?, ongoing=?, failed=?, '
                   'waiting=?, done=? WHERE engine_id=? AND execution_id=?')
            sqlite.execute(sql, [
                json.dumps(ready),
                json.dumps(ongoing),
                json.dumps(failed),
                json.dumps(waiting),
                json.dumps(done),
                engine_id, execution_id
            ])

            if not ongoing and not ready:
                if failed:
                    sql = 'UPDATE capsul_execution SET error=? WHERE engine_id=? AND execution_id=?'
                    sqlite.execute(sql, ['Some jobs failed', engine_id, execution_id])
                sql = 'UPDATE capsul_execution SET status=?, end_time=? WHERE engine_id=? AND execution_id=?'
                sqlite.execute(sql, ['finalization', end_time, engine_id, execution_id])


    def status(self, engine_id, execution_id):
        with self._read() as sqlite:
            if sqlite:
                sql = 'SELECT status FROM capsul_execution WHERE engine_id=? AND execution_id=?'
                return sqlite.execute(sql, [engine_id, execution_id]).fetchone()[0]

        
    def workflow_parameters_values_json(self, engine_id, execution_id):
        with self._read() as sqlite:
            if sqlite:
                sql = 'SELECT workflow_parameters_values FROM capsul_execution WHERE engine_id=? AND execution_id=?'
                row = sqlite.execute(sql, [engine_id, execution_id]).fetchone()
                return json.loads(row[0])


    def workflow_parameters_dict(self, engine_id, execution_id):
        with self._read() as sqlite:
            if sqlite:
                sql = 'SELECT workflow_parameters_dict FROM capsul_execution WHERE engine_id=? AND execution_id=?'
                row = sqlite.execute(sql, [engine_id, execution_id]).fetchone()
                return json.loads(row[0])


    def get_job_input_parameters(self, engine_id, execution_id, job_id):
        with self._read_write() as sqlite:
            sql = 'SELECT workflow_parameters_values FROM capsul_execution WHERE engine_id=? AND execution_id=?'
            row = sqlite.execute(sql, [engine_id, execution_id]).fetchone()
            values = json.loads(row[0])
            sql = 'SELECT job FROM capsul_job WHERE engine_id=? AND execution_id=? AND job_id=?'
            row = sqlite.execute(sql, [engine_id, execution_id, job_id]).fetchone()
            job = json.loads(row[0])
            indices = job.get('parameters_index', {})
            result = {}
            for k, i in indices.items():
                if isinstance(i, list):
                    result[k] = [values[j] for j in i]
                else:
                    result[k] = values[i]
            job['input_parameters'] = result
            sql = 'UPDATE capsul_job SET job=? WHERE engine_id=? AND execution_id=? AND job_id=?'
            sqlite.execute(sql, [json.dumps(job), engine_id, execution_id, job_id])
            return result        


    def set_job_output_parameters(self, engine_id, execution_id, job_id, output_parameters):
        with self._read_write() as sqlite:
            sql = 'SELECT workflow_parameters_values FROM capsul_execution WHERE engine_id=? AND execution_id=?'
            row = sqlite.execute(sql, [engine_id, execution_id]).fetchone()
            values = json.loads(row[0])
            sql = 'SELECT job FROM capsul_job WHERE engine_id=? AND execution_id=? AND job_id=?'
            row = sqlite.execute(sql, [engine_id, execution_id, job_id]).fetchone()
            job = json.loads(row[0])
            indices = job.get('parameters_index', {})
            for name, value in output_parameters.items():
                values[indices[name]] = value
            job['output_parameters'] = output_parameters
            sql = 'UPDATE capsul_job SET job=? WHERE engine_id=? AND execution_id=? AND job_id=?'
            sqlite.execute(sql, [json.dumps(job), engine_id, execution_id, job_id])
            sql = 'UPDATE capsul_execution SET workflow_parameters_values=? WHERE engine_id=? AND execution_id=?'
            sqlite.execute(sql, [json.dumps(values), engine_id, execution_id])


    def job_json(self, engine_id, execution_id, job_id):
        with self._read() as sqlite:
            if sqlite:
                sql = 'SELECT job FROM capsul_job WHERE engine_id=? AND execution_id=? AND job_id=?'
                row = sqlite.execute(sql, [engine_id, execution_id, job_id]).fetchone()
                return json.loads(row[0])


    def execution_report_json(self, engine_id, execution_id):
        with self._read() as sqlite:
            if sqlite:
                sql = ('SELECT label, status, tmp, error, error_detail, start_time, end_time, '
                    'executable, execution_context, workflow_parameters_values, waiting, '
                    'ready, ongoing, done, failed FROM capsul_execution '
                    'WHERE engine_id=? AND execution_id=?')
                row = sqlite.execute(sql, [engine_id, execution_id]).fetchone()
                (label, status, tmp, error, error_detail, start_time, end_time, executable,
                execution_context, parameters_values, waiting, ready, ongoing,
                done, failed) = row
                
                sql = 'SELECT job FROM capsul_job WHERE engine_id=? AND execution_id=?'
                rows = sqlite.execute(sql, [engine_id, execution_id])
                jobs = [json.loads(row[0]) for row in rows]
                parameters_values = json.loads(parameters_values)
                for job in jobs:
                    job['parameters'] = self.job_parameters_from_values(
                        job, parameters_values)

                result = dict(
                    label=label,
                    engine_id=engine_id,
                    execution_id=execution_id,
                    executable=json.loads(executable),
                    execution_context=json.loads(execution_context),
                    status=status,
                    error=error,
                    error_detail=error_detail,
                    start_time=start_time,
                    end_time=end_time,
                    workflow_parameters=parameters_values,
                    waiting=json.loads(waiting),
                    ready=json.loads(ready),
                    ongoing=json.loads(ongoing),
                    done=json.loads(done),
                    failed=json.loads(failed),
                    jobs=jobs,
                    temporary_directory=tmp,
                    engine_debug={},
                )
                return result


    def dispose(self, engine_id, execution_id):
        with self._read_write() as sqlite:
            sql = 'SELECT status FROM capsul_execution WHERE engine_id=? AND execution_id=?'
            row = sqlite.execute(sql, [engine_id, execution_id]).fetchone()
            if row[0] == 'ended':
                sql = 'SELECT persistent, executions FROM capsul_engine WHERE engine_id=?'
                row = sqlite.execute(sql, [engine_id]).fetchone()
                persistent, executions = row
                if not persistent:
                    sql = 'DELETE FROM capsul_job WHERE engine_id=? AND execution_id=?'
                    sqlite.execute(sql, [engine_id, execution_id])
                    sql = 'DELETE FROM capsul_execution WHERE engine_id=? AND execution_id=?'
                    sqlite.execute(sql, [engine_id, execution_id])
                    executions = json.loads(executions)
                    executions.remove(execution_id)
                    sql = 'UPDATE capsul_engine SET executions=? WHERE engine_id=?'
                    sqlite.execute(sql, [json.dumps(executions), engine_id])
                    


    def check_shutdown(self):
        database_empty = False
        with self._read() as sqlite:
            if sqlite:
                sql = 'SELECT COUNT(*) FROM capsul_connection'
                row = sqlite.execute(sql).fetchone()
                if row[0] == 0:
                    sql = 'SELECT COUNT(*) FROM capsul_engine'
                    row = sqlite.execute(sql).fetchone()
                    if row[0] == 0:
                        database_empty = True
        if database_empty and os.path.exists(self.path):
            os.remove(self.path)

    
    def start_execution(self, engine_id, execution_id, tmp):
        with self._read_write() as sqlite:
            sql = 'UPDATE capsul_execution SET tmp=?, status=? WHERE engine_id=? AND execution_id=?'
            sqlite.execute(sql, [tmp, 'running', engine_id, execution_id]).fetchone()


    def end_execution(self, engine_id, execution_id):
        with self._read_write() as sqlite:
            sql = 'SELECT tmp, dispose, label FROM capsul_execution WHERE engine_id=? AND execution_id=?'
            row = sqlite.execute(sql, [engine_id, execution_id]).fetchone()
            tmp, dispose, label = row
            sql = 'UPDATE capsul_execution SET status=?, tmp=? WHERE engine_id=? AND execution_id=?'
            sqlite.execute(sql, ['ended', None, engine_id, execution_id])
            if dispose:
                sql = 'SELECT executions FROM capsul_engine WHERE engine_id=?'
                row = sqlite.execute(sql, [engine_id]).fetchone()
                executions = json.loads(row[0])
                executions.remove(execution_id)
                sql = 'UPDATE capsul_engine SET executions=? WHERE engine_id=?'
                sqlite.execute(sql, [json.dumps(executions), engine_id])
                sql = 'DELETE FROM capsul_job WHERE engine_id=? AND execution_id=?'
                sqlite.execute(sql, [engine_id, execution_id])
                sql = 'DELETE FROM capsul_execution WHERE engine_id=? AND execution_id=?'
                sqlite.execute(sql, [engine_id, execution_id])
                if not executions and not label:
                    # Engine is already disopsed: delete it
                    sql = 'DELETE FROM capsul_execution WHERE engine_id=?'
                    sqlite.execute(sql, [engine_id])
                    sql = 'DELETE FROM capsul_engine WHERE engine_id=?'
                    sqlite.execute(sql, [engine_id])
                    sql = 'DELETE FROM capsul_job WHERE engine_id=?'
                    sqlite.execute(sql, [engine_id])
            return tmp


    def tmp(self, engine_id, execution_id):
        with self._read() as sqlite:
            if sqlite:
                sql = 'SELECT tmp FROM capsul_execution WHERE engine_id=? AND execution_id=?'
                row = sqlite.execute(sql, [engine_id, execution_id]).fetchone()
                if row:
                    return row[0]


    def error(self, engine_id, execution_id):
        with self._read() as sqlite:
            if sqlite:
                sql = 'SELECT error FROM capsul_execution WHERE engine_id=? AND execution_id=?'
                row = sqlite.execute(sql, [engine_id, execution_id]).fetchone()
                if row:
                    return row[0]

    
