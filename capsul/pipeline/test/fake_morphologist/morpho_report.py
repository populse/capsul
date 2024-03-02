import os

from soma.controller import Directory, File, Literal, undefined

from capsul.api import Process


class morpho_report(Process):
    def __init__(self, **kwargs):
        super(morpho_report, self).__init__(**kwargs)
        self.name = "Report"

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
            write=False,
        )
        self.add_field(
            "left_grey_white",
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
        self.add_field(
            "right_grey_white",
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
        self.add_field(
            "left_gm_mesh",
            File,
            read=True,
            extensions=[".gii", ".mesh", ".obj", ".ply", ".tri"],
            optional=True,
            write=False,
        )
        self.add_field(
            "right_gm_mesh",
            File,
            read=True,
            extensions=[".gii", ".mesh", ".obj", ".ply", ".tri"],
            optional=True,
            write=False,
        )
        self.add_field(
            "left_wm_mesh",
            File,
            read=True,
            extensions=[".gii", ".mesh", ".obj", ".ply", ".tri"],
            optional=True,
            write=False,
        )
        self.add_field(
            "right_wm_mesh",
            File,
            read=True,
            extensions=[".gii", ".mesh", ".obj", ".ply", ".tri"],
            optional=True,
            write=False,
        )
        self.add_field(
            "left_labelled_graph",
            File,
            read=True,
            extensions=[".arg", ".data"],
            optional=True,
            write=False,
        )
        self.add_field(
            "right_labelled_graph",
            File,
            read=True,
            extensions=[".arg", ".data"],
            optional=True,
            write=False,
        )
        self.add_field(
            "talairach_transform",
            File,
            read=True,
            extensions=[".trm"],
            optional=True,
            write=False,
        )
        self.add_field(
            "brain_volumes_file",
            File,
            read=True,
            extensions=[".csv"],
            optional=True,
            write=False,
        )
        self.add_field(
            "normative_brain_stats",
            File,
            read=True,
            extensions=[".json"],
            optional=True,
            dataset=None,
            write=False,
        )
        self.add_field("report", File, write=True, extensions=[".pdf"], read=True)
        self.add_field("subject", str, dataset="output")

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
