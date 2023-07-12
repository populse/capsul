:orphan:

.. _completion:

Parameters completion
#####################

Completion in Capsul v3
=======================

This is not a doc yet, I write down thnigs that I seem to understand at the time I read them in the code.

:mod:`capsul.dataset` contains classes :class:`~capsul.dataset.ProcessMetadata`, :class:`~capsul.dataset.ProcessSchema`, :class:`~capsul.dataset.MetadataSchema`, :class:`~capsul.dataset.BrainVISASchema`.

* Schemas must be defined, by subclassing :class:`~capsul.dataset.MetadataSchema`, like in :class:`~capsul.dataset.BIDSSchema` or :class:`~capsul.dataset.BrainVISASSchema`.

It defines metadata fora given schema name (like ``shared``), and the way to build a filename from metadata and optionally the inverse.

::

    class SharedSchema(MetadataSchema):
        '''Metadata schema for BrainVISA shared dataset
        '''
        schema_name = 'shared'
        data_id: str = ''
        side: str = None
        graph_version: str = None
        model_version: str = None

        def _path_list(self):

            path_list = []
            filename = []
            if self.data_id == 'normalization_template':
                path_list = ['anatomical_templates']
                filename.append('MNI152_T1_2mm.nii.gz')
            elif self.data_id == 'trans_mni_to_acpc':
                path_list = ['transformation']
                filename.append('spm_template_novoxels_TO_talairach.trm')
            # ...

            path_list.append(''.join(filename))
            return path_list


* Metadata values are assigned to a process parameters via :class:`~capsul.dataset.ProcessSchema` subclasses.

If a process uses several datasets with different schemas for different parameters (for instance input, output, shared datasets), several :class:`~capsul.dataset.ProcessSchema` subclasses may be declared for the same process class.

As the used shema is specified in the :class:`~capsul.dataset.ProcessSchema` subclass declaration, several subclasses may be declared for the same process parameters with different schemas. The schema selection will be done, for each dataset, at the time of data selection.

* set this in the Capsul config::

    config = {
        'builtin': {
            'dataset': {
                'input': {
                    'path': '/tmp/bids',
                    'metadata_schema': 'bids',
                },
                'output': {
                    'path': '/tmp/brainvisa',
                    'metadata_schema': 'brainvisa',
                },
                'shared': {
                    'path': '/tmp/shared',
                    'metadata_schema': 'shared',
                },
            }
        }
    }

    config_file = '/tmp/capsul_config.json'
    with open(config_file, 'w') as f:
        json.dump(config, f)

    capsul = Capsul('test_fake_morphologist', site_file=config_file,
                    user_file=None)

* Assign datasets and metadata schemas to a given process parameters

::

    datasets = {
        't1mri': 'input',
        'PrepareSubject_Normalization_Normalization_AimsMIRegister_anatomical_template': 'shared',
        'PrepareSubject_TalairachFromNormalization_normalized_referential': 'shared',
        'PrepareSubject_TalairachFromNormalization_transform_chain_ACPC_to_Normalized': 'shared',
        'PrepareSubject_TalairachFromNormalization_acpc_referential': 'shared',
        'PrepareSubject_StandardACPC_older_MNI_normalization': None,
        'PrepareSubject_Normalization_commissures_coordinates': None,
        'PrepareSubject_Normalization_NormalizeFSL_template': 'shared',
        'PrepareSubject_Normalization_NormalizeSPM_template': 'shared',
        'PrepareSubject_Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_normalized_volume': None,
    }

    morphologist = capsul.executable(
        'capsul.pipeline.test.fake_morphologist.morphologist.Morphologist')
    metadata = ProcessMetadata(morphologist, execution_context,
                               datasets=datasets)

* metadata needs to be filled in, either by hand::

    metadata.subject = 'aleksander'
    # etc.

or using an input filename in a schema which has defined the ``metadata`` method::

    input = '/tmp/bids/rawdata/sub-aleksander/ses-m0/anat/sub-aleksander_ses-m0_T1w.nii'
    input_metadata \
        = execution_context.dataset['input'].schema.metadata(input)

    metadata.bids = input_metadata

* Then run the completion::

    metadata.generate_paths(morphologist)


Completion model [v2, obsolete]
===============================

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


.. _fom:

File Organization Model (FOM)
=============================

FOMs are defined in the :mod:`Soma-base library <soma.fom>` as an independent system, and used in Capsul as a files completion implementation.

Using FOMs
----------

FOMs are integrated in the completion system. It is activated using the FomConfig module of StudyConfig:

::

    from capsul.api import StudyConfig

    study_config = StudyConfig('test_study', modules=['FomConfig'])
    study_config.inpupt_fom = 'morphologist-auto-1.0'
    study_config.output_fom = 'morphologist-auto-1.0'

The FOM module (through the AttributesConfig module) sets up the attributes schema:

    >>> study_config.attributes_schema_paths
    ['capsul.attributes.completion_engine_factory']
    >>> study_config.process_completion
    'builtin'

The rest works just as the above completion system.


Defining FOMs
-------------

FOMs are JSON files placed in a FOM path defined somewhere in the application - generally ``<brainvisa_dir>/share/fom``. They define how a set of attributes are used to build paths for processes parameters.

In Capsul a StudyConfig option, `StudyConfig.fom_path` is defined in the :class:`~capsul.study_config.config_modules.fom_config.FomConfig` module to handle the FOM search path.

Ex:

.. code-block:: json

    {
        "fom_name": "morphologist-auto-nonoverlap-1.0",

        "fom_import": ["formats-brainvisa-1.0", "brainvisa-formats-3.2.0",
                       "shared-brainvisa-1.0"],

        "attribute_definitions" : {
          "acquisition" : {"default_value" : "default_acquisition"},
          "analysis" : {"default_value" : "default_analysis"},
          "sulci_recognition_session" :  {"default_value" : "default_session"},
          "graph_version": {"default_value": "3.1"},
        },

        "shared_patterns": {
          "acquisition": "<center>/<subject>/t1mri/<acquisition>",
          "analysis": "{acquisition}/<analysis>",
          "recognition_analysis": "{analysis}/folds/<graph_version>/<sulci_recognition_session>_auto",
        },

        "processes" : {
            "Morphologist" : {
                "t1mri":
                    [["input:{acquisition}/<subject>", "images"]],
                "imported_t1mri":
                    [["output:{acquisition}/<subject>", "images"]],
                "t1mri_referential":
                    [["output:{acquisition}/registration/RawT1-<subject>_<acquisition>", "Referential"]],
                "reoriented_t1mri":
                    [["output:{acquisition}/<subject>", "images"]],
                "t1mri_nobias":
                    [["output:{analysis}/nobias_<subject>", "images" ]],
                "split_brain":
                    [["output:{analysis}/segmentation/voronoi_<subject>","images"]],
                "left_graph":
                    [["output:{analysis}/folds/<graph_version>/<side><subject>",
                        "Graph and data",
                        {"side": "L", "labelled": "No"}]],
                "left_labelled_graph":
                    [["output:{recognition_analysis}/<side><subject>_<sulci_recognition_session>_auto",
                        "Graph and data", {"side": "L"}]],
                "right_graph":
                    [["output:{analysis}/folds/<graph_version>/<side><subject>",
                        "Graph and data", {"side":"R","labelled":"No"}]],
                "right_labelled_graph":
                    [["output:{recognition_analysis}/<side><subject>_<sulci_recognition_session>_auto",
                        "Graph and data", {"side": "R"}]],
                "Talairach_transform":
                    [["output:{acquisition}/registration/RawT1-<subject>_<acquisition>_TO_Talairach-ACPC",
                        "Transformation matrix"]]
            }
        }
    }


Iterating processing over multiple data
#######################################

Iterating is done by creating a small pipeline containing an iterative node. This can be done using the utility method :meth:`~capsul.study_config.study_config.StudyConfig.get_iteration_pipeline` of :class:`~capsul.study_config.study_config.StudyConfig`::

    from capsul.api import Pipeline, StudyConfig
    from capsul.attributes.completion_engine import ProcessCompletionEngine

    study_config = StudyConfig('test_study', modules=['FomConfig'])
    study_config.input_fom = 'morphologist-auto-nonoverlap-1.0'
    study_config.output_fom = 'morphologist-auto-nonoverlap-1.0'

    pipeline = study_config.get_iteration_pipeline(
        'iter', 'morpho', 'morphologist.capsul.morphologist',
        iterative_plugs=['t1mri'])

    cm = ProcessCompletionEngine.get_completion_engine(pipeline)
    cm.get_attribute_values().subject = ['s1', 's2', 's3']
    cm.complete_parameters()

Note that :meth:`~capsul.study_config.study_config.StudyConfig.get_iteration_pipeline` is the equivalent of::

    pipeline = Pipeline()
    pipeline.set_study_config(study_config)
    pipeline.add_iterative_process('morpho',
                                   'morphologist.capsul.morphologist',
                                   iterative_plugs=['t1mri'])
    pipeline.autoexport_nodes_parameters(include_optional=True)
