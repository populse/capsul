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

1. Set the FOM path in Capsul config, using either:

    - in python::

        from capsul.api import capsul_engine
        import sys
        import os

        ce = capsul_engine()
        ce.load_module('fom')
        with ce.settings as s:
            conf = s.config('fom', 'global')
            conf.fom_path = [
                os.path.join(
                    os.path.dirname(sys.modules['capsul'].__file__),
                    'pipeline', 'test', 'fake_morphologist', 'foms')
            ] + conf.fom_path

    - the configuration settings GUI, for instance in Populse-MIA:

        - open the MIA preferences
        - go to the ``Pipeline`` tab
        - click on ``Edit Capsul config``
        - open the ``fom`` tab
        - in ``fom_path``, add an item and enter the path of Capsul sources,
          plus ``capsul/pipeline/test/fake_morphologist/foms``
        - click ``OK`` to validate
        - click ``OK`` in the Mia preferences to validate

2. Instantiate the pipeline, either:

    - in python::

        pipeline = ce.get_process_instance(
            'capsul.pipeline.test.fake_morphologist.morphologist')

    - in MIA:

        - Run populse_mia
        - open a project, if needed
        - go to the pipeline manager tab
        - select in the ``Pipeline`` menu in the tab, ``load pipeline``
        - in the pipeline definition / file edit line, type ``capsul.pipeline.test.fake_morphologist.morphologist``

3. Completion should be available in the pipeline, and it should be able to run.
  Running it is fast (every process just writes a few text lines in output files, just to check that it has run and has been able to create output files).

  Notes about completion in Morphologist / Fake Morphologist:

  - The completion uses the FOM system. It uses attributes which are available in the ``Attributes`` part of parameters controllers GUIs. 2 main attributes are required: ``center`` and ``subject``.
  - If the importation step needs to be used (if the main input is not organised in a brainvisa / morphologist database), then the main ``t1mri`` input has to be filled manually. In controllers GUIs (in MIA for instance), you need to check the "show completion" box on the right at the beginning of non-attribute parameters, then to enter a value for the ``t1mri`` parameter (it's OK to use the MIA ``Filter`` button and select it in the Mia database).
