import os

from soma.controller import Directory, File, Literal, undefined

from capsul.api import Process


class SulciDeepLabeling(Process):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "CNN_recognition19"

        self.add_field(
            "graph", File, doc="input graph to segment", read=True, write=False
        )
        self.add_field(
            "roots",
            File,
            doc="root file corresponding to the input graph",
            read=True,
            write=False,
        )
        self.add_field(
            "model_file",
            File,
            dataset="shared",
            doc="file (.mdsm) storing neural network parameters",
            read=True,
            write=False,
        )
        self.add_field(
            "param_file",
            File,
            dataset="shared",
            doc="file (.json) storing the hyperparameters (cutting threshold)",
            read=True,
            write=False,
        )
        self.add_field("rebuild_attributes", bool, default=True, optional=True)
        self.rebuild_attributes = True
        self.add_field(
            "skeleton",
            File,
            doc="skeleton file corresponding to the input graph",
            read=True,
            write=False,
        )
        self.add_field("allow_multithreading", bool, default=True, optional=True)
        self.allow_multithreading = True
        self.add_field(
            "labeled_graph", File, write=True, doc="output labeled graph", read=True
        )
        self.add_field(
            "cuda",
            int,
            doc="device on which to run the training(-1 for cpu, i>=0 for the i-th gpu)",
            default=-1,
            optional=True,
        )
        self.cuda = -1
        self.add_field(
            "fix_random_seed",
            bool,
            doc="Use same random sequence",
            default=False,
            optional=True,
        )
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
