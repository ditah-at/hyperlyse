from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt6.QtWidgets import QSizePolicy

class PlotCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.figure = Figure(figsize=(width, height), dpi=dpi)
        self.ax = self.figure.add_subplot(111)

        FigureCanvas.__init__(self, self.figure)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(self, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        FigureCanvas.updateGeometry(self)

    def plot(self, x, y, label='', linewidth=2, hold=False):
        if not hold:
            self.figure.clear()
            self.ax = self.figure.add_subplot(111)
        self.ax.plot(x, y, label=label, linewidth=linewidth)
        self.ax.set_ylim(0,1)
        if label:
            self.ax.legend()
        self.draw()

    def reset(self):
        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        self.draw()

    def save(self, fileName):
        self.figure.savefig(fileName, transparent=True)