# -*- coding: utf-8 -*-

from capsul.api import Process
import os
import traits.api as traits


class AcpcOrientation(Process):
    def __init__(self):
        super(AcpcOrientation, self).__init__()
        self.name = 'AcpcOrientation'

        self.add_trait("T1mri", traits.File(allowed_extensions=['.nii.gz', '.svs', '.bmp', '.dcm', '', '.i', '.v', '.fdf', '.mgh', '.mgz', '.gif', '.ima', '.dim', '.ndpi', '.vms', '.vmu', '.jpg', '.scn', '.mnc', '.mng', '.nii', '.pbm', '.pgm', '.png', '.ppm', '.img', '.hdr', '.svslide', '.tiff', '.tif', '.vimg', '.vinfo', '.vhdr', '.bif', '.xbm', '.xpm', '.czi', '.mnc.gz'], output=False, optional=False))
        self.add_trait("commissure_coordinates", traits.File(allowed_extensions=['.APC'], output=True, optional=False))
        self.commissure_coordinates = ''
        self.add_trait("Normalised", traits.Enum('No', 'MNI from SPM', 'MNI from Mritotal', 'Marseille from SPM', output=False, optional=False))
        self.Normalised = 'No'
        self.add_trait("Anterior_Commissure", traits.List(traits.Float(), optional=True, copy='deep', output=False))
        self.Anterior_Commissure = [0.0, 0.0, 0.0]
        self.add_trait("Posterior_Commissure", traits.List(traits.Float(), optional=True, copy='deep', output=False))
        self.Posterior_Commissure = [0.0, 0.0, 0.0]
        self.add_trait("Interhemispheric_Point", traits.List(traits.Float(), optional=True, copy='deep', output=False))
        self.Interhemispheric_Point = [0.0, 0.0, 0.0]
        self.add_trait("Left_Hemisphere_Point", traits.List(traits.Float(), optional=True, copy='deep', output=False))
        self.Left_Hemisphere_Point = [0.0, 0.0, 0.0]
        self.add_trait("allow_flip_initial_MRI", traits.Bool(output=False, optional=False))
        self.allow_flip_initial_MRI = False
        self.add_trait("reoriented_t1mri", traits.File(allowed_extensions=['.nii.gz', '.bmp', '.dcm', '', '.i', '.v', '.fdf', '.gif', '.ima', '.dim', '.jpg', '.mnc', '.mng', '.nii', '.pbm', '.pgm', '.png', '.ppm', '.img', '.hdr', '.tiff', '.tif', '.vimg', '.vinfo', '.vhdr', '.xbm', '.xpm', '.mnc.gz'], output=True, optional=False))
        self.reoriented_t1mri = ''
        self.add_trait("remove_older_MNI_normalization", traits.Bool(output=False, optional=False))
        self.remove_older_MNI_normalization = True
        self.add_trait("older_MNI_normalization", traits.File(allowed_extensions=['.trm'], optional=True, output=False))

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
