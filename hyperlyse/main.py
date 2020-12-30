import sys
import os
import numpy as np
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QAction
from PyQt5.QtWidgets import QWidget, QLabel, QCheckBox, QSlider, QPushButton
from PyQt5.QtWidgets import QSizePolicy, QHBoxLayout, QGridLayout
import matplotlib.image
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from hyperlyse import specim, processing


class PlotCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.figure = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.figure.add_subplot(111)

        FigureCanvas.__init__(self, self.figure)
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

    def save(self, fileName):
        self.figure.savefig(fileName, transparent=True)

CROSS_SIZE = 5
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

        # central widget and outer layout
        cw = QWidget(self)
        self.setCentralWidget(cw)
        layout_outer = QGridLayout(cw)
        cw.setLayout(layout_outer)

        # image display
        self.imageLabel = QLabel(cw)
        img_startup = QPixmap()
        img_startup.load('startup.png')
        self.imageLabel.setPixmap(img_startup)
        self.imageLabel.mousePressEvent = self.handleClickOnImage
        self.imageLabel.setAcceptDrops(True)
        self.imageLabel.dragEnterEvent = self.handleDragEnter
        self.imageLabel.dropEvent = self.handleDrop
        layout_outer.addWidget(self.imageLabel, 0, 0)

        # image controls
        layout_img_ctrl = QHBoxLayout(cw)
        layout_outer.addLayout(layout_img_ctrl, 1, 0)

        self.checkBoxRGB = QCheckBox(cw)
        self.checkBoxRGB.setChecked(True)
        self.checkBoxRGB.setText('RGB')
        self.checkBoxRGB.stateChanged.connect(self.handleCheckBoxRGB)
        layout_img_ctrl.addWidget(self.checkBoxRGB)

        self.lambdaSlider = QSlider(cw)
        self.lambdaSlider.setOrientation(Qt.Horizontal)
        self.lambdaSlider.setEnabled(False)
        self.lambdaSlider.valueChanged.connect(self.handleSliderChanged)
        layout_img_ctrl.addWidget(self.lambdaSlider)

        self.lambdaLabel = QLabel(cw)
        layout_img_ctrl.addWidget(self.lambdaLabel)

        # specrtra plot
        self.plot = PlotCanvas(cw)
        layout_outer.addWidget(self.plot, 0, 1)

        # export controls
        layout_export_ctrl = QHBoxLayout(cw)
        layout_outer.addLayout(layout_export_ctrl, 1, 1)

        self.exportButton = QPushButton(cw)
        self.exportButton.setText('Export Spectrum')
        self.exportButton.clicked.connect(self.exportSpectrum)
        layout_export_ctrl.addWidget(self.exportButton)
        
        self.includeImageCheckbox = QCheckBox(cw)
        self.includeImageCheckbox.setChecked(True)
        self.includeImageCheckbox.setText('include rgb image')
        layout_export_ctrl.addWidget(self.includeImageCheckbox)

        self.includeGraphCheckbox = QCheckBox(cw)
        self.includeGraphCheckbox.setChecked(True)
        self.includeGraphCheckbox.setText('include graph image')
        layout_export_ctrl.addWidget(self.includeGraphCheckbox)


        # create statusbar (in case we need it at some point..)
        self.statusBar()

        # create menu
        menuBar = self.menuBar()
        fileMenu = menuBar.addMenu('&File')

        actionLoadData = QAction('&Load HS data...', self)
        actionLoadData.triggered.connect(self.handleLoadData)
        fileMenu.addAction(actionLoadData)

        self.actionSaveImage = QAction('&Save image...', self)
        self.actionSaveImage.setEnabled(False)
        self.actionSaveImage.triggered.connect(self.exportImage)
        fileMenu.addAction(self.actionSaveImage)

        # finito!
        self.show()

    def loadData(self, filename):
        try:
            self.cube = specim.read(filename)
            self.rgb = specim.cube2rgb(self.cube)
            self.resetUI()
            self.setImageLabel(self.rgb)
            self.rawfile = filename
            self.actionSaveImage.setEnabled(True)
        except:
            print("Error loading file.")

    def resetUI(self):
        self.checkBoxRGB.setChecked(True)
        self.lambdaSlider.setValue(0)
        self.lambdaSlider.setEnabled(False)
        self.lambdaLabel.setText('')
        if self.cube is not None:
            if len(self.cube.shape) > 2:
                self.lambdaSlider.setMaximum(self.cube.shape[2])
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
            self.imageLabel.setPixmap(qPixmap)

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

    def exportSpectrum(self):
        if self.spectrum is not None:
            expdir = os.path.dirname(self.rawfile)
            basename = os.path.basename(self.rawfile).split('.')[0]
            expfile = os.path.join(expdir, "%s_(%d,%d).txt" % (basename, self.x, self.y))

            fileName, _ = QFileDialog.getSaveFileName(None, "Save spectrum", expfile, "All Files (*)")

            if fileName:
                data_x = np.float32(specim.lambda_space)
                data = np.transpose([data_x, self.spectrum])
                np.savetxt(fileName, data, fmt='%.4f', delimiter=', ')

                if self.includeImageCheckbox.isChecked() and self.rgb is not None:
                    img = np.copy(self.rgb)
                    rows, cols, _ = img.shape
                    img[self.y, max(self.x-CROSS_SIZE, 0):min(self.x+CROSS_SIZE+1, rows-1)] = [0, 1, 0]
                    img[max(self.y - CROSS_SIZE, 0):min(self.y + CROSS_SIZE+1, cols - 1), self.x] = [0, 1, 0]
                    img[img>1.0] = 1.0
                    base, ext = os.path.splitext(fileName)
                    matplotlib.image.imsave(base+'.png', img)

                if self.includeGraphCheckbox.isChecked():
                    base, ext = os.path.splitext(fileName)
                    self.plot.save(base+'_graph.png')


    def exportImage(self):
        expdir = os.path.dirname(self.rawfile)
        basename = os.path.basename(self.rawfile).split('.')[0]
        if self.checkBoxRGB.isChecked():
            suffix = 'rgb'
        else:
            suffix = self.lambdaLabel.text()
        expfile = os.path.join(expdir, "%s_%s.png" % (basename, suffix))

        fileName, _ = QFileDialog.getSaveFileName(None, "Save spectrum", expfile, "All Files (*)")
        if fileName:
            self.imageLabel.pixmap().save(fileName)

    def handleCheckBoxRGB(self):
        if self.checkBoxRGB.isChecked():
            self.lambdaSlider.setEnabled(False)
            self.lambdaLabel.setText('')
            if self.rgb is not None:
                self.setImageLabel(self.rgb)
        else:
            self.lambdaSlider.setEnabled(True)
            self.handleSliderChanged()

    def handleSliderChanged(self):
        layer = self.lambdaSlider.value()
        if self.cube is not None:
            if 0 <= layer < self.cube.shape[2]:
                img = self.cube[:, :, layer]
                self.setImageLabel(img)
                wl = specim.lambda_space[layer]
                self.lambdaLabel.setText('%.1fnm' % wl)

# main
if __name__ == "__main__":
    # app = QApplication([])
    # win = MainWindow()
    # sys.exit(app.exec())
    processing.create_database('E:/CVL_offline/specim_data/Worco_medium_poster', True)
