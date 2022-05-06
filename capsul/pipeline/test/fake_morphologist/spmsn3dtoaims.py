# -*- coding: utf-8 -*-

from capsul.api import Process
import os
import traits.api as traits


class SPMsn3dToAims(Process):
    def __init__(self):
        super(SPMsn3dToAims, self).__init__()
        self.name = 'SPMsn3dToAims'

        self.add_trait("read", traits.File(allowed_extensions=['.mat'], output=False, optional=False, connected_output=False))
        self.add_trait("write", traits.File(allowed_extensions=['.trm'], output=True, optional=False))
        self.write = ''
        self.add_trait("target", traits.Enum('MNI template', 'unspecified template', 'normalized_volume in AIMS orientation', output=False, optional=False))
        self.target = 'MNI template'
        self.add_trait("source_volume", traits.File(allowed_extensions=['.nii', '.img', '.hdr'], optional=True, output=False))
        self.add_trait("normalized_volume", traits.File(allowed_extensions=['.nii', '.img', '.hdr'], optional=True, output=False))
        self.add_trait("removeSource", traits.Bool(output=False, optional=False))
        self.removeSource = False

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
