# -*- coding: utf-8 -*-

from capsul.api import Process
import os
import traits.api as traits


class ScalpMesh(Process):
    def __init__(self):
        super(ScalpMesh, self).__init__()
        self.name = 'ScalpMesh'

        self.add_trait("t1mri_nobias", traits.File(allowed_extensions=['.nii.gz', '.svs', '.bmp', '.dcm', '', '.i', '.v', '.fdf', '.mgh', '.mgz', '.gif', '.ima', '.dim', '.ndpi', '.vms', '.vmu', '.jpg', '.scn', '.mnc', '.mng', '.nii', '.pbm', '.pgm', '.png', '.ppm', '.img', '.hdr', '.svslide', '.tiff', '.tif', '.vimg', '.vinfo', '.vhdr', '.bif', '.xbm', '.xpm', '.czi', '.mnc.gz'], output=False, optional=False, connected_output=True))
        self.add_trait("histo_analysis", traits.File(allowed_extensions=['.han'], optional=True, output=False, connected_output=True))
        self.add_trait("head_mesh", traits.File(allowed_extensions=['.gii', '.mesh', '.obj', '.ply', '.tri'], output=True, optional=False))
        self.head_mesh = ''
        self.add_trait("head_mask", traits.File(allowed_extensions=['.nii.gz', '.bmp', '.dcm', '', '.i', '.v', '.fdf', '.gif', '.ima', '.dim', '.jpg', '.mnc', '.mng', '.nii', '.pbm', '.pgm', '.png', '.ppm', '.img', '.hdr', '.tiff', '.tif', '.vimg', '.vinfo', '.vhdr', '.xbm', '.xpm', '.mnc.gz'], output=True, optional=True))
        self.head_mask = ''
        self.add_trait("keep_head_mask", traits.Bool(output=False, optional=False))
        self.keep_head_mask = False
        self.add_trait("remove_mask", traits.File(allowed_extensions=['.nii.gz', '.svs', '.bmp', '.dcm', '', '.i', '.v', '.fdf', '.mgh', '.mgz', '.gif', '.ima', '.dim', '.ndpi', '.vms', '.vmu', '.jpg', '.scn', '.mnc', '.mng', '.nii', '.pbm', '.pgm', '.png', '.ppm', '.img', '.hdr', '.svslide', '.tiff', '.tif', '.vimg', '.vinfo', '.vhdr', '.bif', '.xbm', '.xpm', '.czi', '.mnc.gz'], optional=True, output=False))
        self.add_trait("first_slice", traits.Int(optional=True, output=False))
        self.add_trait("threshold", traits.Int(optional=True, output=False))
        self.add_trait("closing", traits.Float(optional=True, output=False))
        self.add_trait("threshold_mode", traits.Enum('auto', 'abs', 'grey', output=False, optional=False))
        self.threshold_mode = 'auto'

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
