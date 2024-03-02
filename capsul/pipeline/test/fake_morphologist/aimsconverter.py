import os

from soma.controller import Directory, File, Literal, undefined

from capsul.api import Process


class AimsConverter(Process):
    def __init__(self, **kwargs):
        super(AimsConverter, self).__init__(**kwargs)
        self.name = "converter"

        self.add_field(
            "read",
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
        self.add_field(
            "write", File, write=True, extensions=[".nii"], read=True, optional=False
        )
        self.add_field(
            "preferredFormat",
            Literal[
                None,
                "gz compressed NIFTI-1 image",
                "NIFTI-1 image",
                "GIS image",
                "MINC image",
                "gz compressed MINC image",
                "SPM image",
                "ECAT v image",
                "ECAT i image",
                "JPEG image",
                "GIF image",
                "PNG image",
                "BMP image",
                "PBM image",
                "PGM image",
                "PPM image",
                "XBM image",
                "XPM image",
                "TIFF image",
                "TIFF(.tif) image",
                "DICOM image",
                "Directory",
                "FDF image",
                "VIDA image",
            ],
            optional=True,
        )
        self.add_field("removeSource", bool, optional=True)
        self.removeSource = False
        self.add_field("ascii", bool, optional=True)
        self.ascii = False
        self.add_field(
            "voxelType",
            Literal[
                None,
                "U8",
                "S8",
                "U16",
                "S16",
                "U32",
                "S32",
                "FLOAT",
                "DOUBLE",
                "RGB",
                "RGBA",
                "HSV",
            ],
            optional=True,
        )
        self.add_field("rescaleDynamic", bool, optional=True)
        self.rescaleDynamic = False
        self.add_field("useInputTypeLimits", bool, optional=True)
        self.useInputTypeLimits = False
        self.add_field("inputDynamicMin", float, optional=True)
        self.add_field("inputDynamicMax", float, optional=True)
        self.add_field("outputDynamicMin", float, optional=True)
        self.add_field("outputDynamicMax", float, optional=True)

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
