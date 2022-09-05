# Path generation API

We call path generation the automatic creation of paths values for a process instance. This document describes the path generation system of Capsul.


## General principles

The path generation system is designed to be fully automatic. Path generation must not need any user input except the selection of a few input parameters of the process. This is important to be able to use path generation on iteration of hundreds of executions. 

Path generation is done using metadata and metadata schema. The metadata contains the values that are used to build various part of the path. For instance, the subject code is often used in path names as well as an extension defining the file type. These two values are included in the metadata. There is no single way to create a path given metadata. There are many possible layouts for path names using various metadata. For instance, BrainVISA has defined a path organisation layout. BIDS is another path organisation layout that is the actual standard for neuroimaging. Capsul can support many different systems; each one beign defined in a `MetadataSchema` class (see below).

Metadata given to create a path name can have various origins. For instance, the extension of the file is most often dependent on the process. An image parameter uses an image extension (such as `.nii`) whereas a mesh parameter uses a mesh format (such as `.gii`). This kind of metatada, called process metadata, is defined globally for a process, usually by the process developper. On the other hand, metadata such a subject identifier depends on the usage context of the process. This kind of metadata is called user metadata becaus it is given at runtime as the result of a user action (manual, entry, database selection, etc.).

The path generation system must be able to deal with several metadata schemas for a single process. If not it woul mean that all process parameters must be in the same schema. This is the case if all input and output data are following the BIDS standard. However, in many cases a process will have to deal with several metadata schemas. For instance, there could be one schema for input data (i.e. BIDS), another schema for output data (for use cases not covered by BIDS) and other schemas for third party data (for instance template images in SPM software directory). To support several metadata schema, Capsul make a link between a dataset (i.e. a directory) and the metadata schema used throughout that directory using he `Dataset` class.

### Using path generation

Path generation is done for all path parameters of a process. The following diagram illustrate the case of a process with one `input`parameter supposed to follow BIDS schema and one `output` parameter following another schema called BrainVISA. In oder to use path generation, the user must create a ̀ProcessMetadata` instance that allows to set user metadata for all schemas used by the process. These user metadata are combined with process metadata in order to generate values for all path parameters.

```mermaid
graph LR
    P["Process<br/><code>input</code> → 'bids' schema<br/><code>output</code> → 'brainvisa' schema"]
    -- 1 - create metadata for process -->
    M["ProcessMetadata<br/><code>bids</code> → metadata for bids schema<br/><code>brainvisa</code> → metadata for brainvisa schema"]
    -- 2 - Generate paths --> P
```

## Datasets and relative directory reference

In Capsul, during a process creation, the authors can define how many different datasets the process will use. For instance, a normalization process could be defined with three datasets : one for input data, one for output data and one containing normalization templates. Except the list of datasets, no other information is known about them at process creation time (neither the base path of the dataset nor the schema it uses). Therefore, a process simply defines one name for each dataset it uses. By default, two datasets are defined : ̀input` for input files and `output`for output files. But a processes can define there own dataset symbolic names. For instance `SPM templates` could be used to designate the directory containing the template images bundled with the SPM software. Of course, it is necessary that all processes uses the same symbolic name for a given directory.

To ba able to do something with a dataset name, one must know two things:
* What is the path of the base directory for this dataset ?
* How the file names are organized in this directory ? In other words, what is the metadata schema associated with this dataset.

This information depends on the execution environment. Indeed, the path of a directory that will be used by a process may only be valid on the execution environment. If the user is on a remote computer this path may be invalid on this machine. Therefore, the link between a dataset global name and its actual location and schema is done in Capsul's execution environment configuration. This configuration contains a series of `Dataset` objects making the link between the global name and the base path location as well as the metadata schema. A metadata schema represents the orgranization of the paths within the dataset. For instance their is a metadata schema for BIDS organization. Each metadata schema is a subclass of `MetadataSchema` that derives from `Controller`. A schema contains controller fields describing the metadata that can be used to create a single path. For instance, a BIDS dataset class could be defined as follows:

```
class BIDSSchema(MetadataSchema):
    ''' Metadata schema for BIDS datasets
    '''
    schema_name = 'bids'

    folder: Literal['sourcedata', 'rawdata', 'derivative']
    process: str = None
    sub: str
    ses: str
    data_type: str = None
    task: str = None
    acq: str = None
    ce: str = None
    rec: str = None
    run: str = None
    echo: str = None
    part: str = None
    suffix: str = None
    extension: str

```

The fields are the various elements that one can find in a complete BIDS path. Given valid values for these fields, it is possible to build any valid BIDS paths (relative to a base path).

## Using dataset to create paths for a process

A full path name can be generated given a `Dataset` and metadata values for this dataset (a kind of `dict`). Therefore, the completion algorithm takes some user given metadata values does the following:

For each parameter of type path:
    Identify a dataset for the parameter
    Complete the given metadata with others metadata defined globally for this parameter and dataset schema
    Create a path for the parameter with the completed metadata

Things are not as simple as that when iterations comes into the game. But, let's discover it step by step. The complexity of the path generation framework is hidden in a `ProcessMetadata` class. An instance of this class is created given a process and an execution context. It is a controller whose fields represent all the metadata that are necessary to generate all paths for the process in the given context (execution context is necessary to identify the datasets that are available in the execution environment).
