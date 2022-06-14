======
CAPSUL 
======

Future Capsul version 3
=======================

This branch contains the code of the future 3.0 release. This is still work in progress and using it is not possible through standards installation means such as Pypi.

Using development version od Capsul v3
======================================

To use Capsul v3 it is mandatory to have at least Python 3.9 and the @pydantic_controller@ branch of projects `soma-base <https://github.com/populse/soma-base>`_ and `capsul <https://github.com/populse/capsul>`_ .

The simplest is to use a `casa-distro <https://github.com/brainvisa/casa-distro>`_ container for developers, and setup a minimalist dev environment, based on an Ubuntu 22.04 container with singularity:

* `install singularity <https://brainvisa.info/web/download.html#prerequisites-for-singularity-on-linux>`_


* get a recent `developer image <https://brainvisa.info/web/download.html#installing-a-singularity-developer-environment>`_::
  
        wget https://brainvisa.info/download/casa-dev-5.3-6.sif

* setup a developer environment::

      mkdir capsul3
      singularity run -B capsul3:/casa/setup casa-dev-5.3-6.sif distro=opensource

* change the `bv_maker.cfg` file for a ligher one, which switches to the expected branches::

      cat > capsul3/conf/bv_maker.cfg << EOF
      [ source \$CASA_SRC ]
        brainvisa brainvisa-cmake \$CASA_BRANCH
        brainvisa casa-distro \$CASA_BRANCH
        git https://github.com/populse/soma-base.git pydantic_controller soma/soma-base
        git https://github.com/populse/soma-workflow.git master soma/soma-workflow
        git https://github.com/populse/populse_db.git master populse_db
        git https://github.com/populse/capsul.git pydantic_controller capsul

      [ build \$CASA_BUILD ]
        default_steps = configure build
        make_options = -j\$NCPU
        build_type = Release
        packaging_thirdparty = OFF
        clean_config = ON
        clean_build = ON
        test_ref_data_dir = \$CASA_TESTS/ref
        test_run_data_dir = \$CASA_TESTS/test
        brainvisa brainvisa-cmake \$CASA_BRANCH \$CASA_SRC
        brainvisa casa-distro \$CASA_BRANCH \$CASA_SRC
        + \$CASA_SRC/soma/soma-base
        + \$CASA_SRC/soma/soma-workflow
        + $CASA_SRC/populse_db
        + \$CASA_SRC/capsul
      EOF

* get the code and build::

      python3/bin/bv_maker

* Temporarily (until we ship it in a newer dev image), you need to install pydantic:

      python3/bin/bv pip3 install pydantic

* It's ready. You can us it using either::

      python3/bin/bv bash
      python3/bin/bv ipython3
      python3/bin/bv python <script>

  You can also set the python3/bin directory into your `PATH` configuration.
