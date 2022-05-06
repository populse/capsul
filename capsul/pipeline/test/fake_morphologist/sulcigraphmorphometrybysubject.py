# -*- coding: utf-8 -*-

from capsul.api import Process
import os
import traits.api as traits


class sulcigraphmorphometrybysubject(Process):
    def __init__(self):
        super(sulcigraphmorphometrybysubject, self).__init__()
        self.name = 'sulcigraphmorphometrybysubject'

        self.add_trait("left_sulci_graph", traits.File(allowed_extensions=['.arg', '.data'], output=False, optional=False, connected_output=True))
        self.add_trait("right_sulci_graph", traits.File(allowed_extensions=['.arg', '.data'], output=False, optional=False, connected_output=True))
        self.add_trait("sulci_file", traits.File(allowed_extensions=['.json'], output=False, optional=False))
        self.sulci_file = '/volatile/riviere/brainvisa/build-stable-qt5/share/brainvisa-share-4.6/nomenclature/translation/sulci_default_list.json'
        self.add_trait("use_attribute", traits.Enum('label', 'name', output=False, optional=False))
        self.use_attribute = 'label'
        self.add_trait("sulcal_morpho_measures", traits.File(allowed_extensions=['.csv'], output=True, optional=False))
        self.sulcal_morpho_measures = ''

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
