# -*- coding: utf-8 -*-

from capsul.api import Process
import os
import traits.api as traits


class normalization_t1_spm8_reinit(Process):
    def __init__(self):
        super(normalization_t1_spm8_reinit, self).__init__()
        self.name = 'normalization_t1_spm8_reinit'

        self.add_trait("anatomy_data", traits.File(allowed_extensions=['.nii', '.img', '.hdr'], output=False, optional=False, connected_output=True))
        self.add_trait("anatomical_template", traits.File(allowed_extensions=['.nii', '.mnc', '.img', '.hdr'], optional=True, output=False))
        self.anatomical_template = '/i2bm/local/spm8/templates/T1.nii'
        self.add_trait("voxel_size", traits.Enum('[1 1 1]', output=False, optional=False))
        self.voxel_size = '[1 1 1]'
        self.add_trait("cutoff_option", traits.Int(output=False, optional=False))
        self.cutoff_option = 25
        self.add_trait("nbiteration", traits.Int(output=False, optional=False))
        self.nbiteration = 16
        self.add_trait("transformations_informations", traits.File(allowed_extensions=['.mat'], output=True, optional=False))
        self.transformations_informations = ''
        self.add_trait("normalized_anatomy_data", traits.File(allowed_extensions=['.nii', '.img', '.hdr'], output=True, optional=False))
        self.normalized_anatomy_data = ''
        self.add_trait("allow_retry_initialization", traits.Bool(output=False, optional=False))
        self.allow_retry_initialization = True
        self.add_trait("init_translation_origin", traits.Enum(0, 1, output=False, optional=False))
        self.init_translation_origin = 0

    def _run_process(self):
        outputs = []
        for name, trait in self.user_traits().items():
            if isinstance(trait.trait_type, traits.File):
                if trait.output:
                    outputs.append(name)
                    continue
                filename = getattr(self, name)
                if filename not in (None, traits.Undefined, ''):
                    if not os.path.exists(filename):
                        raise ValueError(
                          'Input parameter: %s, file %s does not exist'
                          % (name, repr(filename)))

        for name in outputs:
            trait = self.trait(name)
            filename = getattr(self, name)
            if filename not in (None, traits.Undefined, ''):
                with open(filename, 'w') as f:
                    f.write('class: %s\n' % self.__class__.__name__)
                    f.write('name: %s\n' % self.name)
                    f.write('parameter: %s\n' % name)
