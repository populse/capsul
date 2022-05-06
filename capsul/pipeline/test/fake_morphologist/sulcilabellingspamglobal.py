# -*- coding: utf-8 -*-

from capsul.api import Process
import os
import traits.api as traits


class SulciLabellingSPAMGlobal(Process):
    def __init__(self):
        super(SulciLabellingSPAMGlobal, self).__init__()
        self.name = 'SulciLabellingSPAMGlobal'

        self.add_trait("data_graph", traits.File(allowed_extensions=['.arg', '.data'], output=False, optional=False))
        self.add_trait("output_graph", traits.File(allowed_extensions=['.arg', '.data'], output=True, optional=False))
        self.output_graph = ''
        self.add_trait("model_type", traits.Enum('Talairach', 'Global registration', output=False, optional=False))
        self.model_type = 'Global registration'
        self.add_trait("model", traits.File(allowed_extensions=['.dat'], output=False, optional=False))
        self.add_trait("posterior_probabilities", traits.File(allowed_extensions=['.csv'], output=True, optional=False))
        self.posterior_probabilities = ''
        self.add_trait("labels_translation_map", traits.File(allowed_extensions=['.trl', '.def'], output=False, optional=False))
        self.labels_translation_map = '/volatile/riviere/brainvisa/build-stable-qt5/share/brainvisa-share-4.6/nomenclature/translation/sulci_model_2008.trl'
        self.add_trait("labels_priors", traits.File(allowed_extensions=['.dat'], output=False, optional=False))
        self.add_trait("output_transformation", traits.File(allowed_extensions=['.trm'], output=True, optional=True))
        self.output_transformation = ''
        self.add_trait("initial_transformation", traits.File(allowed_extensions=['.trm'], optional=True, output=False))
        self.add_trait("output_t1_to_global_transformation", traits.File(allowed_extensions=['.trm'], output=True, optional=True))
        self.output_t1_to_global_transformation = ''

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
