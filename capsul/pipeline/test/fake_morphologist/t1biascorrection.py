# -*- coding: utf-8 -*-

from capsul.api import Process
import os
import traits.api as traits


class T1BiasCorrection(Process):
    def __init__(self):
        super(T1BiasCorrection, self).__init__()
        self.name = 'T1BiasCorrection'

        self.add_trait("t1mri", traits.File(allowed_extensions=['.nii.gz', '.svs', '.bmp', '.dcm', '', '.i', '.v', '.fdf', '.mgh', '.mgz', '.gif', '.ima', '.dim', '.ndpi', '.vms', '.vmu', '.jpg', '.scn', '.mnc', '.mng', '.nii', '.pbm', '.pgm', '.png', '.ppm', '.img', '.hdr', '.svslide', '.tiff', '.tif', '.vimg', '.vinfo', '.vhdr', '.bif', '.xbm', '.xpm', '.czi', '.mnc.gz'], output=False, optional=False, connected_output=True))
        self.add_trait("commissure_coordinates", traits.File(allowed_extensions=['.APC'], optional=True, output=False, connected_output=True))
        self.add_trait("sampling", traits.Float(output=False, optional=False))
        self.sampling = 16.0
        self.add_trait("field_rigidity", traits.Float(output=False, optional=False))
        self.field_rigidity = 20.0
        self.add_trait("zdir_multiply_regul", traits.Float(output=False, optional=False))
        self.zdir_multiply_regul = 0.5
        self.add_trait("wridges_weight", traits.Float(output=False, optional=False))
        self.wridges_weight = 20.0
        self.add_trait("ngrid", traits.Int(output=False, optional=False))
        self.ngrid = 2
        self.add_trait("delete_last_n_slices", traits.Str(output=False, optional=False))
        self.delete_last_n_slices = 'auto (AC/PC Points needed)'
        self.add_trait("t1mri_nobias", traits.File(allowed_extensions=['.nii.gz', '.bmp', '.dcm', '', '.i', '.v', '.fdf', '.gif', '.ima', '.dim', '.jpg', '.mnc', '.mng', '.nii', '.pbm', '.pgm', '.png', '.ppm', '.img', '.hdr', '.tiff', '.tif', '.vimg', '.vinfo', '.vhdr', '.xbm', '.xpm', '.mnc.gz'], output=True, optional=False))
        self.t1mri_nobias = ''
        self.add_trait("mode", traits.Enum('write_minimal', 'write_all', 'delete_useless', 'write_minimal without correction', output=False, optional=False))
        self.mode = 'write_minimal'
        self.add_trait("write_field", traits.Enum('yes', 'no', output=False, optional=False))
        self.write_field = 'no'
        self.add_trait("field", traits.File(allowed_extensions=['.nii.gz', '.bmp', '.dcm', '', '.i', '.v', '.fdf', '.gif', '.ima', '.dim', '.jpg', '.mnc', '.mng', '.nii', '.pbm', '.pgm', '.png', '.ppm', '.img', '.hdr', '.tiff', '.tif', '.vimg', '.vinfo', '.vhdr', '.xbm', '.xpm', '.mnc.gz'], output=True, optional=True))
        self.field = ''
        self.add_trait("write_hfiltered", traits.Enum('yes', 'no', output=False, optional=False))
        self.write_hfiltered = 'yes'
        self.add_trait("hfiltered", traits.File(allowed_extensions=['.nii.gz', '.bmp', '.dcm', '', '.i', '.v', '.fdf', '.gif', '.ima', '.dim', '.jpg', '.mnc', '.mng', '.nii', '.pbm', '.pgm', '.png', '.ppm', '.img', '.hdr', '.tiff', '.tif', '.vimg', '.vinfo', '.vhdr', '.xbm', '.xpm', '.mnc.gz'], output=True, optional=False))
        self.hfiltered = ''
        self.add_trait("write_wridges", traits.Enum('yes', 'no', 'read', output=False, optional=False))
        self.write_wridges = 'yes'
        self.add_trait("white_ridges", traits.File(allowed_extensions=['.nii.gz', '.bmp', '.dcm', '', '.i', '.v', '.fdf', '.gif', '.ima', '.dim', '.jpg', '.mnc', '.mng', '.nii', '.pbm', '.pgm', '.png', '.ppm', '.img', '.hdr', '.tiff', '.tif', '.vimg', '.vinfo', '.vhdr', '.xbm', '.xpm', '.mnc.gz'], output=True, optional=False))
        self.white_ridges = ''
        self.add_trait("variance_fraction", traits.Int(output=False, optional=False))
        self.variance_fraction = 75
        self.add_trait("write_variance", traits.Enum('yes', 'no', output=False, optional=False))
        self.write_variance = 'yes'
        self.add_trait("variance", traits.File(allowed_extensions=['.nii.gz', '.bmp', '.dcm', '', '.i', '.v', '.fdf', '.gif', '.ima', '.dim', '.jpg', '.mnc', '.mng', '.nii', '.pbm', '.pgm', '.png', '.ppm', '.img', '.hdr', '.tiff', '.tif', '.vimg', '.vinfo', '.vhdr', '.xbm', '.xpm', '.mnc.gz'], output=True, optional=False))
        self.variance = ''
        self.add_trait("edge_mask", traits.Enum('yes', 'no', output=False, optional=False))
        self.edge_mask = 'yes'
        self.add_trait("write_edges", traits.Enum('yes', 'no', output=False, optional=False))
        self.write_edges = 'yes'
        self.add_trait("edges", traits.File(allowed_extensions=['.nii.gz', '.bmp', '.dcm', '', '.i', '.v', '.fdf', '.gif', '.ima', '.dim', '.jpg', '.mnc', '.mng', '.nii', '.pbm', '.pgm', '.png', '.ppm', '.img', '.hdr', '.tiff', '.tif', '.vimg', '.vinfo', '.vhdr', '.xbm', '.xpm', '.mnc.gz'], output=True, optional=False))
        self.edges = ''
        self.add_trait("write_meancurvature", traits.Enum('yes', 'no', output=False, optional=False))
        self.write_meancurvature = 'no'
        self.add_trait("meancurvature", traits.File(allowed_extensions=['.nii.gz', '.bmp', '.dcm', '', '.i', '.v', '.fdf', '.gif', '.ima', '.dim', '.jpg', '.mnc', '.mng', '.nii', '.pbm', '.pgm', '.png', '.ppm', '.img', '.hdr', '.tiff', '.tif', '.vimg', '.vinfo', '.vhdr', '.xbm', '.xpm', '.mnc.gz'], output=True, optional=True))
        self.meancurvature = ''
        self.add_trait("fix_random_seed", traits.Bool(output=False, optional=False))
        self.fix_random_seed = False
        self.add_trait("modality", traits.Enum('T1', 'T2', output=False, optional=False))
        self.modality = 'T1'
        self.add_trait("use_existing_ridges", traits.Bool(output=False, optional=False))
        self.use_existing_ridges = False

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
