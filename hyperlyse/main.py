import sys
import os
import numpy as np
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog
from PyQt5.QtWidgets import QWidget, QLabel, QCheckBox, QSlider, QPushButton, QComboBox
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout, QSpacerItem
import matplotlib.image
from matplotlib import pyplot as plt
from hyperlyse import specim, Analysis, PlotCanvas


# config
DEFAULT_DB_FILE = 'Worco_medium_poster_spectra-db.json'

class DisplayMode:
    RGB = 0
    LAYERS = 1
    SIMILARITY = 2

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        # data members
        self.cube = None
        self.rgb = None
        self.similarity_map = None
        self.similarity_ref_spectrum = []
        self.similarity_use_gradient = False
        self.x = -1
        self.y = -1
        self.spectrum = None
        self.rawfile = None

        self.anal = Analysis()
        self.anal.load_db(DEFAULT_DB_FILE)


        ##########
        # setup ui
        ##########
        self.setWindowTitle('Hyperlyse')

        ### central widget and outer layout
        cw = QWidget(self)
        self.setCentralWidget(cw)
        layout_outer = QHBoxLayout(cw)
        cw.setLayout(layout_outer)

        ### image display
        layout_img = QVBoxLayout(cw)
        layout_outer.addLayout(layout_img)

        self.lbl_img = QLabel(cw)
        img_startup = QPixmap()
        img_startup.load('startup.png')
        self.lbl_img.setPixmap(img_startup)
        self.lbl_img.mousePressEvent = self.handle_click_on_image
        self.lbl_img.setAcceptDrops(True)
        self.lbl_img.dragEnterEvent = self.handle_drag_enter
        self.lbl_img.dropEvent = self.handle_drop
        layout_img.addWidget(self.lbl_img)

        layout_img_ctrl = QHBoxLayout(cw)
        layout_img.addLayout(layout_img_ctrl)

        lbl_img_display = QLabel(cw)
        lbl_img_display.setText('Display:')
        layout_img_ctrl.addWidget(lbl_img_display)

        self.cmb_mode = QComboBox(cw)
        self.cmb_mode.addItem('RGB', DisplayMode.RGB)
        self.cmb_mode.addItem('layers', DisplayMode.LAYERS)
        self.cmb_mode.addItem('similarity', DisplayMode.SIMILARITY)
        self.cmb_mode.setCurrentIndex(0)
        self.cmb_mode.currentIndexChanged.connect(self.update_image_label)
        layout_img_ctrl.addWidget(self.cmb_mode)

        self.sl_lambda = QSlider(cw)
        self.sl_lambda.setOrientation(Qt.Horizontal)
        self.sl_lambda.setVisible(False)
        self.sl_lambda.valueChanged.connect(self.update_image_label)
        self.sl_lambda.setMinimumWidth(300)
        layout_img_ctrl.addWidget(self.sl_lambda)

        self.cmb_reference = QComboBox(cw)
        self.cmb_reference.addItem('SELECTED PIXEL', -1)
        for s, i in zip(self.anal.db, range(len(self.anal.db))):
            self.cmb_reference.addItem(s['name'], i)
        self.cmb_reference.setVisible(False)
        self.cmb_reference.currentIndexChanged.connect(self.update_image_label)
        layout_img_ctrl.addWidget(self.cmb_reference)

        self.cb_similarity_gradient = QCheckBox(cw)
        self.cb_similarity_gradient.setChecked(False)
        self.cb_similarity_gradient.setText('compare gradients')
        self.cb_similarity_gradient.setVisible(False)
        self.cb_similarity_gradient.stateChanged.connect(self.update_image_label)
        layout_img_ctrl.addWidget(self.cb_similarity_gradient)

        self.lbl_lambda = QLabel(cw)
        layout_img_ctrl.addWidget(self.lbl_lambda)

        layout_img_ctrl.addStretch()


        ### specrtra display
        layout_spectra = QVBoxLayout(cw)
        layout_outer.addLayout(layout_spectra)

        # db search controls
        layout_search_ctrls = QHBoxLayout(self)
        layout_spectra.addLayout(layout_search_ctrls)

        self.cb_spectra_search = QCheckBox(cw)
        self.cb_spectra_search.setText('Show similar spectra')
        self.cb_spectra_search.stateChanged.connect(self.update_spectrum_plot)
        layout_search_ctrls.addWidget(self.cb_spectra_search)

        self.cb_squared = QCheckBox(self)
        self.cb_squared.setText('squared errors')
        self.cb_squared.setChecked(True)
        self.cb_squared.setEnabled(False)
        self.cb_squared.stateChanged.connect(self.update_spectrum_plot)
        layout_search_ctrls.addWidget(self.cb_squared)

        self.cb_gradient = QCheckBox(self)
        self.cb_gradient.setText('compare gradients')
        self.cb_gradient.setChecked(False)
        self.cb_gradient.setEnabled(False)
        self.cb_gradient.stateChanged.connect(self.update_spectrum_plot)
        layout_search_ctrls.addWidget(self.cb_gradient)

        self.lbl_nspectra = QLabel(self)
        self.lbl_nspectra.setText('number of spectra:')
        self.lbl_nspectra.setEnabled(False)
        layout_search_ctrls.addWidget(self.lbl_nspectra)

        self.sl_nspectra = QSlider(self)
        self.sl_nspectra.setMinimum(1)
        self.sl_nspectra.setMaximum(10)
        self.sl_nspectra.setOrientation(Qt.Horizontal)
        self.sl_nspectra.setValue(3)
        self.sl_nspectra.valueChanged.connect(self.update_spectrum_plot)
        self.sl_nspectra.setEnabled(False)
        layout_search_ctrls.addWidget(self.sl_nspectra)

        # plot canvas
        self.plot = PlotCanvas(cw)
        layout_spectra.addWidget(self.plot)

        # export controls
        layout_export_ctrl = QHBoxLayout(cw)
        layout_spectra.addLayout(layout_export_ctrl)

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


        ### statusbar
        #self.statusBar().showMessage('Ready')
        # self.progress_bar = QProgressBar(cw)
        # self.progress_bar.setFixedHeight(10)
        # self.progress_bar.setValue(0)
        # self.statusBar().addPermanentWidget(self.progress_bar)

        ### create menu
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
        # self.action_match_cube = menu_analysis.addAction('&Match whole image with database')
        # self.action_match_cube.setEnabled(False)
        # self.action_match_cube.triggered.connect(self.match_cube)

        submenu_db = menu_analysis.addMenu('&Database management')
        action_load_db = submenu_db.addAction('&Load database from .json...')
        action_load_db.triggered.connect(self.handle_action_load_db)
        action_create_db = submenu_db.addAction('&Create new database...')
        action_create_db.triggered.connect(self.handle_action_create_db)


        # additional windows (define here for better readability only)
        self.match_point_win = None

        # finito!
        self.show()

    ##############
    # UI updates
    ##############
    def reset_ui(self):
        self.x = self.y = -1
        self.cmb_mode.setCurrentIndex(0)
        self.sl_lambda.setValue(0)
        self.sl_lambda.setVisible(False)
        self.lbl_lambda.setText('')
        self.cmb_reference.setVisible(False)
        self.cb_similarity_gradient.setVisible(False)
        if self.cube is not None:
            if len(self.cube.shape) > 2:
                self.sl_lambda.setMaximum(self.cube.shape[2])
        self.plot.reset()

    def update_image_label(self):
        img = None
        # handle img checkbox and lambda slider
        if self.cmb_mode.currentData() == DisplayMode.RGB:
            self.sl_lambda.setVisible(False)
            self.lbl_lambda.setText('')
            self.cmb_reference.setVisible(False)
            self.cb_similarity_gradient.setVisible(False)
            if self.rgb is not None:
                img = self.rgb

        elif self.cmb_mode.currentData() == DisplayMode.LAYERS:
            self.sl_lambda.setVisible(True)
            self.cmb_reference.setVisible(False)
            self.cb_similarity_gradient.setVisible(False)
            layer = self.sl_lambda.value()
            if self.cube is not None:
                if 0 <= layer < self.cube.shape[2]:
                    img = self.cube[:, :, layer]
                    self.lbl_lambda.setText('%.1fnm' % specim.lambda_space[layer])

        elif self.cmb_mode.currentData() == DisplayMode.SIMILARITY:
            self.sl_lambda.setVisible(False)
            self.lbl_lambda.setText('')
            self.cmb_reference.setVisible(True)
            self.cb_similarity_gradient.setVisible(True)
            ref_spec = None
            if self.cmb_reference.currentData() == -1:
                if self.spectrum is not None:
                    ref_spec = self.spectrum
            else:
                ref_spec = self.anal.db[self.cmb_reference.currentData()]['spectrum']
            if ref_spec is not None and self.cube is not None:
                # do we have to recompute the similarity map?
                if list(ref_spec) != list(self.similarity_ref_spectrum) \
                        or self.cb_similarity_gradient.isChecked() != self.similarity_use_gradient:
                    self.similarity_ref_spectrum = ref_spec
                    self.similarity_use_gradient = self.cb_similarity_gradient.isChecked()
                    sim_map = self.anal.compare_cube_to_spectrum(self.cube,
                                                                 ref_spec,
                                                                 use_gradient=self.cb_similarity_gradient.isChecked())
                    cm = plt.get_cmap('viridis')
                    self.similarity_map = cm(sim_map)[:, :, :3]
                img = self.similarity_map


        if img is not None:
            if self.x != -1 != self.y:
                img = self.draw_cross(img, self.x, self.y)

            # float to normalized 8 bit
            img = np.uint8(img * (255 / img.max()))
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

    def update_spectrum_plot(self):
        search_enabled = self.cb_spectra_search.isChecked()
        self.cb_gradient.setEnabled(search_enabled)
        self.cb_squared.setEnabled(search_enabled)
        self.lbl_nspectra.setEnabled(search_enabled)
        self.sl_nspectra.setEnabled(search_enabled)

        if self.spectrum is not None:
            self.plot.plot(specim.lambda_space,
                           self.spectrum,
                           label='query',
                           hold=False)

            if search_enabled:
                result = self.anal.search_spectrum(self.spectrum,
                                                   use_gradient=self.cb_gradient.isChecked(),
                                                   squared_errs=self.cb_squared.isChecked())
                for s in result[:self.sl_nspectra.value()]:
                    self.plot.plot(specim.lambda_space,
                                   s['spectrum'],
                                   label='%s (e=%.3f)' % (s['name'], s['error']),
                                   linewidth=1,
                                   hold=True)

    ##################
    # loading HS data
    ##################
    def load_data(self, filename):
        try:
            self.cube = specim.read(filename)
            self.rgb = specim.cube2rgb(self.cube)
            self.reset_ui()
            self.update_image_label()
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

    #############################
    # image & spectra operations
    #############################
    def handle_click_on_image(self, event):
        self.x = event.pos().x()
        self.y = event.pos().y()

        print("x=%d, y=%d" % (self.x, self.y))

        if 0 <= self.x < specim.cols and 0 <= self.y < specim.rows and self.cube is not None:
            self.spectrum = self.cube[self.y, self.x, :]
            self.update_image_label()
            self.update_spectrum_plot()

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
                    img = self.draw_cross(self.rgb, self.x, self.y)
                    base, ext = os.path.splitext(fileName)
                    matplotlib.image.imsave(base+'.png', img)

                if self.cb_incl_graph.isChecked():
                    base, ext = os.path.splitext(fileName)
                    self.plot.save(base+'_graph.png')

    def export_image(self):
        expdir = os.path.dirname(self.rawfile)
        basename = os.path.basename(self.rawfile).split('.')[0]
        if self.cmb_mode.currentData() == DisplayMode.RGB:
            suffix = 'rgb'
        elif self.cmb_mode.currentData() == DisplayMode.LAYERS:
            suffix = self.lbl_lambda.text()
        expfile = os.path.join(expdir, "%s_%s.png" % (basename, suffix))

        fileName, _ = QFileDialog.getSaveFileName(None, "Export image", expfile, "All Files (*)")
        if fileName:
            self.lbl_img.pixmap().save(fileName)

    def draw_cross(self, img_in: np.array, x, y, size=5,
                   color_h=(0, 1, 0), color_v=(1, 0, 0), color_c=(0, 0, 1)):
        """
        Creates a copy of img_in with a cross drawn onto it at given position
        :param img_in:
        :param x:
        :param y:
        :param size:
        :param color:
        :return:
        """
        img = np.copy(img_in)
        rows = img.shape[0]
        cols = img.shape[1]
        if len(img.shape) == 2:
            img = np.dstack([img, img, img])
        if 0 < x < cols and 0 < y < rows:
            img[y, max(x - size, 0):min(x + size + 1, rows - 1)] = color_v
            img[max(y - size, 0):min(y + size + 1, cols - 1), x] = color_h
            img[y, x] = color_c
        else:
            print('warning: invalid x and y given to draw_cross. returning original image.')
        return img

    ###########
    # analysis
    ###########
    def handle_action_create_db(self):
        dirname, _ = QFileDialog.getExistingDirectory(None, "Select root directory for database creation", "")
        if dirname:
            Analysis.create_database(dirname, True)

    def handle_action_load_db(self):
        filename, _ = QFileDialog.getOpenFileName(None, "Select file containing reference spectra",
                                                  "", "json files (*.json)")
        if filename:
            self.anal.load_db(filename)

    def match_cube(self):
        vis_dir = os.path.join(os.path.dirname(self.rawfile), '..', 'pigment_maps')
        self.anal.compare_cube_to_db(self.cube,
                                     use_gradient=False,
                                     squared_errs=True,
                                     vis_dir=vis_dir)


# main
if __name__ == "__main__":
    app = QApplication([])
    win = MainWindow()
    sys.exit(app.exec())

