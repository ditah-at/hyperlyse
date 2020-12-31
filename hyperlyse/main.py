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
from hyperlyse import specim, Analysis


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


# config
CROSS_SIZE = 5
DB_FILE = 'Worco_medium_poster_spectra-db.json'
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

        self.anal = Analysis()
        self.anal.load_db(DB_FILE)


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
        self.lbl_img = QLabel(cw)
        img_startup = QPixmap()
        img_startup.load('startup.png')
        self.lbl_img.setPixmap(img_startup)
        self.lbl_img.mousePressEvent = self.handle_click_on_image
        self.lbl_img.setAcceptDrops(True)
        self.lbl_img.dragEnterEvent = self.handle_drag_enter
        self.lbl_img.dropEvent = self.handle_drop
        layout_outer.addWidget(self.lbl_img, 0, 0)

        # image controls
        layout_img_ctrl = QHBoxLayout(cw)
        layout_outer.addLayout(layout_img_ctrl, 1, 0)

        self.cb_rgb = QCheckBox(cw)
        self.cb_rgb.setChecked(True)
        self.cb_rgb.setText('RGB')
        self.cb_rgb.stateChanged.connect(self.handle_cb_rgb_changed)
        layout_img_ctrl.addWidget(self.cb_rgb)

        self.sl_lambda = QSlider(cw)
        self.sl_lambda.setOrientation(Qt.Horizontal)
        self.sl_lambda.setEnabled(False)
        self.sl_lambda.valueChanged.connect(self.handle_sl_lambda_changed)
        layout_img_ctrl.addWidget(self.sl_lambda)

        self.lbl_lambda = QLabel(cw)
        layout_img_ctrl.addWidget(self.lbl_lambda)

        # specrtra plot
        self.plot = PlotCanvas(cw)
        layout_outer.addWidget(self.plot, 0, 1)

        # export controls
        layout_export_ctrl = QHBoxLayout(cw)
        layout_outer.addLayout(layout_export_ctrl, 1, 1)

        self.btn_export = QPushButton(cw)
        self.btn_export.setText('Export Spectrum')
        self.btn_export.clicked.connect(self.export_spectrum)
        layout_export_ctrl.addWidget(self.btn_export)
        
        self.cb_incl_img = QCheckBox(cw)
        self.cb_incl_img.setChecked(True)
        self.cb_incl_img.setText('include rgb image')
        layout_export_ctrl.addWidget(self.cb_incl_img)

        self.cb_incl_graph = QCheckBox(cw)
        self.cb_incl_graph.setChecked(True)
        self.cb_incl_graph.setText('include graph image')
        layout_export_ctrl.addWidget(self.cb_incl_graph)


        # create statusbar (in case we need it at some point..)
        self.statusBar()

        # create menu
        menubar = self.menuBar()

        # file menu
        menu_file = menubar.addMenu('&File')

        action_load_data = menu_file.addAction('&Load HS data...')
        action_load_data.triggered.connect(self.handle_action_load_data)

        self.action_save_img = menu_file.addAction('&Save image...')
        self.action_save_img.setEnabled(False)
        self.action_save_img.triggered.connect(self.export_image)

        # analysis menu
        menu_analysis = menubar.addMenu('&Analysis')
        self.action_match_cube = menu_analysis.addAction('&Match whole image with database...')
        self.action_match_cube.setEnabled(False)
        self.action_match_cube.triggered.connect(self.match_cube)

        submenu_db = menu_analysis.addMenu('&Database management')
        action_create_db = submenu_db.addAction('&Create new database...')
        action_create_db.triggered.connect(self.create_db)
        submenu_db.addAction(action_create_db)


        # finito!
        self.show()

    ##############
    # UI updates
    ##############
    def reset_ui(self):
        self.cb_rgb.setChecked(True)
        self.sl_lambda.setValue(0)
        self.sl_lambda.setEnabled(False)
        self.lbl_lambda.setText('')
        if self.cube is not None:
            if len(self.cube.shape) > 2:
                self.sl_lambda.setMaximum(self.cube.shape[2])
        self.plot.reset()

    def set_image_label(self, img: np.array):
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
            self.lbl_img.setPixmap(qPixmap)

    ##################
    # loading HS data
    ##################
    def load_data(self, filename):
        try:
            self.cube = specim.read(filename)
            self.rgb = specim.cube2rgb(self.cube)
            self.reset_ui()
            self.set_image_label(self.rgb)
            self.rawfile = filename
            self.action_save_img.setEnabled(True)
            self.action_match_cube.setEnabled(True)
        except Exception as e:
            print("Error loading file: ")
            print(e)

    def handle_action_load_data(self):
        filename, _ = QFileDialog.getOpenFileName(None, "Select Specim Raw File", "", "Specim raw files (*.raw)")
        if filename:
            self.load_data(filename)

    def handle_drag_enter(self, e):
        if e.mimeData().hasUrls():
            e.accept()
        else:
            e.ignore()

    def handle_drop(self, e):
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
        self.load_data(filename)

    ####################
    # spectra operations
    ####################
    def handle_click_on_image(self, event):
        self.x = event.pos().x()
        self.y = event.pos().y()

        print("x=%d, y=%d" % (self.x, self.y))

        if 0 <= self.x < specim.cols and 0 <= self.y < specim.rows and self.cube is not None:
            self.spectrum = self.cube[self.y, self.x, :]
            self.plot.plot(specim.lambda_space, self.spectrum)

    def export_spectrum(self):
        if self.spectrum is not None:
            expdir = os.path.dirname(self.rawfile)
            basename = os.path.basename(self.rawfile).split('.')[0]
            expfile = os.path.join(expdir, "%s_(%d,%d).txt" % (basename, self.x, self.y))

            fileName, _ = QFileDialog.getSaveFileName(None, "Save spectrum", expfile, "All Files (*)")

            if fileName:
                data_x = np.float32(specim.lambda_space)
                data = np.transpose([data_x, self.spectrum])
                np.savetxt(fileName, data, fmt='%.4f', delimiter=', ')

                if self.cb_incl_img.isChecked() and self.rgb is not None:
                    img = np.copy(self.rgb)
                    rows, cols, _ = img.shape
                    img[self.y, max(self.x-CROSS_SIZE, 0):min(self.x+CROSS_SIZE+1, rows-1)] = [0, 1, 0]
                    img[max(self.y - CROSS_SIZE, 0):min(self.y + CROSS_SIZE+1, cols - 1), self.x] = [0, 1, 0]
                    img[img>1.0] = 1.0
                    base, ext = os.path.splitext(fileName)
                    matplotlib.image.imsave(base+'.png', img)

                if self.cb_incl_graph.isChecked():
                    base, ext = os.path.splitext(fileName)
                    self.plot.save(base+'_graph.png')

    ###################
    # image operations
    ###################
    def handle_cb_rgb_changed(self):
        if self.cb_rgb.isChecked():
            self.sl_lambda.setEnabled(False)
            self.lbl_lambda.setText('')
            if self.rgb is not None:
                self.set_image_label(self.rgb)
        else:
            self.sl_lambda.setEnabled(True)
            self.handle_sl_lambda_changed()

    def handle_sl_lambda_changed(self):
        layer = self.sl_lambda.value()
        if self.cube is not None:
            if 0 <= layer < self.cube.shape[2]:
                img = self.cube[:, :, layer]
                self.set_image_label(img)
                wl = specim.lambda_space[layer]
                self.lbl_lambda.setText('%.1fnm' % wl)

    def export_image(self):
        expdir = os.path.dirname(self.rawfile)
        basename = os.path.basename(self.rawfile).split('.')[0]
        if self.cb_rgb.isChecked():
            suffix = 'rgb'
        else:
            suffix = self.lbl_lambda.text()
        expfile = os.path.join(expdir, "%s_%s.png" % (basename, suffix))

        fileName, _ = QFileDialog.getSaveFileName(None, "Export image", expfile, "All Files (*)")
        if fileName:
            self.lbl_img.pixmap().save(fileName)

    ###########
    # analysis
    ###########
    def create_db(self):
        dirname, _ = QFileDialog.getExistingDirectory(None, "Select root directory for database creation", "")
        if dirname:
            Analysis.create_database(dirname, True)

    def match_cube(self):
        vis_dir = os.path.join(os.path.dirname(self.rawfile), '..', 'pigment_maps')
        self.anal.compare_cube_to_db(self.cube,
                                     use_gradient=True,
                                     squared_errs=True,
                                     vis_dir=vis_dir)


# main
if __name__ == "__main__":
    app = QApplication([])
    win = MainWindow()
    sys.exit(app.exec())

