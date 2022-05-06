# -*- coding: utf-8 -*-

from capsul.api import Process
import os
import traits.api as traits


class Normalization_FSL_reinit(Process):
    def __init__(self):
        super(Normalization_FSL_reinit, self).__init__()
        self.name = 'Normalization_FSL_reinit'

        self.add_trait("anatomy_data", traits.File(allowed_extensions=['.nii', '.nii.gz'], output=False, optional=False, connected_output=True))
        self.add_trait("anatomical_template", traits.File(allowed_extensions=['.nii', '.nii.gz'], output=False, optional=False))
        self.anatomical_template = '/usr/share/fsl/data/standard/MNI152_T1_2mm_brain.nii.gz'
        self.add_trait("Alignment", traits.Enum('Already Virtually Aligned', 'Not Aligned but Same Orientation', 'Incorrectly Oriented', output=False, optional=False))
        self.Alignment = 'Not Aligned but Same Orientation'
        self.add_trait("transformation_matrix", traits.File(allowed_extensions=['.mat'], output=True, optional=False))
        self.transformation_matrix = ''
        self.add_trait("normalized_anatomy_data", traits.File(allowed_extensions=['.nii.gz'], output=True, optional=False))
        self.normalized_anatomy_data = ''
        self.add_trait("cost_function", traits.Enum('corratio', 'mutualinfo', 'normcorr', 'normmi', 'leastsq', 'labeldiff', output=False, optional=False))
        self.cost_function = 'corratio'
        self.add_trait("search_cost_function", traits.Enum('corratio', 'mutualinfo', 'normcorr', 'normmi', 'leastsq', 'labeldiff', output=False, optional=False))
        self.search_cost_function = 'corratio'
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
