import os, re
from soma.qt_gui.qt_backend import QtGui, loadUi
from capsul.pipeline.pipeline_nodes import PipelineNode

class ActivationInspector(QtGui.QWidget):
    def __init__(self, pipeline, file, developper_view=None, parent=None):
        super(ActivationInspector, self).__init__(parent)
        ui = os.path.join(os.path.dirname(__file__),'activation_inspector.ui')
        loadUi(ui,self)
        self.pipeline = pipeline
        self.file = file
        self.pipeline._debug_activations = self.file
        self.pipeline.update_nodes_and_plugs_activation()
        self.update()
        self.events.currentRowChanged.connect(self.update_pipeline_activation)
        self.btnUpdate.clicked.connect(self.update)
        self.next.clicked.connect(self.find_next)
        self.previous.clicked.connect(self.find_previous)
        self.developper_view = developper_view
        if developper_view is not None:
          developper_view.plug_clicked.connect(self.plug_clicked)

        
    def update(self):
        f = open(self.file)
        pipeline_name = f.readline().strip()
        if pipeline_name != self.pipeline.id:
            raise ValueError('"%s" recorded activations for pipeline "%s" but not for "%s"' % (self.file, pipeline_name, self.pipeline.id))
        self.activations = []
        current_activations = {}
        self.events.clear()
        parser=re.compile(r'(\d+)([+-=])([^:]*)(:([a-zA-Z_0-9]+))?')
        for i in f.readlines():
            iteration, activation, node, x, plug = parser.match(i.strip()).groups()
            if activation == '+':
                current_activations['%s:%s' % (node,plug or '')] = True
            else:
                del current_activations['%s:%s' % (node,plug or '')]
            self.activations.append(current_activations.copy())
            self.events.addItem('%s %s:%s' % (activation, node, plug or ''))
        self.events.setCurrentRow(self.events.count()-1)
    
    def update_pipeline_activation(self,index):
        activations = self.activations[self.events.currentRow()]
        for node in self.pipeline.all_nodes():
            node_name = node.full_name
            for plug_name, plug in node.plugs.iteritems():
                plug.activated = activations.get('%s:%s' % (node_name, plug_name), False)
            node.activated = activations.get('%s:' % node_name, False)
        
        # Refresh views relying on plugs and nodes selection
        for node in self.pipeline.all_nodes():
            if isinstance(node, PipelineNode):
                node.process.selection_changed = True

    def find_next(self):
        pattern = re.compile(self.pattern.text())
        i = self.events.currentRow() + 1
        while i < self.events.count():
            if pattern.search(self.events.item(i).text()):
                self.events.setCurrentRow(i)
                break
            i += 1
        
    def find_previous(self):
        pattern = re.compile(self.pattern.text())
        i = self.events.currentRow() - 1
        while i > 0:
            if pattern.search(self.events.item(i).text()):
                self.events.setCurrentRow(i)
                break
            i -= 1

    def plug_clicked(self, plug_name):
        self.pattern.setText(plug_name)
