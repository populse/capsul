# -*- coding: utf-8 -*-

from capsul.api import Process
import os
from soma.controller import File, Directory, undefined, Literal


class FSLnormalizationToAims(Process):
    def __init__(self, **kwargs):
        super(FSLnormalizationToAims, self).__init__(**kwargs)
        self.name = "ConvertFSLnormalizationToAIMS"

        self.add_field("read", File, read=True, extensions=[".mat"], write=False)
        self.add_field(
            "source_volume",
            File,
            read=True,
            extensions=[
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
        self.add_field("write", File, write=True, extensions=[".trm"], read=True)
        self.add_field(
            "registered_volume",
            File,
            read=True,
            extensions=[".nii", ".nii.gz"],
            write=False,
        )
        self.add_field("standard_template", Literal[0, 1, 2])
        self.standard_template = 0
        self.add_field("set_transformation_in_source_volume", bool)
        self.set_transformation_in_source_volume = True

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
