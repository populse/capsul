# -*- coding: utf-8 -*-

from capsul.api import Process
import os
import traits.api as traits


class SulciDeepLabeling(Process):
    def __init__(self):
        super(SulciDeepLabeling, self).__init__()
        self.name = 'SulciDeepLabeling'

        self.add_trait("graph", traits.File(output=False, desc='input graph to segment', optional=False))
        self.add_trait("roots", traits.File(output=False, desc='root file corresponding to the input graph', optional=False))
        self.add_trait("model_file", traits.File(output=False, desc='file (.mdsm) storing neural network parameters', optional=False))
        self.add_trait("param_file", traits.File(output=False, desc='file (.json) storing the hyperparameters (cutting threshold)', optional=False))
        self.add_trait("rebuild_attributes", traits.Bool(output=False, optional=False))
        self.rebuild_attributes = True
        self.add_trait("skeleton", traits.File(output=False, desc='skeleton file corresponding to the input graph', optional=False))
        self.add_trait("allow_multithreading", traits.Bool(output=False, optional=False))
        self.allow_multithreading = True
        self.add_trait("labeled_graph", traits.File(output=True, desc='output labeled graph', optional=False))
        self.labeled_graph = ''
        self.add_trait("cuda", traits.Int(output=False, desc='device on which to run the training(-1 for cpu, i>=0 for the i-th gpu)', optional=False))
        self.cuda = -1
        self.add_trait("fix_random_seed", traits.Bool(output=False, desc='Use same random sequence', optional=False))
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
