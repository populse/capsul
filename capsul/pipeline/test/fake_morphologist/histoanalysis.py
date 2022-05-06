# -*- coding: utf-8 -*-

from capsul.api import Process
import os
import traits.api as traits


class HistoAnalysis(Process):
    def __init__(self):
        super(HistoAnalysis, self).__init__()
        self.name = 'HistoAnalysis'

        self.add_trait("t1mri_nobias", traits.File(allowed_extensions=['.nii.gz', '.svs', '.bmp', '.dcm', '', '.i', '.v', '.fdf', '.mgh', '.mgz', '.gif', '.ima', '.dim', '.ndpi', '.vms', '.vmu', '.jpg', '.scn', '.mnc', '.mng', '.nii', '.pbm', '.pgm', '.png', '.ppm', '.img', '.hdr', '.svslide', '.tiff', '.tif', '.vimg', '.vinfo', '.vhdr', '.bif', '.xbm', '.xpm', '.czi', '.mnc.gz'], output=False, optional=False, connected_output=True))
        self.add_trait("use_hfiltered", traits.Bool(output=False, optional=False))
        self.use_hfiltered = True
        self.add_trait("hfiltered", traits.File(allowed_extensions=['.nii.gz', '.svs', '.bmp', '.dcm', '', '.i', '.v', '.fdf', '.mgh', '.mgz', '.gif', '.ima', '.dim', '.ndpi', '.vms', '.vmu', '.jpg', '.scn', '.mnc', '.mng', '.nii', '.pbm', '.pgm', '.png', '.ppm', '.img', '.hdr', '.svslide', '.tiff', '.tif', '.vimg', '.vinfo', '.vhdr', '.bif', '.xbm', '.xpm', '.czi', '.mnc.gz'], optional=True, output=False, connected_output=True))
        self.add_trait("use_wridges", traits.Bool(output=False, optional=False))
        self.use_wridges = True
        self.add_trait("white_ridges", traits.File(allowed_extensions=['.nii.gz', '.svs', '.bmp', '.dcm', '', '.i', '.v', '.fdf', '.mgh', '.mgz', '.gif', '.ima', '.dim', '.ndpi', '.vms', '.vmu', '.jpg', '.scn', '.mnc', '.mng', '.nii', '.pbm', '.pgm', '.png', '.ppm', '.img', '.hdr', '.svslide', '.tiff', '.tif', '.vimg', '.vinfo', '.vhdr', '.bif', '.xbm', '.xpm', '.czi', '.mnc.gz'], optional=True, output=False, connected_output=True))
        self.add_trait("undersampling", traits.Enum('2', '4', '8', '16', '32', 'auto', 'iteration', output=False, optional=False))
        self.undersampling = 'iteration'
        self.add_trait("histo_analysis", traits.File(allowed_extensions=['.han'], output=True, optional=False))
        self.histo_analysis = ''
        self.add_trait("histo", traits.File(output=True, optional=False))
        self.histo = ''
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
