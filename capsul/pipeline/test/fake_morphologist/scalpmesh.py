from capsul.api import Process
import os
from soma.controller import File, Directory, undefined, Literal


class ScalpMesh(Process):
    def __init__(self, **kwargs):
        super(ScalpMesh, self).__init__(**kwargs)
        self.name = 'HeadMesh'

        self.add_field("t1mri_nobias", File, read=True, extensions=['.nii.gz', '.svs', '.bmp', '.dcm', '', '.i', '.v', '.fdf', '.mgh', '.mgz', '.gif', '.ima', '.dim', '.ndpi', '.vms', '.vmu', '.jpg', '.scn', '.mnc', '.nii', '.pbm', '.pgm', '.png', '.ppm', '.img', '.hdr', '.svslide', '.tiff', '.tif', '.vimg', '.vinfo', '.vhdr', '.bif', '.xbm', '.xpm', '.czi', '.mnc.gz'], write=False)
        self.add_field("histo_analysis", File, read=True, extensions=['.han'], optional=True, write=False)
        self.add_field("head_mesh", File, write=True, extensions=['.gii', '.mesh', '.obj', '.ply', '.tri'], read=True)
        self.add_field("head_mask", File, write=True, extensions=['.nii.gz', '.bmp', '.dcm', '', '.i', '.v', '.fdf', '.gif', '.ima', '.dim', '.jpg', '.mnc', '.nii', '.pbm', '.pgm', '.png', '.ppm', '.img', '.hdr', '.tiff', '.tif', '.vimg', '.vinfo', '.vhdr', '.xbm', '.xpm', '.mnc.gz'], optional=True, read=True)
        self.add_field("keep_head_mask", bool)
        self.keep_head_mask = False
        self.add_field("remove_mask", File, read=True, extensions=['.nii.gz', '.svs', '.bmp', '.dcm', '', '.i', '.v', '.fdf', '.mgh', '.mgz', '.gif', '.ima', '.dim', '.ndpi', '.vms', '.vmu', '.jpg', '.scn', '.mnc', '.nii', '.pbm', '.pgm', '.png', '.ppm', '.img', '.hdr', '.svslide', '.tiff', '.tif', '.vimg', '.vinfo', '.vhdr', '.bif', '.xbm', '.xpm', '.czi', '.mnc.gz'], optional=True, dataset=None, write=False)
        self.add_field("first_slice", int, optional=True)
        self.add_field("threshold", int, optional=True)
        self.add_field("closing", float, optional=True)
        self.add_field("threshold_mode", Literal['auto','abs','grey'])
        self.threshold_mode = 'auto'

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
