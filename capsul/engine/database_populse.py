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
                    "value": dict,
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
        print('!!!!!!!!!!!!!', database_engine)
        self.storage = Storage(database_engine)
        with self.storage.schema() as schema:
            schema.add_schema("capsul.engine.database_populse")

    def __del__(self):
        self.close()

    def close(self):
        self.db = None

    def commit(self):
        # self.dbs.save_modifications()
        with self.db as dbs:
            dbs.save_modifications()

    def rollback(self):
        # self.dbs.unsave_modifications()
        with self.db as dbs:
            dbs.unsave_modifications()

    def set_named_directory(self, name, path):
        if path:
            path = osp.normpath(osp.abspath(path))
        # doc = self.dbs.get_document('named_directory', name)
        # if doc is None:
        # if path:
        # doc = {'name': name,
        #'path': path}
        # self.dbs.add_document('named_directory', doc)
        # else:
        # if path:
        # self.dbs.set_value('named_directory', name, 'path', path)
        # else:
        # self.dbs.remove_document('named_directory', name)
        with self.db as dbs:
            doc = dbs.get_document("named_directory", name)
            if doc is None:
                if path:
                    doc = {"name": name, "path": path}
                    dbs.add_document("named_directory", doc)
            else:
                if path:
                    dbs.set_value("named_directory", name, "path", path)
                else:
                    dbs.remove_document("named_directory", name)

    def named_directory(self, name):
        # return self.dbs.get_value('named_directory', name, 'path')
        with self.db as dbs:
            return dbs.get_value("named_directory", name, "path")

    def named_directories(self):
        # return self.dbs.filter_documents('named_directory', 'all')
        with self.db as dbs:
            return dbs.filter_documents("named_directory", "all")

    def set_json_value(self, name, json_value):
        # doc = self.dbs.get_document('json_value', name)
        # json_dict = {'value': json_value}
        # if doc is None:
        # doc = {'name': name,
        #'json_dict': json_dict
        # }
        # self.dbs.add_document('json_value', doc)
        # else:
        # self.dbs.set_value('json_value', name, 'json_dict', json_dict)
        with self.db as dbs:
            doc = dbs.get_document("json_value", name)
            json_dict = {"value": json_value}
            if doc is None:
                doc = {"name": name, "json_dict": json_dict}
                dbs.add_document("json_value", doc)
            else:
                dbs.set_value("json_value", name, "json_dict", json_dict)

    def json_value(self, name):
        # doc = self.dbs.get_document('json_value', name)
        # if doc:
        # return doc['json_dict']['value']
        # return None
        with self.db as dbs:
            doc = dbs.get_document("json_value", name)
            if doc:
                return doc["json_dict"]["value"]
            return None

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
