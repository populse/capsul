cmake_minimum_required( VERSION 2.6 )

# look for BrainVisa config

set( brainvisa_enabled "0" )
set( USE_BRAINVISA_CMAKE TRUE CACHE BOOL "use Brainvisa cmake build system" )

if( USE_BRAINVISA_CMAKE )
  find_package( brainvisa-cmake )
  if( brainvisa-cmake_FOUND )
    set( brainvisa_enabled "1" )
    BRAINVISA_PROJECT()
  endif()
endif()


# Brainvisa-cmake / bv_maker config

if( brainvisa_enabled )

  BRAINVISA_DEPENDENCY( RUN DEPENDS python RUN ">= 2.5;<< 3.0" )
  BRAINVISA_COPY_PYTHON_DIRECTORY( "${CMAKE_CURRENT_SOURCE_DIR}/capsul"
                                  ${PROJECT_NAME} python/capsul )
  find_package( python REQUIRED )
  find_package( Sphinx )

  BRAINVISA_GENERATE_SPHINX_DOC( "doc/source"
    "share/doc/capsul-${BRAINVISA_PACKAGE_VERSION_MAJOR}.${BRAINVISA_PACKAGE_VERSION_MINOR}" )

  set( BV_ENV_PYTHON_CMD 
    "${CMAKE_BINARY_DIR}/bin/bv_env" "${PYTHON_EXECUTABLE}" )

#   BRAINVISA_CREATE_CMAKE_CONFIG_FILES()

  # tests
  enable_testing()
  add_test( capsul-tests "${CMAKE_BINARY_DIR}/bin/bv_env" "${PYTHON_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/test/test_capsul.py" )

endif()

# independent (pure CMake) config

if( NOT brainvisa_enabled )

  set( PROJECT_NAME capsul )
  set( capsul_VERSION 1.0 )
  set( CAPSUL_VERSION_MAJOR 0 )
  set( CAPSUL_VERSION_MINOR 0 )
  set( CAPSUL_VERSION_PATCH 1 )
  set( CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin" )
  if ( NOT DEFINED WIN32 )
    set( CMAKE_LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib" )
  else()
    set( CMAKE_LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin" )
  endif()

  find_package( PythonInterp REQUIRED )

  # doc
  add_custom_command( TARGET doc
    COMMAND make 
    WORKGING_DIRECTORY ${CMAKE_BINARY_DIR}/doc )

  # tests
  enable_testing()
  add_test( capsul-tests "${PYTHON_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/test/test_capsul.py" )

endif()

