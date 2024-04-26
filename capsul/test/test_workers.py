from capsul.api import Capsul
import time

def noop() -> None:
    pass

def test_start_workers():
    capsul = Capsul(database_path="")
    noop_executable = capsul.executable(noop)
    for wc in [3, 2, 1]:
        with capsul.engine(workers_count=wc) as engine:
            requested = engine.config.start_workers.get("count", 0)
            assert requested == wc
            noop_id = engine.start(noop_executable)
            for i in range(100):
                if engine.database.workers_count(engine.engine_id) == wc:
                    break
                time.sleep(0.2)
            else:
                raise RuntimeError(f'expected {wc} workers to be created, got {engine.database.workers_count(engine.engine_id)}')
            engine.dispose(noop_id)
            for i in range(100):
                if engine.database.workers_count(engine.engine_id) == 0:
                    break
                time.sleep(0.2)
            else:
                raise RuntimeError(f'expected workers to be stopped; running workers = {engine.database.workers_count(engine.engine_id)}')
