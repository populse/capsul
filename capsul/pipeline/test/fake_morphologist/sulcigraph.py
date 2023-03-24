# -*- coding: utf-8 -*-

from capsul.api import Process
import os
from soma.controller import File, Directory, undefined, Literal


class SulciGraph(Process):
    def __init__(self, **kwargs):
        super(SulciGraph, self).__init__(**kwargs)
        self.name = "CorticalFoldsGraph"

        self.add_field(
            "skeleton",
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
            "roots",
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
            "grey_white",
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
            "hemi_cortex",
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
            "split_brain",
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
            optional=True,
            write=False,
        )
        self.add_field(
            "white_mesh",
            File,
            read=True,
            allowed_extensions=[".gii", ".mesh", ".obj", ".ply", ".tri"],
            write=False,
        )
        self.add_field(
            "pial_mesh",
            File,
            read=True,
            allowed_extensions=[".gii", ".mesh", ".obj", ".ply", ".tri"],
            write=False,
        )
        self.add_field(
            "commissure_coordinates",
            File,
            read=True,
            allowed_extensions=[".APC"],
            optional=True,
            write=False,
        )
        self.add_field(
            "talairach_transform",
            File,
            read=True,
            allowed_extensions=[".trm"],
            write=False,
        )
        self.add_field("compute_fold_meshes", bool)
        self.compute_fold_meshes = True
        self.add_field("allow_multithreading", bool)
        self.allow_multithreading = True
        self.add_field("graph_version", Literal["3.0", "3.1", "3.2"])
        self.graph_version = "3.1"
        self.add_field(
            "graph", File, write=True, allowed_extensions=[".arg", ".data"], read=True
        )
        self.add_field(
            "sulci_voronoi",
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
            read=True,
        )
        self.add_field("write_cortex_mid_interface", bool)
        self.write_cortex_mid_interface = False
        self.add_field(
            "cortex_mid_interface",
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
            optional=True,
            read=True,
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
