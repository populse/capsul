# -*- coding: utf-8 -*-

from capsul.api import Process
import os
from soma.controller import File, Directory, undefined, Literal


class T1BiasCorrection(Process):
    def __init__(self, **kwargs):
        super(T1BiasCorrection, self).__init__(**kwargs)
        self.name = "BiasCorrection"

        self.add_field(
            "t1mri",
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
            "commissure_coordinates",
            File,
            read=True,
            allowed_extensions=[".APC"],
            optional=True,
            write=False,
        )
        self.add_field("sampling", float)
        self.sampling = 16.0
        self.add_field("field_rigidity", float)
        self.field_rigidity = 20.0
        self.add_field("zdir_multiply_regul", float)
        self.zdir_multiply_regul = 0.5
        self.add_field("wridges_weight", float)
        self.wridges_weight = 20.0
        self.add_field("ngrid", int)
        self.ngrid = 2
        self.add_field("background_threshold_auto", Literal["no", "corners", "otsu"])
        self.background_threshold_auto = "corners"
        self.add_field(
            "delete_last_n_slices",
            str,
            trait="",
            default_value="auto (AC/PC Points needed)",
        )
        self.delete_last_n_slices = "auto (AC/PC Points needed)"
        self.add_field(
            "t1mri_nobias",
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
        self.add_field(
            "mode",
            Literal[
                "write_minimal",
                "write_all",
                "delete_useless",
                "write_minimal without correction",
            ],
        )
        self.mode = "write_minimal"
        self.add_field("write_field", Literal["yes", "no"])
        self.write_field = "no"
        self.add_field(
            "b_field",
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
        self.add_field("write_hfiltered", Literal["yes", "no"])
        self.write_hfiltered = "yes"
        self.add_field(
            "hfiltered",
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
        self.add_field("write_wridges", Literal["yes", "no", "read"])
        self.write_wridges = "yes"
        self.add_field(
            "white_ridges",
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
        self.add_field("variance_fraction", int)
        self.variance_fraction = 75
        self.add_field("write_variance", Literal["yes", "no"])
        self.write_variance = "yes"
        self.add_field(
            "variance",
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
        self.add_field("edge_mask", Literal["yes", "no"])
        self.edge_mask = "yes"
        self.add_field("write_edges", Literal["yes", "no"])
        self.write_edges = "yes"
        self.add_field(
            "edges",
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
        self.add_field("write_meancurvature", Literal["yes", "no"])
        self.write_meancurvature = "no"
        self.add_field(
            "meancurvature",
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
        self.add_field("fix_random_seed", bool)
        self.fix_random_seed = False
        self.add_field("modality", Literal["T1", "T2"])
        self.modality = "T1"
        self.add_field("use_existing_ridges", bool)
        self.use_existing_ridges = False

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
