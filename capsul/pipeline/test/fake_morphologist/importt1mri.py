import os

from soma.controller import Directory, File, Literal, undefined

from capsul.api import Process


class ImportT1MRI(Process):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "importation"

        self.add_field(
            "input",
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
            "output",
            File,
            write=True,
            extensions=[
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
            read=True,
        )
        self.add_field("referential", File, write=True, optional=True, read=True)
        self.add_field(
            "output_database",
            Literal[
                "/host/home/dr144257/data/baseessai",
                "/casa/home/data/baseessai-bids",
                "/home/dr144257/data/archi-sulci",
                "/home/dr144257/data/archi-sulci-sulpat/archi-sulci-2023",
            ],
            optional=True,
        )
        self.output_database = "/host/home/dr144257/data/baseessai"
        self.add_field(
            "attributes_merging",
            Literal["BrainVisa", "header", "selected_from_header"],
            optional=True,
        )
        self.attributes_merging = "BrainVisa"
        self.add_field("selected_attributes_from_header", list, optional=True)
        self.selected_attributes_from_header = []

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
