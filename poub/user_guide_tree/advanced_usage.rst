Parameters completion
#####################

Completion model
================

Using completion
----------------

Process parameters completion for filenames is working using attributes assigned to a process or to its parameters. For instance a given data organization may organize data by study, center, subject, ... These study, center, subject elements can be seen as attributes.

Using an existing completion model is a matter of configuration in StudyConfig. One must use the AttributesModule of StudyConfig, then specify which organization schemas to use.

::

    from capsul.api import StudyConfig

    study_config = StudyConfig('test_study', modules=['AttributesConfig'])
    study_config.input_directory = '/tmp/in'
    study_config.output_directory = '/tmp/out'
    study_config.attributes_schema_paths.append(
        'capsul.attributes.test.test_attributed_process')
    study_config.attributes_schemas['input'] = 'custom_ex'
    study_config.attributes_schemas['output'] = 'custom_ex'
    study_config.path_completion = 'custom_ex'

In this example, the example schemas are defined in the test example ``test_attributed_process``. Completion involves several modular elements:

* data directories: ``study_config.input_directory``, ``study_config.output_directory``, ``study_config.shared_directory``
* schema elements module paths: these are a list of python modules, and must be specified in ``study_config.attributes_schema_paths``
* Naming the attributes schemas to use for the different data directories (input, output, shared): ``study_config.attributes_schemas['input'] = 'custom_ex'`` etc. Each defines the set of attributes used in the data files organization.
* Naming the path completion system: ``study_config.path_completion = 'custom_ex'``. It is responsible for building file names from the attributes set.

Once configured, using completion on a process works as in this example:

::

    process = study_config.get_process_instance(
        'capsul.attributes.test.test_attributed_process.DummyProcess')
    compl_engine = ProcessCompletionEngine.get_completion_engine(process)
    attributes = compl_engine.get_attribute_values()
    attributes.center = 'jojo'
    attributes.subject = 'barbapapa'
    compl_engine.complete_parameters()

After the call to ``compl_engine.complete_parameters()``, the file parameters of ``process`` should be built.

It is possible to make completion run automatically when attributes change, using a notification callback:

::

    attributes.on_trait_change(compl_engine.attributes_changed)

::

    >>> attributes.subject = 'casimir'
    >>> process.truc
    '/tmp/in/DummyProcess_truc_jojo_casimir'

Note that completion will also take place inside iterations in an iterative process, when generating a workflow.


Graphical interface
-------------------

Once PyQt4 or PySide QApplication is created:

::

    from capsul.qt_gui.widgets.attributed_process_widget \
        import AttributedProcessWidget

    cwid = AttributedProcessWidget(process, enable_attr_from_filename=True,
                                   enable_load_buttons=True)
    cwid.show()


Defining a custom completion system
-----------------------------------

It may require to define a few classes to handle the different aspects.

Path building from attributes
+++++++++++++++++++++++++++++

::

    class MyPathCompletion(PathCompletionEngineFactory, PathCompletionEngine):
        factory_id = 'custom_ex'

        def __init__(self):
            super(MyPathCompletion, self).__init__()

        def get_path_completion_engine(self, process):
            return self

        def attributes_to_path(self, process, parameter, attributes):
            study_config = process.get_study_config()
            att_dict = attributes.get_parameters_attributes()[parameter]
            elements = [process.name, parameter]
            # get attributes sorted by user_traits
            for key in attributes.user_traits().keys():
                val = att_dict.get(key)
                if val and val is not Undefined:
                    elements.append(str(val))
            if 'generated_by_parameter' in att_dict:
                directory = study_config.output_directory
            else:
                directory = study_config.input_directory
            return os.path.join(directory, '_'.join(elements))

Note the ``factory_id`` class variable: it is used to register the classes in a factory managed in the study config AttributesConfig module. Its value may be named in the ``study_config.attributes_schemas`` dictionary, as a value for a given directory organization.


Declaring attributes sets
+++++++++++++++++++++++++

::

    class CustomAttributesSchema(AttributesSchema):
        factory_id = 'custom_ex'

        class Acquisition(EditableAttributes):
            center = String()
            subject = String()

        class Group(EditableAttributes):
            group = String()

        class Processing(EditableAttributes):
            analysis = String()

The classes Acquisition, Group and Processing will be available for association to process attributes.


Declaring process and parameters attributes
+++++++++++++++++++++++++++++++++++++++++++

::

    class DummyProcessAttributes(ProcessAttributes):
        factory_id = 'DummyProcess'

        def __init__(self, process, schema_dict):
            super(DummyProcessAttributes, self).__init__(process, schema_dict)
            self.set_parameter_attributes('truc', 'input', 'Acquisition',
                                          dict(type='array'))
            self.set_parameter_attributes('bidule', 'output', 'Acquisition',
                                          dict(type='array'))

In this example, the parameters ``truc`` and ``bidule`` will inherit the attributes declared for ``Acquisition``: namely, ``center`` and ``subject``.


Putting things together
+++++++++++++++++++++++

The modules containing these definitions must be registered in ``study_config.attributes_schema_paths``, and their names have to be used in ``study_config.attributes_schemas`` and ``study_config.path_completion``


File Organization Model (FOM)
=============================

Using FOMs
----------

FOMs are integrated in the completion system. It is activated using the FomConfig module of StudyConfig:

::

    from capsul.api import StudyConfig

    study_config = StudyConfig('test_study', modules=['FomConfig'])
    study_config.inpupt_fom = 'morphologist-auto-1.0'
    study_config.output_fom = 'morphologist-auto-1.0'

The FOM module (throught the AttributesConfig module) sets up the attributes schema:

    >>> study_config.attributes_schema_paths
    ['capsul.attributes.completion_engine_factory']
    >>> study_config.process_completion
    'builtin'

The rest works just as the above completion system.


Defining FOMs
-------------


Iterating processing over multiple data
#######################################

