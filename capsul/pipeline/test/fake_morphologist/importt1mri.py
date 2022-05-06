# -*- coding: utf-8 -*-

from capsul.api import Process
import os
import traits.api as traits


class ImportT1MRI(Process):
    def __init__(self):
        super(ImportT1MRI, self).__init__()
        self.name = 'ImportT1MRI'

        self.add_trait("input", traits.File(allowed_extensions=['.nii.gz', '.svs', '.bmp', '.dcm', '', '.i', '.v', '.fdf', '.mgh', '.mgz', '.gif', '.ima', '.dim', '.ndpi', '.vms', '.vmu', '.jpg', '.scn', '.mnc', '.mng', '.nii', '.pbm', '.pgm', '.png', '.ppm', '.img', '.hdr', '.svslide', '.tiff', '.tif', '.vimg', '.vinfo', '.vhdr', '.bif', '.xbm', '.xpm', '.czi', '.mnc.gz'], output=False, optional=False))
        self.add_trait("output", traits.File(allowed_extensions=['.nii.gz', '.bmp', '.dcm', '', '.i', '.v', '.fdf', '.gif', '.ima', '.dim', '.jpg', '.mnc', '.mng', '.nii', '.pbm', '.pgm', '.png', '.ppm', '.img', '.hdr', '.tiff', '.tif', '.vimg', '.vinfo', '.vhdr', '.xbm', '.xpm', '.mnc.gz'], output=True, optional=False))
        self.output = ''
        self.add_trait("referential", traits.File(output=True, optional=True))
        self.referential = ''
        self.add_trait("output_database", traits.Enum('/neurospin/lnao/PClean/database_learnclean', '/volatile/riviere/basetests-3.1.0', output=False, optional=False))
        self.output_database = '/neurospin/lnao/PClean/database_learnclean'
        self.add_trait("attributes_merging", traits.Enum('BrainVisa', 'header', 'selected_from_header', output=False, optional=False))
        self.attributes_merging = 'BrainVisa'
        self.add_trait("selected_attributes_from_header", traits.List(traits.Any(), copy='deep', output=False, optional=False))
        self.selected_attributes_from_header = []

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
