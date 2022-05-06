# -*- coding: utf-8 -*-

from capsul.api import Process
import os
import traits.api as traits


class BaladinNormalizationToAims(Process):
    def __init__(self):
        super(BaladinNormalizationToAims, self).__init__()
        self.name = 'BaladinNormalizationToAims'

        self.add_trait("read", traits.File(allowed_extensions=['.txt'], output=False, optional=False, connected_output=True))
        self.add_trait("source_volume", traits.File(allowed_extensions=['.nii.gz', '.svs', '.bmp', '.dcm', '', '.i', '.v', '.fdf', '.mgh', '.mgz', '.gif', '.ima', '.dim', '.ndpi', '.vms', '.vmu', '.jpg', '.scn', '.mnc', '.mng', '.nii', '.pbm', '.pgm', '.png', '.ppm', '.img', '.hdr', '.svslide', '.tiff', '.tif', '.vimg', '.vinfo', '.vhdr', '.bif', '.xbm', '.xpm', '.czi', '.mnc.gz'], output=False, optional=False))
        self.add_trait("write", traits.File(allowed_extensions=['.trm'], output=True, optional=False))
        self.write = ''
        self.add_trait("registered_volume", traits.File(allowed_extensions=['.nii.gz', '.svs', '.bmp', '.dcm', '', '.i', '.v', '.fdf', '.mgh', '.mgz', '.gif', '.ima', '.dim', '.ndpi', '.vms', '.vmu', '.jpg', '.scn', '.mnc', '.mng', '.nii', '.pbm', '.pgm', '.png', '.ppm', '.img', '.hdr', '.svslide', '.tiff', '.tif', '.vimg', '.vinfo', '.vhdr', '.bif', '.xbm', '.xpm', '.czi', '.mnc.gz'], optional=True, output=False))
        self.registered_volume = '/usr/share/fsl/data/standard/MNI152_T1_1mm.nii.gz'
        self.add_trait("set_transformation_in_source_volume", traits.Bool(output=False, optional=False))
        self.set_transformation_in_source_volume = True

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
