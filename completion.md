Path generation API
===================

We call path generation the automatic creation of paths values for a process instance. This document describes the path generation system of Capsul.


General principles
------------------

The path generation system is designed to be fully automatic. Path generation must not need any user input except the selection of a few input parameters of the process. This is important to be able to use path generation on iteration of hundreds of executions. 

Path generation is done using metadata and metadata schema. The metadata contains the values that are used to build various part of the path. For instance, the subject code is often used in path names as well as an extension defining the file type. These two values are included in the metadata. There is no single way to create a path given metadata. There are many possible layouts for path names using various metadata. For instance, BrainVISA has defined a path organisation layout. BIDS is another path organisation layout that is the actual standard for neuroimaging. Capsul can support many different systems; each one beign defined in a `MetadataSchema` class (see below).

Metadata given to create a path name can have various origins. For instance, the extension of the file is most often dependent on the process. An image parameter uses an image extension (such as `.nii`) whereas a mesh parameter uses a mesh format (such as `.gii`). This kind of metatada, called process metadata, is defined globally for a process, usually by the process developper. On the other hand, metadata such a subject identifier depends on the usage context of the process. This kind of metadata is called user metadata becaus it is given at runtime as the result of a user action (manual, entry, database selection, etc.).

The path generation system must be able to deal with several metadata schemas for a single process. If not it woul mean that all process parameters must be in the same schema. This is the case if all input and output data are following the BIDS standard. However, in many cases a process will have to deal with several metadata schemas. For instance, there could be one schema for input data (i.e. BIDS), another schema for output data (for use cases not covered by BIDS) and other schemas for third party data (for instance template images in SPM software directory). To support several metadata schema, Capsul make a link between a dataset (i.e. a directory) and the metadata schema used throughout that directory using he `Dataset` class.

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
