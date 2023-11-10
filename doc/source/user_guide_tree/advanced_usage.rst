:orphan:

.. _completion:

Parameters completion
#####################

Completion in Capsul v3
=======================

This is not a doc yet, I write down thnigs that I seem to understand at the time I read them in the code.

Process parameters completion for filenames is working using attributes (or "metadata" assigned to a process or to its parameters. For instance a given data organization may organize data by study, center, subject, ... These study, center, subject elements can be seen as attributes.

:mod:`capsul.dataset` contains classes :class:`~capsul.dataset.ProcessMetadata`, :class:`~capsul.dataset.ProcessSchema`, :class:`~capsul.dataset.MetadataSchema`, :class:`~capsul.dataset.BrainVISASchema`.

* Schemas must be defined, by subclassing :class:`~capsul.dataset.MetadataSchema`, like in :class:`~capsul.dataset.BIDSSchema` or :class:`~capsul.dataset.BrainVISASSchema`.

It defines metadata for a given schema name (like ``shared``), and the way to build a filename from metadata and optionally the inverse.

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

    capsul = Capsul(site_file=config_file,
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

  Datasets paths start with a code which should be replaced on server side, because the final location of data may not exist on the client machine which performs the completion. For instance::

    !{dataset.output.path}/subjects/someone/t1mri/m0/someone.nii.gz

  This final replacement can be triggered using::

    morphologist.resolve_paths(execution_context)


Steps to use completion for a pipeline with all already defined
===============================================================

::

    from capsul.api import Capsul
    from capsul.schemas.brainvisa import (declare_morpho_schemas,
                                          morphologist_datasets)
    from capsul.dataset import ProcessMetadata


    morpho_module = 'capsul.pipeline.test.fake_morphologist'


    def get_shared_path():
        try:
            from soma import aims
            return aims.carto.Paths.resourceSearchPath()[-1]
        except Exception:
            return '!{dataset.shared.path}'


    declare_morpho_schemas(morpho_module)

    capsul = Capsul()
    config = capsul.config

    config.builtin.add_module('spm')
    config.builtin.add_module('axon')
    config.import_dict({
        'builtin': {
            'config_modules': [
                'spm',
                'axon',
            ],
            'dataset': {
                'input': {
                    'path': '/tmp/morpho-bids',
                    'metadata_schema': 'bids',
                },
                'output': {
                    'path': '/tmp/morpho-bv',
                    'metadata_schema': 'brainvisa',
                },
                'shared': {
                    'path': get_shared_path(),
                    'metadata_schema': 'brainvisa_shared',
                },
            },
            'spm': {
                'spm12_standalone': {
                    'directory': '/volatile/local/spm12-standalone',
                    'standalone': True,
                    'version': '12',
                }
            },
            'matlab': {
                'matlab_mcr': {
                    'mcr_directory': '/volatile/local/spm12-standalone/mcr/v97' # '/tmp/matlab_mcr/v97',
                }
            },
        }
    })

    mp = capsul.executable('%s.morphologist.Morphologist' % morpho_module)

    execution_context = capsul.engine().execution_context(mp)
    # get metadata from an input t1mri path in the input BIDS database
    input = '/tmp/morpho-bids/rawdata/sub-aleksander/ses-m0/anat/' \
        'sub-aleksander_ses-m0_T1w.nii.gz'
    # completion API
    input_metadata = execution_context.dataset['input'].schema.metadata(input)

    metadata = ProcessMetadata(mp, execution_context,
                               datasets=morphologist_datasets)
    # set input metadata in the pipeline metadata set
    metadata.bids = input_metadata
    # run completion
    metadata.generate_paths(mp)
    mp.resolve_paths(execution_context)


Note that completion will also take place inside iterations in an iterative process, when generating a workflow.


Graphical interface
-------------------

Once PyQt5 or PySide QApplication is created:

::

    from capsul.qt_gui.widgets.attributed_process_widget \
        import AttributedProcessWidget

    cwid = AttributedProcessWidget(process, enable_attr_from_filename=True,
                                   enable_load_buttons=True)
    cwid.show()

If a metadata completion has been setup on the process, attributes will be visible (and editable) in the interface.


Defining a custom completion system
-----------------------------------

It may require to define a few classes to handle the different aspects.


Declaring attributes sets
+++++++++++++++++++++++++



Declaring process and parameters attributes
+++++++++++++++++++++++++++++++++++++++++++



Putting things together
+++++++++++++++++++++++




Iterating processing over multiple data
#######################################

Iterating is done by creating a small pipeline containing an iterative node. This can be done using the utility method :meth:`~capsul.application.Capsul.executable_iteration` of :class:`~capsul.application.Capsul`::

    from capsul.api import Pipeline, Capsul

    non_iterative_plugs = [f.name for f in mp.fields()
                           if f.name in morphologist_datasets
                               and morphologist_datasets.get(f.name)
                                   in ('shared', None)]
    pipeline = capsul.executable_iteration(
        '%s.morphologist.Morphologist' % morpho_module,
        non_iterative_plugs=non_iterative_plugs)
