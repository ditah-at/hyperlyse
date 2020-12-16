import sys
import os
import numpy as np
from PyQt5 import uic
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QSizePolicy, QFileDialog
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import hyperlyse.specim as specim
#from hyperlyse.mainwindow import Ui_MainWindow


#globals
cube = None
rgb = None
x = 0
y = 0
spectrum = None
rawfile = None


class PlotCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)

        FigureCanvas.__init__(self, fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding, QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

    def plot(self, x, y):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.plot(x, y)
        self.draw()




def handleLoadData():
    global cube, rgb, rawfile
    rawfile, _ = QFileDialog.getOpenFileName(None, "Select Specim Raw File", "", "Specim raw files (*.raw)")

    try:
        cube = specim.read(rawfile)
        rgb = specim.cube2rgb(cube)
        rgb = np.uint8(rgb * 2 ** 8)

        height, width, channel = rgb.shape
        bytesPerLine = 3 * width
        qImg = QImage(rgb.tobytes(), width, height, bytesPerLine, QImage.Format_RGB888)
        qPixmap = QPixmap.fromImage(qImg)
        win.imageLabel.setPixmap(qPixmap)

    except:
        print("oops")


def handleDrop(event):
    print("mimi")

def handleClickOnImage(event):
    global x, y, spectrum, cube
    x = event.pos().x()
    y = event.pos().y()

    print("x=%d, y=%d" % (x, y))

    if 0 <= x < specim.cols and 0 <= y < specim.rows and cube is not None:
        spectrum = cube[y, x, :]
        plot.plot(specim.lambda_space, spectrum)


def handleExportButton():
    global x, y, spectrum, rawfile

    if spectrum is not None:
        expdir = os.path.dirname(rawfile)
        basename = os.path.basename(rawfile).split('.')[0]
        expfile = os.path.join(expdir, "%s_(%d,%d).txt" % (basename, x, y))

        fileName, _ = QFileDialog.getSaveFileName(None, "Save spectrum", expfile, "All Files (*)")

        if fileName:
            data_x = np.float32(specim.lambda_space)
            data = np.transpose([data_x, spectrum])
            np.savetxt(fileName, data, fmt='%.4f', delimiter=', ')




#main

app = QApplication([])
win = uic.loadUi("mainwindow.ui")  # specify the location of your .ui file

startupImg = QPixmap()
startupImg.load('startup.png')
win.imageLabel.setPixmap(startupImg)

win.imageLabel.mousePressEvent = handleClickOnImage

plot = PlotCanvas()
win.centralwidget.layout().addWidget(plot,0,1)

win.exportButton.clicked.connect(handleExportButton)

win.actionLoad_HS_data.triggered.connect(handleLoadData)

#win.imageLabel.setAcceptDrops(True)
#win.imageLabel.dropEvent = handleDrop

win.show()

sys.exit(app.exec())
