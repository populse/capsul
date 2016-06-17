
from capsul.api import StudyConfig
from capsul.api import get_process_instance
from capsul.process.attributed_process import AttributedProcessFactory
from capsul.process import attributed_process_iteration


if __name__ == '__main__':
    from capsul.qt_gui.widgets.pipeline_developper_view \
        import PipelineDevelopperView
    from soma.qt_gui.qt_backend import QtGui, QtCore

    study_config = StudyConfig(
        'test_study',
        modules=StudyConfig.default_modules + ['FomConfig', 'BrainVISAConfig'])
    pipeline = get_process_instance(
        'bv_capsul_ex.ex_processes.GroupAveragePipeline')
    patt = AttributedProcessFactory().get_attributed_process(pipeline,
                                                             study_config)
    qapp = None
    if QtGui.QApplication.instance() is None:
        qapp = QtGui.QApplication(['test_app'])
    pv = PipelineDevelopperView(patt, allow_open_controller=True,
                                enable_edition=True, show_sub_pipelines=True)
    pv.show()
    if qapp:
        qapp.exec_()


