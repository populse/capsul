# -*- coding: utf-8 -*-

from capsul.api import Process
import os
import traits.api as traits


class SulciLabellingSPAMMarkov(Process):
    def __init__(self):
        super(SulciLabellingSPAMMarkov, self).__init__()
        self.name = 'SulciLabellingSPAMMarkov'

        self.add_trait("data_graph", traits.File(allowed_extensions=['.arg', '.data'], output=False, optional=False, connected_output=True))
        self.add_trait("output_graph", traits.File(allowed_extensions=['.arg', '.data'], output=True, optional=False))
        self.output_graph = ''
        self.add_trait("model", traits.File(allowed_extensions=['.dat'], output=False, optional=False))
        self.add_trait("posterior_probabilities", traits.File(allowed_extensions=['.csv'], output=True, optional=False))
        self.posterior_probabilities = ''
        self.add_trait("labels_translation_map", traits.File(allowed_extensions=['.trl', '.def'], output=False, optional=False))
        self.labels_translation_map = '/volatile/riviere/brainvisa/build-stable-qt5/share/brainvisa-share-4.6/nomenclature/translation/sulci_model_2008.trl'
        self.add_trait("labels_priors", traits.File(allowed_extensions=['.dat'], output=False, optional=False))
        self.add_trait("segments_relations_model", traits.File(allowed_extensions=['.dat'], output=False, optional=False))
        self.add_trait("initial_transformation", traits.File(allowed_extensions=['.trm'], optional=True, output=False))
        self.add_trait("global_transformation", traits.File(allowed_extensions=['.trm'], optional=True, output=False, connected_output=True))
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
