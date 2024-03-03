import os

from soma.controller import Directory, File, Literal, undefined

from capsul.api import Process


class sulcigraphmorphometrybysubject(Process):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "SulcalMorphometry"

        self.add_field(
            "left_sulci_graph",
            File,
            read=True,
            extensions=[".arg", ".data"],
            write=False,
        )
        self.add_field(
            "right_sulci_graph",
            File,
            read=True,
            extensions=[".arg", ".data"],
            write=False,
        )
        self.add_field(
            "sulci_file",
            File,
            read=True,
            extensions=[".json"],
            dataset="shared",
            write=False,
        )
        self.sulci_file = "/casa/host/build/share/brainvisa-share-5.2/nomenclature/translation/sulci_default_list.json"
        self.add_field("use_attribute", Literal["label", "name"])
        self.use_attribute = "label"
        self.add_field(
            "sulcal_morpho_measures", File, write=True, extensions=[".csv"], read=True
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
