# -*- coding: utf-8 -*-

from capsul.api import Process
import os
from soma.controller import File, Directory, undefined, Literal


class Normalization_Baladin(Process):
    def __init__(self, **kwargs):
        super(Normalization_Baladin, self).__init__(**kwargs)
        self.name = "NormalizeBaladin"

        self.add_field(
            "anatomy_data", File, read=True, extensions=[".ima", ".dim"], write=False
        )
        self.add_field(
            "anatomical_template",
            File,
            read=True,
            extensions=[".ima", ".dim"],
            dataset="shared",
            write=False,
        )
        self.add_field(
            "transformation_matrix", File, write=True, extensions=[".txt"], read=True
        )
        self.add_field(
            "normalized_anatomy_data",
            File,
            write=True,
            extensions=[".ima", ".dim", ".nii", ".nii.gz"],
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
