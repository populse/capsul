Fake Morphologist pipeline
==========================

This directory contains auto-generated files

obtained using the following python code, with morphologist installed::

    from capsul.api import capsul_engine
    from capsul.pipeline import pipeline_tools
    import sys
    import os

    ce = capsul_engine()
    out_dir = os.path.join(
        os.path.dirname(sys.modules['capsul.pipeline'].__file__),
        'test', 'fake_morphologist')

    m = ce.get_process_instance('morphologist.capsul.morphologist')
    pipeline_tools.write_fake_pipeline(
        m, 'capsul.pipeline.test.fake_morphologist', out_dir)


It contains a replica of the "real" Morphologist pipeline, as a fake one, with no dependencies. It allows to run tests using the real structure of the pipeline, but does not depend on Morphologist and its dependencies (compiled algorithms etc).
