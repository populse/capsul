# -*- coding: utf-8 -*-

from capsul.api import Process
import os
from soma.controller import File, Directory, undefined, Literal
import pydantic


class AcpcOrientation(Process):
    def __init__(self, **kwargs):
        super(AcpcOrientation, self).__init__(**kwargs)
        self.name = 'StandardACPC'

        self.add_field("T1mri", File, read=True, allowed_extensions=['.nii.gz', '.svs', '.bmp', '.dcm', '', '.i', '.v', '.fdf', '.mgh', '.mgz', '.gif', '.ima', '.dim', '.ndpi', '.vms', '.vmu', '.jpg', '.scn', '.mnc', '.nii', '.pbm', '.pgm', '.png', '.ppm', '.img', '.hdr', '.svslide', '.tiff', '.tif', '.vimg', '.vinfo', '.vhdr', '.bif', '.xbm', '.xpm', '.czi', '.mnc.gz'], write=False)
        self.add_field("commissure_coordinates", File, write=True, allowed_extensions=['.APC'], read=True)
        self.add_field("Normalised", Literal['No','MNI from SPM','MNI from Mritotal','Marseille from SPM'])
        self.Normalised = 'No'
        self.add_field("Anterior_Commissure", pydantic.conlist(float, min_items=3, max_items=3), optional=True)
        self.Anterior_Commissure = [0.0, 0.0, 0.0]
        self.add_field("Posterior_Commissure", pydantic.conlist(float, min_items=3, max_items=3), optional=True)
        self.Posterior_Commissure = [0.0, 0.0, 0.0]
        self.add_field("Interhemispheric_Point", pydantic.conlist(float, min_items=3, max_items=3), optional=True)
        self.Interhemispheric_Point = [0.0, 0.0, 0.0]
        self.add_field("Left_Hemisphere_Point", pydantic.conlist(float, min_items=3, max_items=3), optional=True)
        self.Left_Hemisphere_Point = [0.0, 0.0, 0.0]
        self.add_field("allow_flip_initial_MRI", bool)
        self.allow_flip_initial_MRI = False
        self.add_field("reoriented_t1mri", File, write=True, allowed_extensions=['.nii.gz', '.bmp', '.dcm', '', '.i', '.v', '.fdf', '.gif', '.ima', '.dim', '.jpg', '.mnc', '.nii', '.pbm', '.pgm', '.png', '.ppm', '.img', '.hdr', '.tiff', '.tif', '.vimg', '.vinfo', '.vhdr', '.xbm', '.xpm', '.mnc.gz'], read=True)
        self.add_field("remove_older_MNI_normalization", bool)
        self.remove_older_MNI_normalization = True
        self.add_field("older_MNI_normalization", File, read=True, allowed_extensions=['.trm'], optional=True, write=False)

    def execute(self, context):
        outputs = []
        for field in self.fields():
            name = field.name
            if isinstance(field.type, File):
                if field.write:
                    outputs.append(name)
                    continue
                filename = getattr(self, name, undefined)
                if filename not in (None, undefined, ''):
                    if not os.path.exists(filename):
                        raise ValueError(
                          'Input parameter: %s, file %s does not exist'
                          % (name, repr(filename)))

        for name in outputs:
            field = self.field(name)
            filename = getattr(self, name, undefined)
            if filename not in (None, undefined, ''):
                with open(filename, 'w') as f:
                    f.write('class: %s\n' % self.__class__.__name__)
                    f.write('name: %s\n' % self.name)
                    f.write('parameter: %s\n' % name)
