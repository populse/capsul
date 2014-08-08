import sys

from traits.api import *
from PySide.QtGui import QApplication

from controller_widget import ControllerWidget
from soma.controller import Controller


class Point(Controller):
    x = Float()
    y = Float()


class Bidule(Controller):
    e = Enum("1", "2", "3")
    i = Int()
    s = Str()
    f = Float()
    p = Instance(Point)
    l = List(Instance(Point))

    def __init__(self, s='default', i=-4, p=None):
        super(Bidule, self).__init__()
        self.s = s
        self.i = i
        if p is None:
            p = Point()
        self.p = p
    self.l = [Point(), Point()]

qApp = QApplication(sys.argv)
controller = Bidule()
controller.s = ""
controller.f = 10.2
widget = ControllerWidget(controller)
widget.show()
qApp.exec_()



