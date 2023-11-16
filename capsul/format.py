from soma.controller import Controller

"""
Management of formats and format lists. A format is the association
between a label (i.e. a string value) and a list of path extensions.
A named formats list is an association between a label and a list of formats.

These formats and lists are managed by a FormatsManager object. A
global instance of such a manager can be obtainer using global_formats()
function.

For instance one can register a new image format with extension '*.raw'
using the following code:

from capsul.format import global_formats
gf = global_formats()
gf["Raw image format"] = ["raw"]

Creating a new named format list containing BrainVISA image formats
and this raw format can be done like this:

pri = gf.new_format_list("Possibly raw image")
pri.extend(gf.formats("BrainVISA image formats"))
pri.append(gf["Raw image format"])
"""


class Format(Controller):
    """A single named format"""

    label: str
    extensions: list[str]


class NamedFormatList(list):
    """A named list for formats"""

    def __init__(self, label, formats):
        super().__init__()
        self.label = label
        self.extend(formats)


class FormatsManager:
    """Manage formats and named format lists"""

    def __init__(self):
        self._formats = {}
        self._format_lists = {}

    def __setitem__(self, label, value):
        """
        Adds a new fromat. Label is the format name that is displayed to
        the user. It must be unique among all format labels independently
        of character case. value is a list of extensions or a format object.
        """
        if isinstance(value, list):
            format = Format(label=label, extensions=value)
            key = label.lower()
        elif isinstance(value, Format):
            format = value
            key = format.label.lower()
        else:
            raise ValueError(f"Invalid format definition: {repr(value)}")
        f = self._formats.get(key)
        if f:
            raise KeyError(
                f'Cannot create format "{label}" because format "{f.label}" already exists.'
            )
        self._formats[key] = format

    def __getitem__(self, label_or_key):
        """
        Return a Format instance from its label. Research is case independent.
        A KeyError is raised if the fomat is not found.
        """
        return self._formats[label_or_key.lower()]

    def get(self, label_or_key, default=None):
        """
        Return a Format instance from its label. Research is case independent.
        The default value is returned if the format is not found.
        """
        return self._formats.get(label_or_key.lower(), default)

    def update(self, formats_dict):
        """
        Import formats and format lists from a dictionary.
        The dictionary can contain two sub-dictionaries:
        - "formats": whose keys are format labels and keys
                     are lists of extensions.
        - "format_lists": whose keys are format list labels
                          and keys are list of format keys
                          (i.e. case independent format names).
        """
        for label, extensions in formats_dict["formats"].items():
            self[label] = extensions
        for label, formats in formats_dict["format_lists"].items():
            l = []
            for format in formats:
                f = self.get(format)
                if f is None:
                    raise KeyError(f"Unknown format: {format}")
                l.append(f)
            key = label.lower()
            self._format_lists[key] = NamedFormatList(label, l)

    def formats(self, label_of_key, default=None):
        """
        Return the format list with the given label (case independent).
        """
        return self._format_lists.get(label_of_key.lower(), default)

    def new_format_list(self, label):
        """Create a new empty format list"""
        key = label.lower()
        l = self._format_lists.get(key)
        if l:
            raise ValueError(
                f'Cannot create format list "{label}" because list "{f.label}" already exists.'
            )
        result = self._format_lists[key] = NamedFormatList(label, [])
        return result


_global_formats = None


def global_formats():
    """
    Return the global instance of FormatsManager. This object
    is created on first call.
    """
    global _global_formats
    if _global_formats is None:
        _global_formats = FormatsManager()
        _global_formats.update(
            {
                "formats": {
                    "Graph and data": ["arg", "data"],
                    "Matlab script": ["m"],
                    "Matlab file": ["mat"],
                    "gz Matlab file": ["mat.gz"],
                    "bz2 Matlab file": ["mat.bz2"],
                    "GIS image": ["ima", "dim"],
                    "Z compressed GIS image": ["ima.Z", "dim.Z"],
                    "gz compressed GIS image": ["ima.gz", "dim.gz"],
                    "VIDA image": ["vimg", "vinfo", "vhdr"],
                    "Z compressed VIDA image": ["vimg.Z", "vinfo.Z", "vhdr.Z"],
                    "gz compressed VIDA image": ["vimg.gz", "vinfo.gz", "vhdr.gz"],
                    "Phase image": ["pm"],
                    "SPM image": ["img", "hdr"],
                    "Z compressed SPM image": ["img.Z", "hdr.Z"],
                    "gz compressed SPM image": ["img.gz", "hdr.gz"],
                    "ECAT v image": ["v"],
                    "Z compressed ECAT v image": ["v.Z"],
                    "gz compressed ECAT v image": ["v.gz"],
                    "ECAT i image": ["i"],
                    "Z compressed ECAT i image": ["i.Z"],
                    "gz compressed ECAT i image": ["i.gz"],
                    "DICOM image": ["dcm"],
                    "MINC image": ["mnc"],
                    "gz compressed MINC image": ["mnc.gz"],
                    "FDF image": ["fdf"],
                    "NIFTI-1 image": ["nii"],
                    "gz compressed NIFTI-1 image": ["nii.gz"],
                    "FreesurferMGZ": ["mgz"],
                    "FreesurferMGH": ["mgh"],
                    "TRI mesh": ["tri"],
                    "Z compressed TRI mesh": ["tri.Z"],
                    "gz compressed TRI mesh": ["tri.gz"],
                    "MESH mesh": ["mesh"],
                    "Z compressed MESH mesh": ["mesh.Z"],
                    "gz compressed MESH mesh": ["mesh.gz"],
                    "PLY mesh": ["ply"],
                    "Z compressed PLY mesh": ["ply.Z"],
                    "gz compressed PLY mesh": ["ply.gz"],
                    "GIFTI file": ["gii"],
                    "Z compressed GIFTI file": ["gii.Z"],
                    "gz compressed GIFTI file": ["gii.gz"],
                    "MNI OBJ mesh": ["obj"],
                    "Z compressed MNI OBJ mesh": ["obj.Z"],
                    "gz compressed MNI OBJ mesh": ["obj.gz"],
                    "Texture": ["tex"],
                    "Z compressed Texture": ["tex.Z"],
                    "gz compressed Texture": ["tex.gz"],
                    "Moment Vector": ["inv"],
                    "Transformation matrix": ["trm"],
                    "MINC transformation matrix": ["xfm"],
                    "Config file": ["cfg"],
                    "Hierarchy": ["hie"],
                    "Tree": ["tree"],
                    "BrainVISA/Anatomist animation": ["banim"],
                    "MPEG film": ["mpg"],
                    "MP4 film": ["mp4"],
                    "AVI film": ["avi"],
                    "OGG film": ["ogg"],
                    "QuickTime film": ["mov"],
                    "JPEG image": ["jpg"],
                    "GIF image": ["gif"],
                    "PNG image": ["png"],
                    "MNG image": ["mng"],
                    "BMP image": ["bmp"],
                    "PBM image": ["pbm"],
                    "PGM image": ["pgm"],
                    "PPM image": ["ppm"],
                    "XBM image": ["xbm"],
                    "XPM image": ["xpm"],
                    "TIFF image": ["tiff"],
                    "TIFF(.tif) image": ["tif"],
                    "Text file": ["txt"],
                    "CSV file": ["csv"],
                    "JSON file": ["json"],
                    "ASCII results": ["asc"],
                    "XML": ["xml"],
                    "gzipped XML": ["xml.gz"],
                    "Info file": ["info"],
                    "ZIP file": ["zip"],
                    "SVG file": ["svg"],
                    "XLS file": ["xls"],
                    "XLSX file": ["xlsx"],
                    "PS file": ["ps"],
                    "EPS file": ["eps"],
                    "gz compressed PS file": ["ps.gz"],
                    "Log file": ["log"],
                    "pickle file": ["pickle"],
                    "Database Cache file": ["fsd"],
                    "SQLite Database File": ["sqlite"],
                    "HDF5 File": ["h5"],
                    "Python Script": ["py"],
                    "gz compressed TAR archive": ["tar.gz"],
                    "Aims scalar features": ["features"],
                    "Bucket": ["bck"],
                    "mdsm file": ["mdsm"],
                    "Selection": ["sel"],
                    "Text Data Table": ["dat"],
                    "Minf": ["minf"],
                    "HTML": ["html"],
                    "PDF File": ["pdf"],
                    "Soma-Workflow workflow": ["workflow"],
                    "Bval File": ["bval"],
                    "Bvec File": ["bvec"],
                    "Label Translation": ["trl"],
                    "DEF Label Translation": ["def"],
                    "Numpy Array": ["npy"],
                    "Aims bundles": ["bundles", "bundlesdata"],
                    "Trackvis tracts": ["trk"],
                    "Mrtrix tracts": ["tck"],
                    "Bundle Selection Rules": ["brules"],
                    "Referential": ["referential"],
                    "Commissure coordinates": ["APC"],
                    "Histogram": ["his"],
                    "Histo Analysis": ["han"],
                    "Gyri Model": ["gyr"],
                    "Aperio svs": ["svs"],
                    "Hamamatsu vms": ["vms"],
                    "Hamamatsu vmu": ["vmu"],
                    "Hamamatsu ndpi": ["ndpi"],
                    "Leica scn": ["scn"],
                    "MIRAX mrxs": ["mrxs"],
                    "Sakura svslide": ["svslide"],
                    "Ventana bif": ["bif"],
                    "Zeiss czi": ["czi"],
                    "Sparse Matrix": ["imas"],
                    "FreesurferPial": ["pial"],
                    "FreesurferWhite": ["white"],
                    "FreesurferSphereReg": ["sphere.reg"],
                    "FreesurferThickness": ["thickness"],
                    "FreesurferCurv": ["curv"],
                    "FreesurferAvgCurv": ["avg_curv"],
                    "FreesurferCurvPial": ["curv.pial"],
                    "FreesurferParcellation": ["annot"],
                    "FreesurferIsin": ["isin"],
                    "FreesurferLabel": ["label"],
                    "siRelax Fold Energy": ["nrj"],
                    "Sigraph Learner": ["lrn"],
                    "SVM classifier": ["svm"],
                    "MLP classifier": ["net"],
                    "SNNS pattern": ["pat"],
                    "Template model": ["mod"],
                    "Template model domain": ["dom"],
                    "Process execution event": ["bvproc"],
                    "BrainVISA session event": ["bvsession"],
                    "Quality Check Report": ["qcreport"],
                    "Plot results": ["fig"],
                },
                "format_lists": {
                    "anatomist volume formats": [
                        "gz compressed NIFTI-1 image",
                        "NIFTI-1 image",
                        "GIS image",
                        "MINC image",
                        "gz compressed MINC image",
                        "SPM image",
                        "ECAT v image",
                        "ECAT i image",
                        "FreesurferMGZ",
                        "FreesurferMGH",
                        "Z compressed VIDA image",
                        "gz compressed VIDA image",
                        "Z compressed SPM image",
                        "gz compressed SPM image",
                        "Z compressed ECAT v image",
                        "gz compressed ECAT v image",
                        "Z compressed ECAT i image",
                        "gz compressed ECAT i image",
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
                        "FDF image",
                        "VIDA image",
                        "gz compressed GIS image",
                        "Z compressed GIS image",
                    ],
                    "aims readable volume formats": [
                        "gz compressed NIFTI-1 image",
                        "NIFTI-1 image",
                        "GIS image",
                        "MINC image",
                        "gz compressed MINC image",
                        "SPM image",
                        "ECAT v image",
                        "ECAT i image",
                        "FreesurferMGZ",
                        "FreesurferMGH",
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
                        "FDF image",
                        "VIDA image",
                        "TIFF image",
                        "TIFF(.tif) image",
                        "Aperio svs",
                        "Hamamatsu vms",
                        "Hamamatsu vmu",
                        "Leica scn",
                        "Hamamatsu ndpi",
                        "Sakura svslide",
                        "Ventana bif",
                        "Zeiss czi",
                    ],
                    "aims writable volume formats": [
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
                        "FDF image",
                        "VIDA image",
                    ],
                    "aims image formats": [
                        "JPEG image",
                        "GIF image",
                        "PNG image",
                        "MNG image",
                        "BMP image",
                        "PBM image",
                        "PGM image",
                        "PPM image",
                        "XBM image",
                        "XPM image",
                        "TIFF image",
                        "TIFF(.tif) image",
                    ],
                    "anatomist mesh formats": [
                        "GIFTI file",
                        "MESH mesh",
                        "TRI mesh",
                        "Z compressed MESH mesh",
                        "gz compressed MESH mesh",
                        "Z compressed TRI mesh",
                        "gz compressed TRI mesh",
                        "PLY mesh",
                        "Z compressed PLY mesh",
                        "gz compressed PLY mesh",
                        "Z compressed GIFTI file",
                        "gz compressed GIFTI file",
                        "MNI OBJ mesh",
                        "Z compressed MNI OBJ mesh",
                        "gz compressed MNI OBJ mesh",
                        "Z compressed GIFTI file",
                        "gz compressed GIFTI file",
                    ],
                    "aims mesh formats": [
                        "GIFTI file",
                        "MESH mesh",
                        "TRI mesh",
                        "PLY mesh",
                        "MNI OBJ mesh",
                    ],
                    "aims texture formats": ["GIFTI file", "Texture"],
                    "anatomist texture formats": [
                        "GIFTI file",
                        "Z compressed GIFTI file",
                        "gz compressed GIFTI file",
                        "Texture",
                        "Z compressed Texture",
                        "Z compressed GIFTI file",
                        "gz compressed GIFTI file",
                        "gz compressed Texture",
                    ],
                    "html pdf": ["HTML", "PDF File"],
                    "brainvisa volume formats": [
                        "gz compressed NIFTI-1 image",
                        "NIFTI-1 image",
                        "GIS image",
                        "MINC image",
                        "gz compressed MINC image",
                        "SPM image",
                        "ECAT v image",
                        "ECAT i image",
                        "FreesurferMGZ",
                        "FreesurferMGH",
                        "Z compressed VIDA image",
                        "gz compressed VIDA image",
                        "Z compressed SPM image",
                        "gz compressed SPM image",
                        "Z compressed ECAT v image",
                        "gz compressed ECAT v image",
                        "Z compressed ECAT i image",
                        "gz compressed ECAT i image",
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
                        "FDF image",
                        "VIDA image",
                        "gz compressed GIS image",
                        "Z compressed GIS image",
                    ],
                    "brainvisa image formats": [
                        "JPEG image",
                        "GIF image",
                        "PNG image",
                        "MNG image",
                        "BMP image",
                        "PBM image",
                        "PGM image",
                        "PPM image",
                        "XBM image",
                        "XPM image",
                        "TIFF image",
                        "TIFF(.tif) image",
                    ],
                    "brainvisa mesh formats": [
                        "GIFTI file",
                        "MESH mesh",
                        "TRI mesh",
                        "Z compressed MESH mesh",
                        "gz compressed MESH mesh",
                        "Z compressed TRI mesh",
                        "gz compressed TRI mesh",
                        "PLY mesh",
                        "Z compressed PLY mesh",
                        "gz compressed PLY mesh",
                        "Z compressed GIFTI file",
                        "gz compressed GIFTI file",
                        "MNI OBJ mesh",
                        "Z compressed MNI OBJ mesh",
                        "gz compressed MNI OBJ mesh",
                        "Z compressed GIFTI file",
                        "gz compressed GIFTI file",
                    ],
                    "brainvisa texture formats": [
                        "GIFTI file",
                        "Z compressed GIFTI file",
                        "gz compressed GIFTI file",
                        "Texture",
                        "Z compressed Texture",
                        "Z compressed GIFTI file",
                        "gz compressed GIFTI file",
                        "gz compressed Texture",
                    ],
                    "aims readable bundles formats": [
                        "Aims bundles",
                        "Trackvis tracts",
                        "Mrtrix tracts",
                    ],
                    "aims writable bundles formats": ["Aims bundles"],
                    "ants volume formats": [
                        "gz compressed NIFTI-1 image",
                        "NIFTI-1 image",
                        "gz compressed SPM image",
                        "SPM image",
                    ],
                    "ants linear transformation": ["Matlab file"],
                    "ants elastic transformation": [
                        "gz compressed NIFTI-1 image",
                        "NIFTI-1 image",
                        "gz compressed SPM image",
                        "SPM image",
                    ],
                    "ants transformation": [
                        "Matlab file",
                        "gz compressed NIFTI-1 image",
                        "NIFTI-1 image",
                        "gz compressed SPM image",
                        "SPM image",
                    ],
                    "aims partialy writable volume formats": [
                        "GIS image",
                        "NIFTI-1 image",
                    ],
                    "aims partialy readable volume formats": [
                        "GIS image",
                        "NIFTI-1 image",
                        "TIFF image",
                        "TIFF(.tif) image",
                        "Aperio svs",
                        "Hamamatsu vms",
                        "Hamamatsu vmu",
                        "Leica scn",
                        "Hamamatsu ndpi",
                        "Sakura svslide",
                        "Ventana bif",
                        "Zeiss czi",
                    ],
                    "openslide": [
                        "TIFF image",
                        "TIFF(.tif) image",
                        "Aperio svs",
                        "Hamamatsu vms",
                        "Hamamatsu vmu",
                        "Leica scn",
                        "Hamamatsu ndpi",
                        "Sakura svslide",
                        "Ventana bif",
                        "Zeiss czi",
                    ],
                    "virtual microscopy formats": [
                        "TIFF image",
                        "TIFF(.tif) image",
                        "Aperio svs",
                        "Hamamatsu vms",
                        "Hamamatsu vmu",
                        "Leica scn",
                        "Hamamatsu ndpi",
                        "Sakura svslide",
                        "Ventana bif",
                        "Zeiss czi",
                    ],
                    "multi resolution formats": [
                        "TIFF image",
                        "TIFF(.tif) image",
                        "Aperio svs",
                        "Hamamatsu vms",
                        "Hamamatsu vmu",
                        "Leica scn",
                        "Hamamatsu ndpi",
                        "Sakura svslide",
                        "Ventana bif",
                        "Zeiss czi",
                    ],
                    "biology 2d image formats": [
                        "TIFF image",
                        "TIFF(.tif) image",
                        "JPEG image",
                        "GIS image",
                    ],
                    "biology 3d volume formats": [
                        "TIFF image",
                        "TIFF(.tif) image",
                        "JPEG image",
                        "GIS image",
                    ],
                    "aims matrix formats": [
                        "gz compressed NIFTI-1 image",
                        "NIFTI-1 image",
                        "GIS image",
                    ],
                },
            }
        )
    return _global_formats
