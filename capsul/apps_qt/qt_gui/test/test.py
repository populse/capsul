import sys

from traits.api import *
from PySide.QtGui import QApplication

from capsul.apps_qt.qt_gui.controller_widget import ControllerWidget
from soma.controller import Controller


class Point(Controller):
    x = Float()
    y = Float()


class Bidule(Controller):
    l = List(Float())
    ll = List(List(Float()))
    e = Enum("1", "2", "3")
    i = Int()
    s = Str()
    f = Float()
    p = Instance(Point)

    def __init__(self, s='default', i=-4, p=None):
        super(Bidule, self).__init__()
        self.s = s
        self.i = i
        if p is None:
            p = Point()
        self.p = p
        self.l = [3.2, 0.5]
        self.ll = [[3.2, 0.5], [1.1, 0.9]]

qApp = QApplication(sys.argv)
controller = Bidule()
controller.s = ""
controller.f = 10.2
widget = ControllerWidget(controller)
widget.show()
qApp.exec_()



