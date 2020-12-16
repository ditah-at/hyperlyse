import sys
import os
import numpy as np
from PyQt5 import uic
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import QUrl, QRect
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QSizePolicy, QFileDialog, QAction, QMenuBar, QMenu, QWidget
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import hyperlyse.specim as specim
#from hyperlyse.mainwindow import Ui_MainWindow


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

    def reset(self):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        self.draw()



#globals
class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        # data members
        self.cube = None
        self.rgb = None
        self.x = 0
        self.y = 0
        self.spectrum = None
        self.rawfile = None

        ##########
        # setup ui
        ##########
        self.setWindowTitle('Hyperlyse')

        # load central widget and contents
        self.cw = uic.loadUi('centralwidget.ui')
        self.setCentralWidget(self.cw)

        # init image panel
        startupImg = QPixmap()
        startupImg.load('startup.png')
        self.cw.imageLabel.setPixmap(startupImg)
        self.cw.imageLabel.mousePressEvent = self.handleClickOnImage
        self.cw.imageLabel.setAcceptDrops(True)
        self.cw.imageLabel.dragEnterEvent = self.handleDragEnter
        self.cw.imageLabel.dropEvent = self.handleDrop

        # init plot panel
        self.plot = PlotCanvas()
        self.cw.layout().addWidget(self.plot, 0, 1)

        # connect ui widgets
        self.cw.exportButton.clicked.connect(self.handleExportButton)
        self.cw.checkBoxRGB.stateChanged.connect(self.handleCheckBoxRGB)
        self.cw.lambdaSlider.setEnabled(False)
        self.cw.lambdaSlider.valueChanged.connect(self.handleSliderChanged)

        # create statusbar
        self.statusBar()

        # setup menu
        actionLoadData = QAction('&Load HS data...', self)
        actionLoadData.setEnabled(True)
        actionLoadData.triggered.connect(self.handleLoadData)
        menuBar = self.menuBar()
        fileMenu = menuBar.addMenu('&File')
        fileMenu.addAction(actionLoadData)

        self.show()

    def loadData(self, filename):
        try:
            self.cube = specim.read(filename)
            self.rgb = specim.cube2rgb(self.cube)
            self.resetUI()
            self.setImageLabel(self.rgb)

            self.rawfile = filename
        except:
            print("Error loading file.")

    def resetUI(self):
        self.cw.checkBoxRGB.setChecked(True)
        self.cw.lambdaSlider.setValue(0)
        self.cw.lambdaSlider.setEnabled(False)
        self.cw.lambdaLabel.setText('')
        if self.cube is not None:
            if len(self.cube.shape) > 2:
                self.cw.lambdaSlider.setMaximum(self.cube.shape[2])
        self.plot.reset()

    def setImageLabel(self, img: np.array):
        # float to normalized 8 bit
        img = np.uint8(img * (2 ** 8 / img.max()))

        s = img.shape
        height = s[0]
        width = s[1]

        qImg = None
        if len(s) == 3:
            if s[2] == 3:
                qImg = QImage(img.tobytes(), width, height, 3 * width, QImage.Format_RGB888)
        else:
            qImg = QImage(img.tobytes(), width, height, width, QImage.Format_Grayscale8)

        if qImg is not None:
            qPixmap = QPixmap.fromImage(qImg)
            self.cw.imageLabel.setPixmap(qPixmap)


    def handleLoadData(self):
        filename, _ = QFileDialog.getOpenFileName(None, "Select Specim Raw File", "", "Specim raw files (*.raw)")
        self.loadData(filename)


    def handleDragEnter(self, e):
        if e.mimeData().hasUrls():
            e.accept()
        else:
            e.ignore()


    def handleDrop(self, e):
        urls = e.mimeData().urls()
        if len(urls) > 1:
            print('Dropped multiple files. Loading one of them (good luck).')
        filename = urls[0].url(QUrl.RemoveScheme)
        #remove leading slashes
        while filename.startswith('/'):
            filename = filename[1:]
        if not filename.endswith('.raw'):
            print('Invalid file extension.')
            return
        self.loadData(filename)


    def handleClickOnImage(self, event):
        self.x = event.pos().x()
        self.y = event.pos().y()

        print("x=%d, y=%d" % (self.x, self.y))

        if 0 <= self.x < specim.cols and 0 <= self.y < specim.rows and self.cube is not None:
            self.spectrum = self.cube[self.y, self.x, :]
            self.plot.plot(specim.lambda_space, self.spectrum)


    def handleExportButton(self):
        if self.spectrum is not None:
            expdir = os.path.dirname(self.rawfile)
            basename = os.path.basename(self.rawfile).split('.')[0]
            expfile = os.path.join(expdir, "%s_(%d,%d).txt" % (basename, self.x, self.y))

            fileName, _ = QFileDialog.getSaveFileName(None, "Save spectrum", expfile, "All Files (*)")

            if fileName:
                data_x = np.float32(specim.lambda_space)
                data = np.transpose([data_x, self.spectrum])
                np.savetxt(fileName, data, fmt='%.4f', delimiter=', ')

    def handleCheckBoxRGB(self):
        if self.cw.checkBoxRGB.isChecked():
            self.cw.lambdaSlider.setEnabled(False)
            self.cw.lambdaLabel.setText('')
            if self.rgb is not None:
                self.setImageLabel(self.rgb)
        else:
            self.cw.lambdaSlider.setEnabled(True)
            self.handleSliderChanged()

    def handleSliderChanged(self):
        layer = self.cw.lambdaSlider.value()
        if self.cube is not None:
            if 0 <= layer < self.cube.shape[2]:
                img = self.cube[:, :, layer]
                self.setImageLabel(img)
                wl = specim.lambda_space[layer]
                self.cw.lambdaLabel.setText('%.1fnm' % wl)

# main
if __name__ == "__main__":
    app = QApplication([])
    win = MainWindow()
    sys.exit(app.exec())
