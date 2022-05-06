# -*- coding: utf-8 -*-

from capsul.api import Process
import os
import traits.api as traits


class TalairachTransformationFromNormalization(Process):
    def __init__(self):
        super(TalairachTransformationFromNormalization, self).__init__()
        self.name = 'TalairachTransformationFromNormalization'

        self.add_trait("normalization_transformation", traits.File(allowed_extensions=['.trm'], output=False, optional=False, connected_output=True))
        self.add_trait("Talairach_transform", traits.File(allowed_extensions=['.trm'], output=True, optional=True))
        self.Talairach_transform = ''
        self.add_trait("commissure_coordinates", traits.File(allowed_extensions=['.APC'], output=True, optional=False))
        self.commissure_coordinates = ''
        self.add_trait("t1mri", traits.File(allowed_extensions=['.nii.gz', '.svs', '.bmp', '.dcm', '', '.i', '.v', '.fdf', '.mgh', '.mgz', '.gif', '.ima', '.dim', '.ndpi', '.vms', '.vmu', '.jpg', '.scn', '.mnc', '.mng', '.nii', '.pbm', '.pgm', '.png', '.ppm', '.img', '.hdr', '.svslide', '.tiff', '.tif', '.vimg', '.vinfo', '.vhdr', '.bif', '.xbm', '.xpm', '.czi', '.mnc.gz'], optional=True, output=False, connected_output=True))
        self.add_trait("source_referential", traits.File(output=False, optional=False))
        self.add_trait("normalized_referential", traits.File(output=False, optional=False))
        self.add_trait("acpc_referential", traits.File(optional=True, output=False))
        self.acpc_referential = '/volatile/riviere/brainvisa/build-stable-qt5/share/brainvisa-share-4.6/registration/Talairach-AC_PC-Anatomist.referential'
        self.add_trait("transform_chain_ACPC_to_Normalized", traits.File(output=False, optional=False))

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
