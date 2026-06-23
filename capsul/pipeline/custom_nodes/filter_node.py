# -*- coding: utf-8 -*-

from capsul.pipeline import pipeline_nodes
from soma.controller import Controller
import traits.api as traits


class FilterNode(pipeline_nodes.Node):
    '''
    This "inert" node builds an output list of file names from a glob
    expression (pattern matching on the filesystem).

    This node is a "pure virtual" node and needs to be subclassed in order to
    work, since the :meth:`update_callback`` method is not implemented and
    should be implemented in different ways depending on the data source
    (``input`` type). There are specializatons for ``glob.glob()`` expressions,
    CSV file reading, and it is esy to write more specialized nodes, such as
    SQL database querying.

    The main ``input`` is the glob expression (ex: ``*/*.nii.gz``). The input
    results may be modified by a filter, and the ``ouputs`` is a list of
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

    When ``filter`` is used, the output type may be specified to be different,
    like ``Str`` or ``Float``. The constructor ``output_type`` parameter is a
    string expressed in traits types names.
    '''

    _doc_path = 'api/pipeline.html#filternode'

    def __init__(self, pipeline, name, out_type=None):
        '''
        Parameters
        ----------
        pipeline: Pipeline
            pipeline which will hold the node
        name: str
            node name
        out_type: str
            type of indiviidual outputs in the list "outputs". By default it is
            File, but iy may be chnaged to Directory or Str (especially if a
            filter is used)

        '''
        super().__init__(pipeline, name,
                         [{'name': 'input', 'optional': False},
                          {'name': 'filter', 'optional': True},
                          {'name': 'keep_empty'}],
                         [{'name': 'outputs', 'optional': False}])
        # self.add_trait('input', traits.Str())
        if out_type is None:
            out_type = traits.File()
        self.add_trait('outputs', traits.List(out_type, output=True))
        self.add_trait('filter', traits.Str())
        self.add_trait('keep_empty', traits.Bool())
        self.keep_empty = True
        self.on_trait_change(self.update_callback, ['filter', 'keep_empty'])

    def update_callback(self):
        raise NotImplementedError(
            'A derived class must overload the update_callback() method.')

    def run_filter(self, req_result):
        conv_types = {'File': str, 'Str': str, 'Directory': str,
                      'Float': float, 'Int': int}
        ot = self.trait('outputs').inner_traits[0]
        if hasattr(ot, 'handler') and hasattr(ot.handler, 'aType'):
            ct = ot.handler.oType
        else:
            dv = ot.default_value
            if hasattr(dv, '__call__'):
                ct = dv()[1]
            else:
                ct = type(dv).__name__

        def conv_type(x):
            c = conv_types.get(ct, str)
            return c(x)

        if not self.filter:
            self.outputs = [conv_type(x) for x in req_result]
            return

        if self.filter:
            res = [conv_type(eval(self.filter)) for x in req_result]
            if not self.keep_empty:
                res = [x for x in res if x]
        self.outputs = res

    def configured_controller(self):
        c = self.configure_controller()
        return c

    @classmethod
    def configure_controller(cls):
        c = Controller()
        c.add_trait('output_type', traits.Str())
        return c

    @classmethod
    def build_node(cls, pipeline, name, conf_controller):
        out_type = conf_controller.output_type
        if not out_type:
            out_type = 'File'
        out_type = getattr(traits, out_type)
        out_type = out_type()
        node = cls(pipeline, name, out_type)
        return node
