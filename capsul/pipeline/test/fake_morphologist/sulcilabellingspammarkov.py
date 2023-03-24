# -*- coding: utf-8 -*-

from capsul.api import Process
import os
from soma.controller import File, Directory, undefined, Literal


class SulciLabellingSPAMMarkov(Process):
    def __init__(self, **kwargs):
        super(SulciLabellingSPAMMarkov, self).__init__(**kwargs)
        self.name = "markovian_recognition"

        self.add_field(
            "data_graph",
            File,
            read=True,
            allowed_extensions=[".arg", ".data"],
            write=False,
        )
        self.add_field(
            "output_graph",
            File,
            write=True,
            allowed_extensions=[".arg", ".data"],
            read=True,
        )
        self.add_field(
            "model", File, read=True, allowed_extensions=[".dat"], write=False
        )
        self.add_field(
            "posterior_probabilities",
            File,
            write=True,
            allowed_extensions=[".csv"],
            read=True,
        )
        self.add_field(
            "labels_translation_map",
            File,
            read=True,
            allowed_extensions=[".trl", ".def"],
            write=False,
        )
        self.labels_translation_map = "/casa/host/build/share/brainvisa-share-5.1/nomenclature/translation/sulci_model_2008.trl"
        self.add_field(
            "labels_priors", File, read=True, allowed_extensions=[".dat"], write=False
        )
        self.add_field(
            "segments_relations_model",
            File,
            read=True,
            allowed_extensions=[".dat"],
            write=False,
        )
        self.add_field(
            "initial_transformation",
            File,
            read=True,
            allowed_extensions=[".trm"],
            optional=True,
            write=False,
        )
        self.add_field(
            "global_transformation",
            File,
            read=True,
            allowed_extensions=[".trm"],
            optional=True,
            write=False,
        )
        self.add_field("fix_random_seed", bool)
        self.fix_random_seed = False

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
