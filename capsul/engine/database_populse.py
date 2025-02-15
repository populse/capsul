# -*- coding: utf-8 -*-
import os.path as osp

from capsul.engine.database import DatabaseEngine

from populse_db.storage import Storage

schemas = [
    {
        "version": "1.0.0",
        "schema": {
            "named_directory": [
                {
                    "name": [str, {"primary_key": True}],
                    "path": str,
                }
            ],
            "json_value": [
                {
                    "name": [str, {"primary_key": True}],
                    "json_dict": dict,
                }
            ],
            "path_metadata": [
                {
                    "path": [str, {"primary_key": True}],
                    "named_directory": str,
                }
            ],
            "metadata": [
                {
                    "path": [str, {"primary_key": True}],
                    "subject": str,
                    "time_point": str,
                    "history": list[str],  # contains a list of execution_id
                }
            ],
        },
    },
]


class PopulseDBEngine(DatabaseEngine):
    def __init__(self, database_engine):
        self.storage = Storage(database_engine)
        with self.storage.schema() as schema:
            schema.add_schema("capsul.engine.database_populse")

    def __del__(self):
        self.close()

    def close(self):
        self.storage = None


    def set_named_directory(self, name, path):
        if path:
            path = osp.normpath(osp.abspath(path))
        with self.storage.data(write=True) as db:
            if path:
                db.named_directory[name] = path
            else:
                del db.named_directory[name]

    def named_directory(self, name):
        with self.storage.data() as db:
            return db.named_directory[name].path.get()

    def named_directories(self):
        with self.storage.data() as db:
            for row in db.named_directory.search(fields=["name"], as_list=True):
                yield row[0]

    def set_json_value(self, name, json_value):
        with self.storage.data(write=True) as db:
            db["json_value"][name].json_dict = json_value

    def json_value(self, name):
        with self.storage.data(write=True) as db:
            return db["json_value"][name].json_dict.get()

    def set_path_metadata(self, path, metadata):
        named_directory = metadata.get("named_directory")
        if named_directory:
            base_path = self.named_directory("capsul_engine")
            if base_path:
                if not path.startswith(named_directory):
                    raise ValueError(
                        'Path "%s" is defined as relative to named directory %s but it does not start with "%s"'
                        % (path, named_directory, base_path)
                    )
                path = path[len(base_path) + 1 :]
            else:
                if osp.isabs(path):
                    raise ValueError(
                        'Cannot determine relative path for "%s" because its base named directory "%s" is unknown'
                        % (path, named_directory)
                    )
        else:
            if osp.isabs(path):
                for nd in self.named_directories():
                    if path.startswith(nd.path):
                        named_directory = nd.name()
                        path = path[len(nd.path) + 1]
                        break
                else:
                    named_directory = None
            else:
                # capsul_engine is the default named directory for relative paths
                named_directory = "capsul_engine"

        doc = metadata.copy()
        doc["path"] = path
        if named_directory:
            doc["named_directory"] = named_directory
        with self.db as dbs:
            dbs.add_document("path_metadata", doc)

    def path_metadata(self, path):
        if osp.isabs(path):
            for nd in self.named_directories():
                if path.startswith(nd.path):
                    path = path[len(nd.path) + 1 :]
                    break
        with self.db as dbs:
            return dbs.get_document("path_metadata", path)
