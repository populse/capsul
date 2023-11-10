# -*- coding: utf-8 -*-

from capsul.api import Process
import os
from soma.controller import File, Directory, undefined, Literal


class Normalization_FSL_reinit(Process):
    def __init__(self, **kwargs):
        super(Normalization_FSL_reinit, self).__init__(**kwargs)
        self.name = "NormalizeFSL"

        self.add_field(
            "anatomy_data", File, read=True, extensions=[".nii", ".nii.gz"], write=False
        )
        self.add_field(
            "anatomical_template",
            File,
            read=True,
            extensions=[".nii", ".nii.gz"],
            dataset="shared",
            write=False,
        )
        self.add_field(
            "Alignment",
            Literal[
                "Already Virtually Aligned",
                "Not Aligned but Same Orientation",
                "Incorrectly Oriented",
            ],
        )
        self.Alignment = "Not Aligned but Same Orientation"
        self.add_field(
            "transformation_matrix", File, write=True, extensions=[".mat"], read=True
        )
        self.add_field(
            "normalized_anatomy_data",
            File,
            write=True,
            extensions=[".nii.gz", ".nii"],
            read=True,
        )
        self.add_field(
            "cost_function",
            Literal[
                "corratio", "mutualinfo", "normcorr", "normmi", "leastsq", "labeldiff"
            ],
        )
        self.cost_function = "corratio"
        self.add_field(
            "search_cost_function",
            Literal[
                "corratio", "mutualinfo", "normcorr", "normmi", "leastsq", "labeldiff"
            ],
        )
        self.search_cost_function = "corratio"
        self.add_field("allow_retry_initialization", bool)
        self.allow_retry_initialization = True
        self.add_field("init_translation_origin", Literal[0, 1])
        self.init_translation_origin = 0

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
