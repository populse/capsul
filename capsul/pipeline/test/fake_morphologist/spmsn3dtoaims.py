# -*- coding: utf-8 -*-

from capsul.api import Process
import os
from soma.controller import File, Directory, undefined, Literal


class SPMsn3dToAims(Process):
    def __init__(self, **kwargs):
        super(SPMsn3dToAims, self).__init__(**kwargs)
        self.name = "ConvertSPMnormalizationToAIMS"

        self.add_field(
            "read", File, read=True, allowed_extensions=[".mat"], write=False
        )
        self.add_field(
            "write", File, write=True, allowed_extensions=[".trm"], read=True
        )
        self.add_field(
            "target",
            Literal[
                "MNI template",
                "unspecified template",
                "normalized_volume in AIMS orientation",
            ],
        )
        self.target = "MNI template"
        self.add_field(
            "source_volume",
            File,
            read=True,
            allowed_extensions=[".nii", ".img", ".hdr"],
            optional=True,
            write=False,
        )
        self.add_field(
            "normalized_volume",
            File,
            read=True,
            allowed_extensions=[".nii", ".img", ".hdr"],
            optional=True,
            write=False,
        )
        self.add_field("removeSource", bool)
        self.removeSource = False

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
