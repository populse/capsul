import tempfile
import sys
from subprocess import check_call
if __name__ == '__main__':
    from soma.qt_gui import qt_backend
    qt_backend.set_qt_backend('PyQt4')
from soma.qt_gui.qt_backend import QtGui
try:
    from traits.api import File, Float, Int, String
except ImportError:
    from enthought.traits.api import File, Float, Int

from capsul.process import Process, get_process_instance
from capsul.pipeline import Pipeline


class EchoProcess(Process):

    def __call__(self):
        print self.id + ':'
        for parameter in self.user_traits():
            print ' ', parameter, '=', repr(getattr(self, parameter))


class SPMNormalization(EchoProcess):

    def __init__(self):
        super(SPMNormalization, self).__init__()
        self.add_trait('image', File())
        self.add_trait('template', File())
        self.add_trait('normalized', File(output=True))


class FSLNormalization(EchoProcess):

    def __init__(self):
        super(FSLNormalization, self).__init__()
        self.add_trait('image', File())
        self.add_trait('template', File())
        self.add_trait('normalized', File(output=True))


class ConvertForFSL(EchoProcess):

    def __init__(self):
        super(ConvertForFSL, self).__init__()
        self.add_trait('input', File())
        self.add_trait('output', File(output=True))


class AnotherNormalization(EchoProcess):

    def __init__(self):
        super(AnotherNormalization, self).__init__()
        self.add_trait('image', File())
        self.add_trait('template', File())
        self.add_trait('normalized', File(output=True))


class ConvertForAnother(EchoProcess):

    def __init__(self):
        super(ConvertForAnother, self).__init__()
        self.add_trait('input', File())
        self.add_trait('output', File(output=True))
        self.add_trait('another_output', File(output=True))


class BiasCorrection(EchoProcess):

    def __init__(self):
        super(BiasCorrection, self).__init__()
        self.add_trait('t1mri', File())
        self.add_trait('field_rigidity', Float())
        self.add_trait('nobias', File(output=True))


class HistoAnalysis(EchoProcess):

    def __init__(self):
        super(HistoAnalysis, self).__init__()
        self.add_trait('image', File())
        self.add_trait('histo_analysis', File(output=True))


class BrainMask(EchoProcess):

    def __init__(self):
        super(BrainMask, self).__init__()
        self.add_trait('t1mri', File())
        self.add_trait('histo_analysis', File())
        self.add_trait('brain_mask', File(output=True))


class SplitBrain(EchoProcess):

    def __init__(self):
        super(SplitBrain, self).__init__()
        self.add_trait('t1mri', File())
        self.add_trait('histo_analysis', File())
        self.add_trait('brain_mask', File())
        self.add_trait('split_brain', File(output=True))


class GreyWhiteClassification(EchoProcess):

    def __init__(self):
        super(GreyWhiteClassification, self).__init__()
        self.add_trait('t1mri', File())
        self.add_trait('label_image', File())
        self.add_trait('label', Int())
        self.add_trait('gw_classification', File(output=True))


class GreyWhiteSurface(EchoProcess):

    def __init__(self):
        super(GreyWhiteSurface, self).__init__()
        self.add_trait('t1mri', File())
        self.add_trait('gw_classification', File())
        self.add_trait('hemi_cortex', File(output=True))
        self.add_trait('white_mesh', File(output=True))


class SphericalHemisphereSurface(EchoProcess):

    def __init__(self):
        super(SphericalHemisphereSurface, self).__init__()
        self.add_trait('gw_classification', File())
        self.add_trait('hemi_cortex', File())
        self.add_trait('hemi_mesh', File(output=True))


class GreyWhite(Pipeline):

    def pipeline_definition(self):
        self.add_process('gw_classification', GreyWhiteClassification())
        self.export_parameter('gw_classification', 't1mri')

        self.add_process('gw_surface', GreyWhiteSurface())
        self.add_link('t1mri->gw_surface.t1mri')
        self.add_link(
            'gw_classification.gw_classification->gw_surface.gw_classification')
        self.export_parameter('gw_classification', 'gw_classification')

        self.add_process('hemi_surface', SphericalHemisphereSurface())
        self.add_link(
            'gw_classification.gw_classification->hemi_surface.gw_classification')
        self.add_link('gw_surface.hemi_cortex->hemi_surface.hemi_cortex')
        self.export_parameter('gw_surface', 'hemi_cortex')


class Morphologist(Pipeline):

    def pipeline_definition(self):
        self.add_trait('t1mri', File())

        self.add_switch('select_normalization', [
                        'spm', 'fsl', 'another', 'none'], 't1mri')
        print(self.nodes['select_normalization'].user_traits())
        self.add_process('bias_correction', BiasCorrection())

        self.add_process(
            'spm_normalization', SPMNormalization)
        self.export_parameter('spm_normalization', 'template')
        self.add_link('t1mri->spm_normalization.image')
        self.add_link(
          'spm_normalization.normalized->select_normalization.spm_switch_t1mri' )
        self.export_parameter('spm_normalization', 'normalized', weak_link=True)

        self.add_process('fsl_convert', ConvertForFSL)
        self.add_process(
            'fsl_normalization', FSLNormalization)
        self.add_link('t1mri->fsl_convert.input')
        self.add_link('template->fsl_normalization.template')
        self.add_link('fsl_convert.output->fsl_normalization.image')
        self.export_parameter('fsl_convert', 'output', 'fsl_converted', weak_link=True)
        self.add_link('fsl_normalization.normalized->select_normalization.fsl_switch_t1mri')
        #self.export_parameter( 'fsl_normalization', 'another', weak_link=True )

        self.add_process(
            'another_convert', ConvertForAnother)
        self.add_process(
            'another_normalization', AnotherNormalization)
        self.add_link('another_normalization.normalized->normalized',weak_link=True)
        self.add_link('t1mri->another_convert.input')
        self.add_link('template->another_normalization.template')
        self.add_link('another_convert.output->another_normalization.image')
        self.add_link('another_normalization.normalized->select_normalization.another_switch_t1mri')

        self.add_link( 't1mri->select_normalization.none_switch_t1mri' )

        self.add_link('select_normalization.t1mri->bias_correction.t1mri')
        self.export_parameter('bias_correction', 'nobias')

        self.add_process('histo_analysis', HistoAnalysis())
        self.add_link('bias_correction.nobias->histo_analysis.image')

        self.add_process('brain_mask', BrainMask())
        self.add_link('select_normalization.t1mri->brain_mask.t1mri')
        self.add_link(
            'histo_analysis.histo_analysis->brain_mask.histo_analysis')
        self.export_parameter('brain_mask', 'brain_mask')

        self.add_process('split_brain', SplitBrain())
        self.add_link('select_normalization.t1mri->split_brain.t1mri')
        self.add_link(
            'histo_analysis.histo_analysis->split_brain.histo_analysis')
        self.add_link('brain_mask.brain_mask->split_brain.brain_mask')

        self.add_process('left_grey_white', GreyWhite(), label=1)
        self.add_link('select_normalization.t1mri->left_grey_white.t1mri')
        self.add_link('split_brain.split_brain->left_grey_white.label_image')
        self.export_parameter(
            'left_grey_white', 'gw_classification', 'left_gw_classification')
        self.export_parameter(
            'left_grey_white', 'hemi_cortex', 'left_hemi_cortex')
        self.export_parameter(
            'left_grey_white', 'hemi_mesh', 'left_hemi_mesh')
        self.export_parameter(
            'left_grey_white', 'white_mesh', 'left_white_mesh')

        self.add_process('right_grey_white', GreyWhite(), label=2)
        self.add_link('select_normalization.t1mri->right_grey_white.t1mri')
        self.add_link('split_brain.split_brain->right_grey_white.label_image')
        self.export_parameter(
            'right_grey_white', 'gw_classification', 'right_gw_classification')
        self.export_parameter(
            'right_grey_white', 'hemi_cortex', 'right_hemi_cortex')
        self.export_parameter(
            'right_grey_white', 'hemi_mesh', 'right_hemi_mesh')
        self.export_parameter(
            'right_grey_white', 'white_mesh', 'right_white_mesh')

        self.node_position = {'another_convert': (100.0, 342.0),
                              'another_normalization': (289.0, 385.0),
                              'bias_correction': (620.0, 140.0),
                              'brain_mask': (930.0, 139.0),
                              'fsl_convert': (131.0, 222.0),
                              'fsl_normalization': (269.0, 192.0),
                              'histo_analysis': (761.0, 190.0),
                              'inputs': (-90.0, 139.0),
                              'left_grey_white': (1242.0, 55.0),
                              'outputs': (1457.0, 103.0),
                              'right_grey_white': (1239.0, 330.0),
                              'select_normalization': (442.0, 65.0),
                              'split_brain': (1089.0, 163.0),
                              'spm_normalization': (173.0, 4.0)}


class WorkflowViewer(QtGui.QWidget):

    def __init__(self, pipeline):
        super(WorkflowViewer, self).__init__()
        self.pipeline = pipeline
        layout = QtGui.QVBoxLayout(self)
        # self.setLayout( layout )
        self.label = QtGui.QLabel()
        layout.addWidget(self.label)
        self.btn_update = QtGui.QPushButton('update')
        layout.addWidget(self.btn_update)
        self.btn_update.clicked.connect(self.update)
        self.update()

    def update(self):
        image = tempfile.NamedTemporaryFile(suffix='.png')
        dot = tempfile.NamedTemporaryFile(suffix='.dot')
        self.write(dot)
        dot.flush()
        check_call( [ 'dot', '-Tpng', '-o', image.name, dot.name ] )
        pixmap = QtGui.QPixmap( image.name ).scaledToHeight( 600 )
        self.label.setPixmap( pixmap )

    def write(self, out=sys.stdout):
        graph = self.pipeline.workflow_graph()
        print >> out, 'digraph workflow {'
        ids = {}
        for n in graph._nodes:
            id = str(len(ids))
            ids[n] = id
            print >> out, '  %s [label="%s"];' % (id, n)
        for n, v in graph._links:
            print >> out, '  %s -> %s;' % (ids[n], ids[v])
        print >> out, '}'


if __name__ == '__main__':
    import sys
    from soma.qt_gui.qt_backend import QtGui
    from soma.gui.widget_controller_creation import ControllerWidget
    from soma.functiontools import SomaPartial as partial
    from capsul.qt_gui.widgets import PipelineDevelopperView

    app = QtGui.QApplication(sys.argv)

    morphologist = Morphologist()

    #  morphologist = get_process_instance('morphologist.morphologist')

    # morphologist.set_string_list( sys.argv[1:] )
    view3 = WorkflowViewer(morphologist)
    view3.show()
    view1 = PipelineDevelopperView(morphologist, show_sub_pipelines=True,
                                   allow_open_controller=True)
    view1.show()
    cw = ControllerWidget(morphologist, live=True)
    cw.show()

    # morphologist.trait( 'nobias' ).hidden = True
    # cw.controller.user_traits_changed = True
    # printer = QtGui.QPrinter( QtGui.QPrinter.HighResolution )
    # printer.setOutputFormat( QtGui.QPrinter.PostScriptFormat )
    # printer.setOutputFileName( sys.argv[ 1 ] )
    # painter = QtGui.QPainter()
    # painter.begin( printer )

    # scale = QtGui.QTransform.fromScale( .5, .5 )
    # painter.setTransform( scale )
    # view1.scene.render( painter )
    # painter.end()

    app.exec_()
    #  morphologist.workflow_graph().write( sys.stdout )
    del view1
    del view3
