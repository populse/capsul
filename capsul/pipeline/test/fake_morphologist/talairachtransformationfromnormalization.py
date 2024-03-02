import os

from soma.controller import Directory, File, Literal, undefined

from capsul.api import Process


class TalairachTransformationFromNormalization(Process):
    def __init__(self, **kwargs):
        super(TalairachTransformationFromNormalization, self).__init__(**kwargs)
        self.name = "TalairachFromNormalization"

        self.add_field(
            "normalization_transformation",
            File,
            read=True,
            extensions=[".trm"],
            write=False,
        )
        self.add_field(
            "Talairach_transform",
            File,
            write=True,
            extensions=[".trm"],
            read=True,
            optional=True,
        )
        self.add_field(
            "commissure_coordinates",
            File,
            write=True,
            extensions=[".APC"],
            optional=False,
            read=True,
        )
        self.add_field(
            "t1mri",
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
            optional=True,
            write=False,
        )
        self.add_field("source_referential", File, read=True, write=False)
        self.add_field(
            "normalized_referential", File, read=True, dataset="shared", write=False
        )
        self.add_field(
            "acpc_referential",
            File,
            read=True,
            optional=True,
            dataset="shared",
            write=False,
        )
        self.acpc_referential = "/casa/host/build/share/brainvisa-share-5.2/registration/Talairach-AC_PC-Anatomist.referential"
        self.add_field(
            "transform_chain_ACPC_to_Normalized",
            File,
            dataset="shared",
            read=True,
            write=False,
        )

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
