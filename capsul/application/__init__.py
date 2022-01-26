import dataclasses
import importlib
import os
import types
import sys

# Nipype import
try:
    from nipype.interfaces.base import Interface as NipypeInterface
# If nipype is not found create a dummy Interface class
except ImportError:
    NipypeInterface = type("Interface", (object, ), {})

from soma.controller import field

from ..process.process import Process
from ..pipeline.pipeline import Pipeline
from ..process.nipype_process import nipype_factory
from ..engine.local import LocalEngine



class Capsul:
    '''User entry point to Capsul features. 
    This objects reads Capsul configuration in site and user environments.
    It allows configuration customization and instanciation of a 
    CapsulEngine instance to reach an execution environment.
    
    Example:

        from capsul.api import Capsul
        capsul = Capsul()
        e = capsul.executable('capsul.process.test.test_runprocess.DummyProcess')
        with capsul.engine() as capsul_engine:
            capsul_engine.run(e)

    '''    

    @staticmethod
    def is_executable(item):
        '''Check if the input item is a process class or function with decorator
        '''
        if isinstance(item, type) and item not in (Pipeline, Process) \
                and (issubclass(item, Process) or issubclass(item, NipypeInterface)):
            return True
        if not inspect.isfunction(item):
            return False
        if item.__annotations__:
            return True
        return False
    
    def executable(self, definition):
        '''
        Build a Process instance given a definition string
        '''
        item = None
        elements = definition.rsplit('.', 1)
        if len(elements) > 1:
            module_name, object_name = elements
            try:
                module = importlib.import_module(module_name)
                item = getattr(module, object_name, None)
            except ImportError as e:
                pass

        if item is not None:
            return self._executable(definition, item)

        raise ValueError(f'Invalid executable definition: {definition}') 
    

    def _executable(self, definition, item):
        '''
        Build a process instance from a Python object and its definition string.
        '''
        result = None
        # If item is already a Process
        # instance.
        if isinstance(item, Process):
            result = process

        # If item is a Process class.
        elif (isinstance(item, type) and
            issubclass(item, Process)):
            result = item(definition=definition)

        # If item is a Nipye
        # interface instance, wrap this structure in a Process class
        elif isinstance(item, NipypeInterface):
            result = nipype_factory(definition, item)

        # If item is a Nipype Interface class.
        elif (isinstance(item, type) and
            issubclass(item, NipypeInterface)):
            result = nipype_factory(definition, item())

        # If item is a function.
        elif isinstance(item, types.FunctionType):
            annotations = getattr(item, '__annotations__', None)
            if annotations:
                result = self.process_from_function(item)(definition=definition)
            else:
                raise ValueError(f'Cannot find annotation description to make function {item} a process')

        else:
            raise ValueError(f'Cannot create an executable from {item}')           

        return result


    def process_from_function(self, function):
        annotations = {}
        for name, type_ in getattr(function, '__annotations__', {}).items():
            output = name == 'return'
            if isinstance(type_, dataclasses.Field):
                metadata = {}
                metadata.update(type_.metadata)
                metadata['output'] = output
                default=type_.default
                default_factory=type_.default_factory
                kwargs = dict(
                    type_=type_.type,
                    default=default,
                    default_factory=default_factory,
                    repr=type_.repr,
                    hash=type_.hash,
                    init=type_.init,
                    compare=type_.compare,
                    metadata=metadata)
            else:
                kwargs = dict(
                    type_=type_,
                    default=undefined,
                    output=output)
            if output:
                # "return" cannot be used as a parameter because it is a Python keyword.
                #  Change it to "result"
                name = 'result'
            annotations[name] = field(**kwargs)

        def wrap(self):
            kwargs = {i: getattr(self, i) for i in annotations if getattr(self, i, undefined) is not undefined}
            result = function(**kwargs)
            setattr(self, 'result', result)

        namespace = {
            '__annotations__': annotations,
            '__call__': wrap,
        }
        name = f'{function.__name__}_process'
        return type(name, (Process,), namespace)


    def engine(self):
        return LocalEngine()