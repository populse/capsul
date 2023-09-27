# -*- coding: utf-8 -*-
from soma.web import WebRoutes, WebBackend


class CapsulRoutes(WebRoutes):
    def dashboard(self):
        return self._result('dashboard.html')



    def engine(self, engine_label):
        engine = self._handler['capsul'].engine(engine_label)
        if engine:
            return self._result('engine.html', engine=engine)


    def execution(self, engine_label, execution_id):
        return self._result('execution.html',
            engine_label=engine_label,
            execution_id=execution_id)


class CapsulBackend(WebBackend):
    def engines(self) -> list:
        return [engine.engine_status() for engine in self._handler['capsul'].engines()]


    def engine_status(self, engine_label: str) -> dict:
        try:
            engine = self._handler['capsul'].engine(engine_label)
        except ValueError:
            return {}
        return engine.engine_status()


    def executions_summary(self, engine_label: str) -> list:
        return self._handler['capsul'].engine(engine_label).executions_summary()


    def execution_report(self, engine_label: str, execution_id: str) -> dict:
        with self._handler['capsul'].engine(engine_label) as engine:
            return engine.database.execution_report_json(engine.engine_id, execution_id)
