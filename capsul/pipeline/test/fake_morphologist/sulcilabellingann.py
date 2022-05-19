# -*- coding: utf-8 -*-

from capsul.api import Process
import os
from soma.controller import File, Directory, undefined, Literal


class SulciLabellingANN(Process):
    def __init__(self, **kwargs):
        super(SulciLabellingANN, self).__init__(**kwargs)
        self.name = 'recognition2000'

        self.add_field("data_graph", File, read=True, allowed_extensions=['.arg', '.data'], write=False)
        self.add_field("model", File, read=True, allowed_extensions=['.arg', '.data'], write=False, optional=True)
        self.model = '/casa/host/build/share/brainvisa-share-5.1/models/models_2008/discriminative_models/3.0/Lfolds_noroots/Lfolds_noroots.arg'
        self.add_field("output_graph", File, write=True, allowed_extensions=['.arg', '.data'], read=True)
        self.add_field("model_hint", Literal[0,1], optional=True)
        self.model_hint = 0
        self.add_field("energy_plot_file", File, write=True, allowed_extensions=['.nrj'], read=True)
        self.add_field("rate", float, optional=True)
        self.rate = 0.98
        self.add_field("stopRate", float, optional=True)
        self.stopRate = 0.05
        self.add_field("niterBelowStopProp", int, optional=True)
        self.niterBelowStopProp = 1
        self.add_field("forbid_unknown_label", bool, optional=True)
        self.forbid_unknown_label = False
        self.add_field("fix_random_seed", bool, optional=True)
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
                if filename not in (None, undefined, ''):
                    if not os.path.exists(filename):
                        raise ValueError(
                          'Input parameter: %s, file %s does not exist'
                          % (name, repr(filename)))

        for name in outputs:
            field = self.field(name)
            filename = getattr(self, name, undefined)
            if filename not in (None, undefined, ''):
                with open(filename, 'w') as f:
                    f.write('class: %s\n' % self.__class__.__name__)
                    f.write('name: %s\n' % self.name)
                    f.write('parameter: %s\n' % name)
