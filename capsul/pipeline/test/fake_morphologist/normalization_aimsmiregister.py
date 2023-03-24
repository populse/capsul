# -*- coding: utf-8 -*-

from capsul.api import Process
import os
from soma.controller import File, Directory, undefined, Literal


class normalization_aimsmiregister(Process):
    def __init__(self, **kwargs):
        super(normalization_aimsmiregister, self).__init__(**kwargs)
        self.name = "Normalization_AimsMIRegister"

        self.add_field(
            "anatomy_data",
            File,
            read=True,
            allowed_extensions=[
                ".nii.gz",
                ".svs",
                ".bmp",
                ".dcm",
                "",
                ".i",
                ".v",
                ".fdf",
                ".mgh",
                ".mgz",
                ".gif",
                ".ima",
                ".dim",
                ".ndpi",
                ".vms",
                ".vmu",
                ".jpg",
                ".scn",
                ".mnc",
                ".nii",
                ".pbm",
                ".pgm",
                ".png",
                ".ppm",
                ".img",
                ".hdr",
                ".svslide",
                ".tiff",
                ".tif",
                ".vimg",
                ".vinfo",
                ".vhdr",
                ".bif",
                ".xbm",
                ".xpm",
                ".czi",
                ".mnc.gz",
            ],
            write=False,
        )
        self.add_field(
            "anatomical_template",
            File,
            read=True,
            allowed_extensions=[
                ".nii.gz",
                ".svs",
                ".bmp",
                ".dcm",
                "",
                ".i",
                ".v",
                ".fdf",
                ".mgh",
                ".mgz",
                ".gif",
                ".ima",
                ".dim",
                ".ndpi",
                ".vms",
                ".vmu",
                ".jpg",
                ".scn",
                ".mnc",
                ".nii",
                ".pbm",
                ".pgm",
                ".png",
                ".ppm",
                ".img",
                ".hdr",
                ".svslide",
                ".tiff",
                ".tif",
                ".vimg",
                ".vinfo",
                ".vhdr",
                ".bif",
                ".xbm",
                ".xpm",
                ".czi",
                ".mnc.gz",
            ],
            write=False,
        )
        self.anatomical_template = "/casa/host/build/share/brainvisa-share-5.1/anatomical_templates/MNI152_T1_2mm.nii.gz"
        self.add_field(
            "transformation_to_template",
            File,
            write=True,
            allowed_extensions=[".trm"],
            optional=True,
            read=True,
        )
        self.add_field(
            "normalized_anatomy_data",
            File,
            write=True,
            allowed_extensions=[
                ".nii.gz",
                ".bmp",
                ".dcm",
                "",
                ".i",
                ".v",
                ".fdf",
                ".gif",
                ".ima",
                ".dim",
                ".jpg",
                ".mnc",
                ".nii",
                ".pbm",
                ".pgm",
                ".png",
                ".ppm",
                ".img",
                ".hdr",
                ".tiff",
                ".tif",
                ".vimg",
                ".vinfo",
                ".vhdr",
                ".xbm",
                ".xpm",
                ".mnc.gz",
            ],
            optional=False,
            read=True,
        )
        self.add_field(
            "transformation_to_MNI",
            File,
            write=True,
            allowed_extensions=[".trm"],
            optional=False,
            read=True,
        )
        self.add_field(
            "transformation_to_ACPC",
            File,
            write=True,
            allowed_extensions=[".trm"],
            optional=True,
            read=True,
        )
        self.add_field(
            "mni_to_acpc",
            File,
            read=True,
            allowed_extensions=[".trm"],
            optional=True,
            write=False,
        )
        self.mni_to_acpc = "/casa/host/build/share/brainvisa-share-5.1/transformation/talairach_TO_spm_template_novoxels.trm"
        self.add_field("smoothing", float)
        self.smoothing = 1.0

    def execute(self, context):
        outputs = []
        for field in self.fields():
            name = field.name
            if isinstance(field.type, File):
                if field.write:
                    outputs.append(name)
                    continue
                filename = getattr(self, name, undefined)
                if filename not in (None, undefined, ""):
                    if not os.path.exists(filename):
                        raise ValueError(
                            "Input parameter: %s, file %s does not exist"
                            % (name, repr(filename))
                        )

        for name in outputs:
            field = self.field(name)
            filename = getattr(self, name, undefined)
            if filename not in (None, undefined, ""):
                with open(filename, "w") as f:
                    f.write("class: %s\n" % self.__class__.__name__)
                    f.write("name: %s\n" % self.name)
                    f.write("parameter: %s\n" % name)
