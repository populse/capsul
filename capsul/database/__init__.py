import importlib
import json

def execution_database_class(database_type):
    db_module = importlib.import_module(f'capsul.database.{database_type}')
    class_name = f'{database_type.capitalize()}ExecutionDatabase'
    return getattr(db_module, class_name)

def create_execution_database(execution_dir, database_type):
    database_class = execution_database_class(database_type)
    with open(f'{execution_dir}/config.json', 'w') as f:
        json.dump({'database_type': database_type}, f)
    return database_class(execution_dir)

def execution_database(execution_dir):
    with open(f'{execution_dir}/config.json') as f:
        database_type = json.load(f)['database_type']
    database_class = execution_database_class(database_type)
    return database_class(execution_dir)
