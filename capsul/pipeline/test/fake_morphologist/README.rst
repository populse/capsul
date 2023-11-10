Fake Morphologist pipeline
==========================

This directory contains mostly auto-generated files

obtained using the following python code, with morphologist installed::

    from capsul.api import executable
    from capsul.pipeline import pipeline_tools
    import sys
    import os

    out_dir = os.path.join(
        os.path.dirname(sys.modules['capsul.pipeline'].__file__), 'test')

    m = executable('morphologist.capsul.morphologist')
    pipeline_tools.write_fake_pipeline(
        m, 'capsul.pipeline.test.fake_morphologist', out_dir)


It contains a replica of the "real" Morphologist pipeline, as a fake one, with no dependencies. It allows to run tests using the real structure of the pipeline, but does not depend on Morphologist and its dependencies (compiled algorithms etc).

[obsolete - needs adaptations for capsul v3]

There is also a copy of the Morphologist "FOM" (file organization model), ``morphologist-auto-1.0.json``, which allows to perform completion on the fake pipeline.

To use it:

1. Import the BrainVisa metadata module and initialize it::

        from capsul.api import Capsul
        from capsul.schemas.brainvisa import (declare_morpho_schemas,
                                            morphologist_datasets)
        from capsul.dataset import ProcessMetadata

        morpho_module = 'capsul.pipeline.test.fake_morphologist'
        # could be the real one instead:
        # morpho_module = 'morphologist.capsul'

        declare_morpho_schemas(morpho_module)


2. Setup Capsul configuration::

        capsul = Capsul()
        config = capsul.config

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
                        'directory': '/usr/local/spm12-standalone',
                        'standalone': True,
                        'version': '12',
                    }
                },
                'matlab': {
                    'matlab_mcr': {
                        'mcr_directory': '/usr/local/spm12-standalone/mcr/v97',
                    }
                },
            }
        })


3. Instantiate the pipeline, either:

    - in python::

        pipeline = capsul.executable(
            'capsul.pipeline.test.fake_morphologist.morphologist')

    - in MIA:

        - Run populse_mia
        - open a project, if needed
        - go to the pipeline manager tab
        - select in the ``Pipeline`` menu in the tab, ``load pipeline``
        - in the pipeline definition / file edit line, type ``capsul.pipeline.test.fake_morphologist.morphologist``

4. Completion::

        execution_context = capsul.engine().execution_context(pipeline)
        # (optional:) get metadata from an input t1mri path in the input BIDS
        # database
        input = '/tmp/morpho-bids/rawdata/sub-aleksander/ses-m0/anat/' \
            'sub-aleksander_ses-m0_T1w.nii.gz'
        input_metadata = execution_context.dataset['input'].schema.metadata(input)

        metadata = ProcessMetadata(pipeline, execution_context,
                                datasets=morphologist_datasets)
        # set input metadata in the pipeline metadata set
        metadata.bids = input_metadata
        # run completion
        metadata.generate_paths(pipeline)


    Notes about completion in Morphologist / Fake Morphologist:

    - If the main input is not organised in a BIDS / brainvisa / morphologist database, then the main ``t1mri`` input has to be filled manually. In controllers GUIs (in MIA for instance), you need to check the "show completion" box on the right at the beginning of non-attribute parameters, then to enter a value for the ``t1mri`` parameter (it's OK to use the MIA ``Filter`` button and select it in the Mia database).
