# -*- coding: utf-8 -*-

from capsul.api import Process
import os
import traits.api as traits


class ReorientAnatomy(Process):
    def __init__(self):
        super(ReorientAnatomy, self).__init__()
        self.name = 'ReorientAnatomy'

        self.add_trait("t1mri", traits.File(allowed_extensions=['.nii.gz', '.svs', '.bmp', '.dcm', '', '.i', '.v', '.fdf', '.mgh', '.mgz', '.gif', '.ima', '.dim', '.ndpi', '.vms', '.vmu', '.jpg', '.scn', '.mnc', '.mng', '.nii', '.pbm', '.pgm', '.png', '.ppm', '.img', '.hdr', '.svslide', '.tiff', '.tif', '.vimg', '.vinfo', '.vhdr', '.bif', '.xbm', '.xpm', '.czi', '.mnc.gz'], output=False, optional=False))
        self.add_trait("output_t1mri", traits.File(allowed_extensions=['.nii.gz', '.bmp', '.dcm', '', '.i', '.v', '.fdf', '.gif', '.ima', '.dim', '.jpg', '.mnc', '.mng', '.nii', '.pbm', '.pgm', '.png', '.ppm', '.img', '.hdr', '.tiff', '.tif', '.vimg', '.vinfo', '.vhdr', '.xbm', '.xpm', '.mnc.gz'], output=True, optional=False))
        self.output_t1mri = ''
        self.add_trait("transformation", traits.File(allowed_extensions=['.trm'], output=False, optional=False, connected_output=True))
        self.add_trait("output_transformation", traits.File(allowed_extensions=['.trm'], output=True, optional=False))
        self.output_transformation = ''
        self.add_trait("commissures_coordinates", traits.File(allowed_extensions=['.APC'], optional=True, output=False))
        self.add_trait("output_commissures_coordinates", traits.File(allowed_extensions=['.APC'], output=True, optional=True))
        self.output_commissures_coordinates = ''
        self.add_trait("allow_flip_initial_MRI", traits.Bool(output=False, optional=False))
        self.allow_flip_initial_MRI = False

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
