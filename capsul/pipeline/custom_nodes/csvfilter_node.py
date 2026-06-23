# -*- coding: utf-8 -*-

import traits.api as traits
from . import filter_node
from capsul.pipeline.pipeline_nodes import Plug
import os
import os.path as osp


class CSVFilterNode(filter_node.FilterNode):
    '''
    This "inert" node builds an output list of file names from a CSV table
    column.

    The main ``input`` is CSV filename.

    ``columpn`` is the header title of the column (ex:: ``patient_id``.
    Results may be modified by a filter, and the ``ouputs`` is a list of
    results.

    As in other custom nodes, the input/output link is done when the input is
    set or changed, not as an execution action: this means it works during the
    pipeline definition phase, not during workflow execution. Thus it may be
    used to feed an iteration node.

    ``filter`` is an optional input, which can be used to filter/transform
    results from the glob filesystem search. The filter string is thus supposed
    to contain a python code expression which will be called using the python
    eval() function, for each individual item of the glob search. The itm will
    be available in the ``x`` variable.

    Ex: ``os.path.basename(x).split('.', 1)[0]``
    '''

    def __init__(self, pipeline, name, out_type=None):
        super().__init__(pipeline, name, out_type)
        self.add_trait('input', traits.Str())
        self.add_trait('column', traits.Str())
        plug = Plug(name='input')
        self.plugs['input'] = plug
        plug = Plug(name='column')
        self.plugs['column'] = plug
        self.on_trait_change(self.update_callback, ['input', 'column'])

    def update_callback(self):
        import pandas as pd
        if self.input:
            df = pd.read_csv(self.input)
            if df.shape[1] == 1:
                df = pd.read_csv(self.input, sep=';')
            self.run_filter(df[self.column])
