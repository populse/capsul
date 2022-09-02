Path generation API
===================

We call path generation the automatic creation of path values that are missing from a process parameters given the values of one or more other path parameters. This issue describes how this path creation is managed by Capsul and what are the API changes that are required to make it work.


General principles
------------------

The path generation system is designed to be fully automatic. Path generation must not need any user input except the selection of a few input parameters of the process. This is important to be able to use path generation on iteration of hundreds of executions. 

Path generation is done using metadata attached to path parameters of the process. Therefore, it is mandatory to be able to associate metadata to these parameters. This can be fairly easy if the process uses only one metadata schema; for instance if all input and output data are following the BIDS standard. However, in many cases a process will have to deal with several metadata schemas. For instance, there could be one schema for input data (i.e. BIDS), another schema for output data (for use cases not covered by BIDS) and other schemas for third party data (for instance template images in SPM software directory). Therefore, the path generation system must support several metadata schema. The `Dataset` class has a central position in the management of paths and metadata.

Datasets
--------

A dataset is an object that is attached to a directory (it contains its path) and makes the link between the directory content and a schema of metadata. A `Dataset` is based on a `MetadataSchema` that is a `Controller` whose fields describes the metadata schema. For instance, a BIDS dataset class could be defined as follows:

```
class BIDSSchema(MetadataSchema):
    ''' BIDS metadata schema
    '''
    folder: Literal['sourcedata', 'rawdata', 'derivative']
    pipeline: str = None
    sub: str
    ses: str
    data_type: str
    task: str = None
    acq: str = None
    ce: str = None
    rec: str = None
    run: str = None
    echo: str = None
    part: str = None
    suffix: str
    extension: st

```

The fields are the various elements that one can find in a complete BIDS path. Given valid values for these fields, it is possible to build a path (relative to a base path).

Using dataset to create paths for a process
-------------------------------------------

A full path name can be generated given a `Dataset` and metadata values for this dataset (a kind of `dict`). Therefore, the completion algorithm takes some user given metadata values does the following:

For each parameter of type path:
    Identify a dataset for the parameter
    Complete the given metadata with others metadata defined globally for this parameter and dataset schema
    Create a path for the parameter with the completed metadata

Things are not as simple as that when iterations comes into the game. But, let's discover it step by step. The complexity of the path generation framework is hidden in a `ProcessMetadata` class. An instance of this class is created given a process and an execution context. It is a controller whose fields represent all the metadata that are necessary to generate all paths for the process in the given context (execution context is necessary to identify the datasets that are available in the execution environment).


