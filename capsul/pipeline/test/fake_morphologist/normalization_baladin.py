# -*- coding: utf-8 -*-

from capsul.api import Process
import os
import traits.api as traits


class Normalization_Baladin(Process):
    def __init__(self):
        super(Normalization_Baladin, self).__init__()
        self.name = 'Normalization_Baladin'

        self.add_trait("anatomy_data", traits.File(allowed_extensions=['.ima', '.dim'], output=False, optional=False))
        self.add_trait("anatomical_template", traits.File(allowed_extensions=['.ima', '.dim'], output=False, optional=False))
        self.anatomical_template = '/usr/share/fsl/data/standard/MNI152_T1_1mm.nii.gz'
        self.add_trait("transformation_matrix", traits.File(allowed_extensions=['.txt'], output=True, optional=False))
        self.transformation_matrix = ''
        self.add_trait("normalized_anatomy_data", traits.File(allowed_extensions=['.ima', '.dim', '.nii', '.nii.gz'], output=True, optional=False))
        self.normalized_anatomy_data = ''

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
