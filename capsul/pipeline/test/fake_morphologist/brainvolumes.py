# -*- coding: utf-8 -*-

from capsul.api import Process
import os
from soma.controller import File, Directory, undefined, Literal


class brainvolumes(Process):
    def __init__(self, **kwargs):
        super(brainvolumes, self).__init__(**kwargs)
        self.name = 'GlobalMorphometry'

        self.add_field("split_brain", File, read=True, extensions=['.nii.gz', '.svs', '.bmp', '.dcm', '', '.i', '.v', '.fdf', '.mgh', '.mgz', '.gif', '.ima', '.dim', '.ndpi', '.vms', '.vmu', '.jpg', '.scn', '.mnc', '.nii', '.pbm', '.pgm', '.png', '.ppm', '.img', '.hdr', '.svslide', '.tiff', '.tif', '.vimg', '.vinfo', '.vhdr', '.bif', '.xbm', '.xpm', '.czi', '.mnc.gz'], write=False)
        self.add_field("left_grey_white", File, read=True, extensions=['.nii.gz', '.svs', '.bmp', '.dcm', '', '.i', '.v', '.fdf', '.mgh', '.mgz', '.gif', '.ima', '.dim', '.ndpi', '.vms', '.vmu', '.jpg', '.scn', '.mnc', '.nii', '.pbm', '.pgm', '.png', '.ppm', '.img', '.hdr', '.svslide', '.tiff', '.tif', '.vimg', '.vinfo', '.vhdr', '.bif', '.xbm', '.xpm', '.czi', '.mnc.gz'], write=False)
        self.add_field("right_grey_white", File, read=True, extensions=['.nii.gz', '.svs', '.bmp', '.dcm', '', '.i', '.v', '.fdf', '.mgh', '.mgz', '.gif', '.ima', '.dim', '.ndpi', '.vms', '.vmu', '.jpg', '.scn', '.mnc', '.nii', '.pbm', '.pgm', '.png', '.ppm', '.img', '.hdr', '.svslide', '.tiff', '.tif', '.vimg', '.vinfo', '.vhdr', '.bif', '.xbm', '.xpm', '.czi', '.mnc.gz'], write=False)
        self.add_field("left_csf", File, write=True, extensions=['.nii.gz', '.bmp', '.dcm', '', '.i', '.v', '.fdf', '.gif', '.ima', '.dim', '.jpg', '.mnc', '.nii', '.pbm', '.pgm', '.png', '.ppm', '.img', '.hdr', '.tiff', '.tif', '.vimg', '.vinfo', '.vhdr', '.xbm', '.xpm', '.mnc.gz'], read=True)
        self.add_field("right_csf", File, write=True, extensions=['.nii.gz', '.bmp', '.dcm', '', '.i', '.v', '.fdf', '.gif', '.ima', '.dim', '.jpg', '.mnc', '.nii', '.pbm', '.pgm', '.png', '.ppm', '.img', '.hdr', '.tiff', '.tif', '.vimg', '.vinfo', '.vhdr', '.xbm', '.xpm', '.mnc.gz'], read=True)
        self.add_field("left_labelled_graph", File, read=True, extensions=['.arg', '.data'], optional=True, write=False)
        self.add_field("right_labelled_graph", File, read=True, extensions=['.arg', '.data'], optional=True, write=False)
        self.add_field("left_gm_mesh", File, read=True, extensions=['.gii', '.mesh', '.obj', '.ply', '.tri'], optional=True, write=False)
        self.add_field("right_gm_mesh", File, read=True, extensions=['.gii', '.mesh', '.obj', '.ply', '.tri'], optional=True, write=False)
        self.add_field("left_wm_mesh", File, read=True, extensions=['.gii', '.mesh', '.obj', '.ply', '.tri'], optional=True, write=False)
        self.add_field("right_wm_mesh", File, read=True, extensions=['.gii', '.mesh', '.obj', '.ply', '.tri'], optional=True, write=False)
        self.add_field("subject", str, dataset='output')
        self.add_field("sulci_label_attribute", str)
        self.sulci_label_attribute = 'label'
        self.add_field("table_format", Literal['2023','old'])
        self.table_format = '2023'
        self.add_field("brain_volumes_file", File, write=True, extensions=['.csv'], read=True)

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
