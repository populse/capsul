# -*- coding: utf-8 -*-

from capsul.api import Process
import os
import traits.api as traits


class AimsConverter(Process):
    def __init__(self):
        super(AimsConverter, self).__init__()
        self.name = 'AimsConverter'

        self.add_trait("read", traits.File(allowed_extensions=['.nii.gz', '.svs', '.bmp', '.dcm', '', '.i', '.v', '.fdf', '.mgh', '.mgz', '.gif', '.ima', '.dim', '.ndpi', '.vms', '.vmu', '.jpg', '.scn', '.mnc', '.mng', '.nii', '.pbm', '.pgm', '.png', '.ppm', '.img', '.hdr', '.svslide', '.tiff', '.tif', '.vimg', '.vinfo', '.vhdr', '.bif', '.xbm', '.xpm', '.czi', '.mnc.gz'], output=False, optional=False))
        self.add_trait("write", traits.File(allowed_extensions=['.nii'], output=True, optional=False))
        self.write = ''
        self.add_trait("preferredFormat", traits.Enum(None, 'gz compressed NIFTI-1 image', 'NIFTI-1 image', 'GIS image', 'MINC image', 'gz compressed MINC image', 'SPM image', 'ECAT v image', 'ECAT i image', 'JPEG image', 'GIF image', 'PNG image', 'MNG image', 'BMP image', 'PBM image', 'PGM image', 'PPM image', 'XBM image', 'XPM image', 'TIFF image', 'TIFF(.tif) image', 'DICOM image', 'Directory', 'FDF image', 'VIDA image', optional=True, output=False))
        self.preferredFormat = None
        self.add_trait("removeSource", traits.Bool(output=False, optional=True))
        self.removeSource = False
        self.add_trait("ascii", traits.Bool(output=False, optional=True))
        self.ascii = False
        self.add_trait("voxelType", traits.Enum(None, 'U8', 'S8', 'U16', 'S16', 'U32', 'S32', 'FLOAT', 'DOUBLE', 'RGB', 'RGBA', 'HSV', optional=True, output=False))
        self.voxelType = None
        self.add_trait("rescaleDynamic", traits.Bool(output=False, optional=True))
        self.rescaleDynamic = False
        self.add_trait("useInputTypeLimits", traits.Bool(output=False, optional=True))
        self.useInputTypeLimits = False
        self.add_trait("inputDynamicMin", traits.Float(optional=True, output=False))
        self.add_trait("inputDynamicMax", traits.Float(optional=True, output=False))
        self.add_trait("outputDynamicMin", traits.Float(optional=True, output=False))
        self.add_trait("outputDynamicMax", traits.Float(optional=True, output=False))

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
