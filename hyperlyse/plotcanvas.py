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

        self.xmin = 0
        self.xmax = 1000
        self.ymin = 0.0
        self.ymax = 1.0

    def set_ranges(self, xmin, xmax, ymin, ymax):
        self.xmin = xmin
        self.xmax = xmax
        self.ymin = ymin
        self.ymax = ymax

    def plot(self,
             x,
             y,
             label='',
             linewidth=2,
             hold=False):
        if not hold:
            self.figure.clear()
            self.ax = self.figure.add_subplot(111)
            color = 'green' if self.xmin < self.xmax else 'red'
            self.ax.axvspan(self.xmin, self.xmax, alpha=0.1, color=color)
        self.ax.plot(x, y, label=label, linewidth=linewidth)
        self.ax.set_ylim(self.ymin, self.ymax)
        if label:
            self.ax.legend()
        self.draw()

    def reset(self):
        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        self.draw()

    def save(self, fileName):
        self.figure.savefig(fileName, transparent=True)