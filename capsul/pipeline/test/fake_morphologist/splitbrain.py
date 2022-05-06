# -*- coding: utf-8 -*-

from capsul.api import Process
import os
import traits.api as traits


class SplitBrain(Process):
    def __init__(self):
        super(SplitBrain, self).__init__()
        self.name = 'SplitBrain'

        self.add_trait("brain_mask", traits.File(allowed_extensions=['.nii.gz', '.svs', '.bmp', '.dcm', '', '.i', '.v', '.fdf', '.mgh', '.mgz', '.gif', '.ima', '.dim', '.ndpi', '.vms', '.vmu', '.jpg', '.scn', '.mnc', '.mng', '.nii', '.pbm', '.pgm', '.png', '.ppm', '.img', '.hdr', '.svslide', '.tiff', '.tif', '.vimg', '.vinfo', '.vhdr', '.bif', '.xbm', '.xpm', '.czi', '.mnc.gz'], output=False, optional=False, connected_output=True))
        self.add_trait("t1mri_nobias", traits.File(allowed_extensions=['.nii.gz', '.svs', '.bmp', '.dcm', '', '.i', '.v', '.fdf', '.mgh', '.mgz', '.gif', '.ima', '.dim', '.ndpi', '.vms', '.vmu', '.jpg', '.scn', '.mnc', '.mng', '.nii', '.pbm', '.pgm', '.png', '.ppm', '.img', '.hdr', '.svslide', '.tiff', '.tif', '.vimg', '.vinfo', '.vhdr', '.bif', '.xbm', '.xpm', '.czi', '.mnc.gz'], output=False, optional=False, connected_output=True))
        self.add_trait("histo_analysis", traits.File(allowed_extensions=['.han'], output=False, optional=False, connected_output=True))
        self.add_trait("commissure_coordinates", traits.File(allowed_extensions=['.APC'], optional=True, output=False, connected_output=False))
        self.add_trait("use_ridges", traits.Bool(output=False, optional=False))
        self.use_ridges = True
        self.add_trait("white_ridges", traits.File(allowed_extensions=['.nii.gz', '.svs', '.bmp', '.dcm', '', '.i', '.v', '.fdf', '.mgh', '.mgz', '.gif', '.ima', '.dim', '.ndpi', '.vms', '.vmu', '.jpg', '.scn', '.mnc', '.mng', '.nii', '.pbm', '.pgm', '.png', '.ppm', '.img', '.hdr', '.svslide', '.tiff', '.tif', '.vimg', '.vinfo', '.vhdr', '.bif', '.xbm', '.xpm', '.czi', '.mnc.gz'], output=False, optional=False, connected_output=True))
        self.add_trait("use_template", traits.Bool(output=False, optional=False))
        self.use_template = True
        self.add_trait("split_template", traits.File(allowed_extensions=['.nii.gz', '.svs', '.bmp', '.dcm', '', '.i', '.v', '.fdf', '.mgh', '.mgz', '.gif', '.ima', '.dim', '.ndpi', '.vms', '.vmu', '.jpg', '.scn', '.mnc', '.mng', '.nii', '.pbm', '.pgm', '.png', '.ppm', '.img', '.hdr', '.svslide', '.tiff', '.tif', '.vimg', '.vinfo', '.vhdr', '.bif', '.xbm', '.xpm', '.czi', '.mnc.gz'], output=False, optional=False))
        self.split_template = '/volatile/riviere/brainvisa/build-stable-qt5/share/brainvisa-share-4.6/hemitemplate/closedvoronoi.ima'
        self.add_trait("mode", traits.Enum('Watershed (2011)', 'Voronoi', output=False, optional=False))
        self.mode = 'Watershed (2011)'
        self.add_trait("variant", traits.Enum('regularized', 'GW Barycentre', 'WM Standard Deviation', output=False, optional=False))
        self.variant = 'GW Barycentre'
        self.add_trait("bary_factor", traits.Enum(0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, output=False, optional=False))
        self.bary_factor = 0.6
        self.add_trait("mult_factor", traits.Enum(0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, optional=True, output=False))
        self.mult_factor = 2
        self.add_trait("initial_erosion", traits.Float(output=False, optional=False))
        self.initial_erosion = 2.0
        self.add_trait("cc_min_size", traits.Int(output=False, optional=False))
        self.cc_min_size = 500
        self.add_trait("split_brain", traits.File(allowed_extensions=['.nii.gz', '.bmp', '.dcm', '', '.i', '.v', '.fdf', '.gif', '.ima', '.dim', '.jpg', '.mnc', '.mng', '.nii', '.pbm', '.pgm', '.png', '.ppm', '.img', '.hdr', '.tiff', '.tif', '.vimg', '.vinfo', '.vhdr', '.xbm', '.xpm', '.mnc.gz'], output=True, optional=False))
        self.split_brain = ''
        self.add_trait("fix_random_seed", traits.Bool(output=False, optional=False))
        self.fix_random_seed = False

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
