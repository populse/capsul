# -*- coding: utf-8 -*-

from capsul.api import Process
import os
import traits.api as traits


class SulciLabellingANN(Process):
    def __init__(self):
        super(SulciLabellingANN, self).__init__()
        self.name = 'SulciLabellingANN'

        self.add_trait("data_graph", traits.File(allowed_extensions=['.arg', '.data'], output=False, optional=False))
        self.add_trait("model", traits.File(allowed_extensions=['.arg', '.data'], output=False, optional=False))
        self.model = '/volatile/riviere/brainvisa/build-stable-qt5/share/brainvisa-share-4.6/models/models_2008/discriminative_models/3.0/Rfolds_noroots/Rfolds_noroots.arg'
        self.add_trait("output_graph", traits.File(allowed_extensions=['.arg', '.data'], output=True, optional=False))
        self.output_graph = ''
        self.add_trait("model_hint", traits.Enum(0, 1, output=False, optional=False))
        self.model_hint = 0
        self.add_trait("energy_plot_file", traits.File(allowed_extensions=['.nrj'], output=True, optional=False))
        self.energy_plot_file = ''
        self.add_trait("rate", traits.Float(output=False, optional=False))
        self.rate = 0.98
        self.add_trait("stopRate", traits.Float(output=False, optional=False))
        self.stopRate = 0.05
        self.add_trait("niterBelowStopProp", traits.Int(output=False, optional=False))
        self.niterBelowStopProp = 1
        self.add_trait("forbid_unknown_label", traits.Bool(output=False, optional=False))
        self.forbid_unknown_label = False
        self.add_trait("fix_random_seed", traits.Bool(output=False, optional=False))
        self.fix_random_seed = False

    def _run_process(self):
        outputs = []
        for name, trait in self.user_traits().items():
            if isinstance(trait.trait_type, traits.File):
                if trait.output:
                    outputs.append(name)
                    continue
                filename = getattr(self, name)
                if filename not in (None, traits.Undefined, ''):
                    if not os.path.exists(filename):
                        raise ValueError(
                          'Input parameter: %s, file %s does not exist'
                          % (name, repr(filename)))

        for name in outputs:
            trait = self.trait(name)
            filename = getattr(self, name)
            if filename not in (None, traits.Undefined, ''):
                with open(filename, 'w') as f:
                    f.write('class: %s\n' % self.__class__.__name__)
                    f.write('name: %s\n' % self.name)
                    f.write('parameter: %s\n' % name)
