from capsul.api import Process
import os
from soma.controller import File, Directory, undefined, Literal


class normalization_t1_spm12_reinit(Process):
    def __init__(self, **kwargs):
        super(normalization_t1_spm12_reinit, self).__init__(**kwargs)
        self.name = 'normalization_t1_spm12_reinit'

        self.add_field("anatomy_data", File, read=True, extensions=['.nii', '.img', '.hdr'], write=False)
        self.add_field("anatomical_template", File, read=True, extensions=['.nii', '.mnc', '.img', '.hdr'], optional=True, dataset='shared', write=False)
        self.add_field("voxel_size", Literal['[1 1 1]'])
        self.voxel_size = '[1 1 1]'
        self.add_field("cutoff_option", int)
        self.cutoff_option = 25
        self.add_field("nbiteration", int)
        self.nbiteration = 16
        self.add_field("transformations_informations", File, write=True, extensions=['.mat'], read=True)
        self.add_field("normalized_anatomy_data", File, write=True, extensions=['.nii', '.img', '.hdr'], read=True)
        self.add_field("allow_retry_initialization", bool)
        self.allow_retry_initialization = True
        self.add_field("init_translation_origin", Literal[0,1])
        self.init_translation_origin = 0

    def execute(self, context):
        outputs = []
        for field in self.fields():
            name = field.name
            if isinstance(field.type, File):
                if field.write:
                    outputs.append(name)
                    continue
                filename = getattr(self, name, undefined)
                if filename not in (None, undefined, ''):
                    if not os.path.exists(filename):
                        raise ValueError(
                          'Input parameter: %s, file %s does not exist'
                          % (name, repr(filename)))

        for name in outputs:
            field = self.field(name)
            filename = getattr(self, name, undefined)
            if filename not in (None, undefined, ''):
                with open(filename, 'w') as f:
                    f.write('class: %s\n' % self.__class__.__name__)
                    f.write('name: %s\n' % self.name)
                    f.write('parameter: %s\n' % name)
