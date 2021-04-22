import sys
import os
import numpy as np
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QInputDialog, QMessageBox
from PyQt5.QtWidgets import QWidget, QLabel, QCheckBox, QSlider, QPushButton, QComboBox, QFrame
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout, QTabWidget, QScrollArea, QSizePolicy, QDesktopWidget
import matplotlib.image
from matplotlib import pyplot as plt
from hyperlyse import SpecimIQ, Analysis, PlotCanvas
import collections

# config
__version__ = "1.1"
INFOTEXT = "\n".join(["Hyperlyse",
                      "Version: %s" % __version__,
                      "Author: Simon Brenner",
                      "Institution: Computer Vision Lab, TU Wien",
                      "License: CC-BY-NC-SA"])


DEFAULT_DB_FILE = 'Worco_medium_poster_spectra-db.json'


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        # data members
        self.cube = None
        self.rgb = None
        self.error_map = None
        self.error_map_ref_spectrum = []
        self.error_map_use_gradient = False
        self.x = -1
        self.y = -1
        self.spectrum = None
        self.rawfile = None

        self.zoom = 1.0
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.drag_start_hs_v = 0
        self.drag_start_vs_v = 0

        self.anal = Analysis()
        self.anal.load_db(DEFAULT_DB_FILE)


        ##########
        # setup ui
        ##########
        self.setWindowTitle('Hyperlyse v%s' % __version__)

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
        self.scroll_img = QScrollArea(cw)
        self.scroll_img.setWidget(self.lbl_img)
        self.scroll_img.mousePressEvent = self.handle_click_on_image_scroll
        self.scroll_img.mouseMoveEvent = self.handle_move_on_image
        self.scroll_img.wheelEvent = self.handle_wheel_on_image
        layout_img.addWidget(self.scroll_img)

        layout_zoom = QHBoxLayout(cw)
        layout_img.addLayout(layout_zoom)
        lbl_zoom = QLabel('Zoom:')
        lbl_zoom.setFixedWidth(40)
        layout_zoom.addWidget(lbl_zoom)
        self.cmb_zoom = QComboBox(cw)
        self.cmb_zoom.addItem('100%', 1)
        self.cmb_zoom.addItem('200%', 2)
        self.cmb_zoom.addItem('400%', 4)
        self.cmb_zoom.addItem('800%', 8)
        self.cmb_zoom.addItem('1600%', 16)
        self.cmb_zoom.currentIndexChanged.connect(self.update_image_label)
        layout_zoom.addWidget(self.cmb_zoom)

        # image controls
        layout_img_ctrl = QHBoxLayout(cw)
        layout_img.addLayout(layout_img_ctrl)

        lbl_img_display = QLabel(cw)
        lbl_img_display.setText('Mode:')
        lbl_img_display.setFixedWidth(40)
        layout_img_ctrl.addWidget(lbl_img_display)

        self.tabs_img_ctrl = QTabWidget(cw)
        self.tabs_img_ctrl.currentChanged.connect(self.update_image_label)
        self.tabs_img_ctrl.setSizePolicy(QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum))
        layout_img_ctrl.addWidget(self.tabs_img_ctrl)

        # RGB -> index 0
        tab_rgb = QWidget()
        tab_rgb.setLayout(QHBoxLayout())
        self.tabs_img_ctrl.addTab(tab_rgb, 'RGB')

        lbl_rgb = QLabel(tab_rgb)
        lbl_rgb.setText('Shows an RGB representation of the Hyperspectral cube.')
        tab_rgb.layout().addWidget(lbl_rgb)

        # layers -> index 1
        tab_layers = QWidget()
        tab_layers.setLayout(QHBoxLayout())
        self.tabs_img_ctrl.addTab(tab_layers, 'layers')

        lbl_layers = QLabel(tab_layers)
        lbl_layers.setText('Select layer:')
        tab_layers.layout().addWidget(lbl_layers)

        self.sl_lambda = QSlider(tab_layers)
        self.sl_lambda.setOrientation(Qt.Horizontal)
        self.sl_lambda.valueChanged.connect(self.update_image_label)
        self.sl_lambda.setMinimumWidth(300)
        self.sl_lambda.setValue(0)
        tab_layers.layout().addWidget(self.sl_lambda)

        self.lbl_lambda = QLabel(tab_layers)
        self.lbl_lambda.setText(self.get_lambda_slider_text(0))
        tab_layers.layout().addWidget(self.lbl_lambda)

        # similarity -> index 2
        tab_similarity = QWidget()
        tab_similarity.setLayout(QHBoxLayout())
        self.tabs_img_ctrl.addTab(tab_similarity, 'similarity')

        self.cmb_reference = QComboBox(tab_similarity)
        self.cmb_reference.addItem('SELECTED PIXEL', -1)
        for s, i in zip(self.anal.db, range(len(self.anal.db))):
            self.cmb_reference.addItem(s['name'], i)
        self.cmb_reference.currentIndexChanged.connect(self.update_image_label)
        tab_similarity.layout().addWidget(self.cmb_reference)

        self.cb_similarity_gradient = QCheckBox(tab_similarity)
        self.cb_similarity_gradient.setChecked(False)
        self.cb_similarity_gradient.setText('compare gradients')
        self.cb_similarity_gradient.stateChanged.connect(self.update_image_label)
        tab_similarity.layout().addWidget(self.cb_similarity_gradient)

        lbl_sim_t = QLabel(tab_similarity)
        lbl_sim_t.setText('t=')
        tab_similarity.layout().addWidget(lbl_sim_t)

        self.sl_sim_t = QSlider(tab_similarity)
        self.sl_sim_t.setOrientation(Qt.Horizontal)
        self.sl_sim_t.setMinimum(0)
        self.sl_sim_t.setMaximum(99)
        self.sl_sim_t.setValue(0)
        self.sl_sim_t.valueChanged.connect(self.update_image_label)
        tab_similarity.layout().addWidget(self.sl_sim_t)

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

        btn_export = QPushButton(cw)
        btn_export.setText('Export Spectrum')
        btn_export.clicked.connect(self.handle_action_export_spectrum)
        layout_export_ctrl.addWidget(btn_export)
        
        self.cb_incl_img = QCheckBox(cw)
        self.cb_incl_img.setChecked(True)
        self.cb_incl_img.setText('include rgb image')
        layout_export_ctrl.addWidget(self.cb_incl_img)

        self.cb_incl_graph = QCheckBox(cw)
        self.cb_incl_graph.setChecked(True)
        self.cb_incl_graph.setText('include graph image')
        layout_export_ctrl.addWidget(self.cb_incl_graph)

        sep = QFrame(cw)
        sep.setFrameShape(QFrame.VLine)
        sep.setFrameShadow(QFrame.Sunken)
        layout_export_ctrl.addWidget(sep)

        btn_add_to_db = QPushButton(cw)
        btn_add_to_db.setText('Add to DB..')
        btn_add_to_db.clicked.connect(self.handle_btn_add_to_db_clicked)
        layout_export_ctrl.addWidget(btn_add_to_db)


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

        action_export_spectrum = menu_file.addAction('&Export spectrum...')
        action_export_spectrum.triggered.connect(self.handle_action_export_spectrum)


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

        # info menu
        menu_info = menubar.addMenu('&?')
        action_info = menu_info.addAction('&Show info')
        action_info.triggered.connect(self.show_info)

        # additional windows (define here for better readability only)
        self.match_point_win = None

        # finito!
        screensize = QDesktopWidget().availableGeometry(self).size() * 0.9
        self.resize(min(screensize.width(), 1064), min(screensize.height(), 652))
        self.show()

    def show_info(self):
        mb = QMessageBox(QMessageBox.Information,
                         "About this software",
                         INFOTEXT,
                         QMessageBox.Close)
        mb.exec()


    ##############
    # UI updates
    ##############
    def reset_ui(self):
        self.x = self.y = -1
        self.error_map = None
        self.error_map_ref_spectrum = []
        self.error_map_use_gradient = False
        self.tabs_img_ctrl.setCurrentIndex(0)
        self.sl_lambda.setValue(0)
        self.lbl_lambda.setText(self.get_lambda_slider_text(0))
        if self.cube is not None:
            if len(self.cube.shape) > 2:
                self.sl_lambda.setMaximum(self.cube.shape[2])
        self.plot.reset()

    def update_image_label(self):
        img = None
        # handle img checkbox and lambda slider
        if self.tabs_img_ctrl.currentIndex() == 0:
            if self.rgb is not None:
                img = self.rgb

        elif self.tabs_img_ctrl.currentIndex() == 1:
            layer = self.sl_lambda.value()
            if self.cube is not None:
                if 0 <= layer < self.cube.shape[2]:
                    img = self.cube[:, :, layer]
                    self.lbl_lambda.setText(self.get_lambda_slider_text(layer))

        elif self.tabs_img_ctrl.currentIndex() == 2:
            ref_spec = None
            if self.cmb_reference.currentData() == -1:
                if self.spectrum is not None:
                    ref_spec = self.spectrum
            else:
                ref_spec = self.anal.db[self.cmb_reference.currentData()]['spectrum']
            if ref_spec is not None and self.cube is not None:
                # do we have to recompute the similarity map?
                if list(ref_spec) != list(self.error_map_ref_spectrum) \
                        or self.cb_similarity_gradient.isChecked() != self.error_map_use_gradient:
                    self.error_map_ref_spectrum = ref_spec
                    self.error_map_use_gradient = self.cb_similarity_gradient.isChecked()
                    self.error_map = self.anal.compare_cube_to_spectrum(self.cube,
                                                                        ref_spec,
                                                                        use_gradient=self.cb_similarity_gradient.isChecked())

                err_map_t = self.error_map.copy()
                t = (100-self.sl_sim_t.value())/100*err_map_t.max()
                err_map_t[err_map_t > t] = t
                img = self.visualize_error_map(err_map_t)


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
                scale = self.cmb_zoom.currentData()
                qPixmap = qPixmap.scaled(width*scale, height*scale, transformMode=Qt.FastTransformation)
                self.lbl_img.setPixmap(qPixmap)
                self.lbl_img.resize(width*scale, height*scale)

    def update_spectrum_plot(self):
        search_enabled = self.cb_spectra_search.isChecked()
        self.cb_gradient.setEnabled(search_enabled)
        self.cb_squared.setEnabled(search_enabled)
        self.lbl_nspectra.setEnabled(search_enabled)
        self.sl_nspectra.setEnabled(search_enabled)

        if self.spectrum is not None:
            self.plot.plot(SpecimIQ.lambda_space,
                           self.spectrum,
                           label='query',
                           hold=False)

            if search_enabled:
                result = self.anal.search_spectrum(self.spectrum,
                                                   use_gradient=self.cb_gradient.isChecked(),
                                                   squared_errs=self.cb_squared.isChecked())
                for s in result[:self.sl_nspectra.value()]:
                    self.plot.plot(SpecimIQ.lambda_space,
                                   s['spectrum'],
                                   label='%s (e=%.3f)' % (s['name'], s['error']),
                                   linewidth=1,
                                   hold=True)

    ##################
    # loading HS data
    ##################
    def load_data(self, filename):
        try:
            self.cube = SpecimIQ.read(filename)
            self.rgb = SpecimIQ.cube2rgb(self.cube)
            self.reset_ui()
            self.update_image_label()
            self.rawfile = filename
            self.action_save_img.setEnabled(True)
            #self.action_match_cube.setEnabled(True)
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
        if event.buttons() == Qt.LeftButton:
            self.x = int(event.pos().x() / self.cmb_zoom.currentData())
            self.y = int(event.pos().y() / self.cmb_zoom.currentData())
            print("Selected point: (%d, %d)" % (self.x, self.y))

            if 0 <= self.x < SpecimIQ.cols and 0 <= self.y < SpecimIQ.rows and self.cube is not None:
                self.spectrum = self.cube[self.y, self.x, :]
                self.update_image_label()
                self.update_spectrum_plot()
        else:
            event.ignore()

    def handle_click_on_image_scroll(self, event):
        if event.buttons() == Qt.RightButton:
            self.drag_start_x = event.pos().x()
            self.drag_start_y = event.pos().y()
            self.drag_start_hs_v = self.scroll_img.horizontalScrollBar().value()
            self.drag_start_vs_v = self.scroll_img.verticalScrollBar().value()
        else:
            event.ignore()

    def handle_move_on_image(self, event):
        if event.buttons() == Qt.RightButton:
            hs_max = self.scroll_img.horizontalScrollBar().maximum()
            vs_max = self.scroll_img.verticalScrollBar().maximum()
            hs_min = self.scroll_img.horizontalScrollBar().minimum()
            vs_min = self.scroll_img.verticalScrollBar().minimum()

            dh = (self.drag_start_x - event.x())
            dv = (self.drag_start_y - event.y())

            self.scroll_img.horizontalScrollBar().setValue(min(hs_max, max(hs_min, self.drag_start_hs_v+dh)))
            self.scroll_img.verticalScrollBar().setValue(min(vs_max, max(vs_min, self.drag_start_vs_v+dv)))

    def handle_wheel_on_image(self, event):
        if self.scroll_img.horizontalScrollBar().maximum() > 0:
            hs_r = self.scroll_img.horizontalScrollBar().value() / self.scroll_img.horizontalScrollBar().maximum()
        else:
            hs_r = 0.5
        if self.scroll_img.verticalScrollBar().maximum() > 0:
            vs_r = self.scroll_img.verticalScrollBar().value() / self.scroll_img.verticalScrollBar().maximum()
        else:
            vs_r = 0.5
        self.cmb_zoom.setCurrentIndex(max(0,
                                          min(self.cmb_zoom.count()-1,
                                              self.cmb_zoom.currentIndex()+np.sign(event.angleDelta().y())
                                              )
                                          )
                                      )
        self.scroll_img.horizontalScrollBar().setValue(int(self.scroll_img.verticalScrollBar().maximum() * hs_r))
        self.scroll_img.verticalScrollBar().setValue(int(self.scroll_img.verticalScrollBar().maximum() * vs_r))

    def handle_action_export_spectrum(self):
        if self.spectrum is not None:
            expdir = os.path.dirname(self.rawfile)
            basename = os.path.basename(self.rawfile).split('.')[0]
            expfile = os.path.join(expdir, "%s_(%d,%d).jdx" % (basename, self.x, self.y))

            fileName, _ = QFileDialog.getSaveFileName(None, "Save spectrum", expfile,
                                                      "JCAMP-DX (*.jdx *.dx *jcm);;Plain x,y pairs (*.dpt *.csv *.txt )")
            if fileName:
                valid = False
                if os.path.splitext(fileName)[1] in ['.dx', '.jdx', '.jcm']:
                    self.export_jcamp(fileName)
                    valid = True
                elif os.path.splitext(fileName)[1] in ['.dpt', '.txt', '.csv']:
                    self.export_dpt(fileName)
                    valid = True

                if valid:
                    if self.cb_incl_img.isChecked() and self.rgb is not None:
                        img = self.draw_cross(self.rgb, self.x, self.y)
                        base, ext = os.path.splitext(fileName)
                        matplotlib.image.imsave(base + '.png', img)

                    if self.cb_incl_graph.isChecked():
                        base, ext = os.path.splitext(fileName)
                        self.plot.save(base + '_graph.png')
                else:
                    print('warning: invalid file extension given. spectrum not saved. allowed: '
                          '.dpt, .txt (plain comma-separated x,y values), .dx, .jdx, .jcm (JCAMP-DX)')

    def export_dpt(self, fileName):
        data_x = np.float32(SpecimIQ.lambda_space)
        data = np.transpose([data_x, self.spectrum])
        np.savetxt(fileName, data, fmt='%.4f', delimiter=',')

    def export_jcamp(self, fileName):
        # prepare output file content
        data = collections.OrderedDict()  # in jcamp, order of elements is kind of important..
        data['##TITLE'] = '%s, position (%d, %d)' % (os.path.basename(self.rawfile).split('.')[0], self.x, self.y)
        data['##JCAMP-DX'] = "5.1"
        data['##DATA TYPE'] = "UV/VIS SPECTRUM"
        data['##ORIGIN'] = "CIMA"
        data['##OWNER'] = "CIMA"

        data['##DATA CLASS'] = 'XYDATA'
        data['##SPECTROMETER/DATASYSTEM'] = "SpecimIQ/Hyperlyse%s" % __version__
        ##INSTRUMENTAL PARAMETERS=(STRING).This optional field is a list of pertinent instrumental settings. Only
        # settings which are essential for applications should be included.
        data['##SAMPLING PROCEDURE'] = "MODE=reflection"
        # First entry in this field should be MODE of observation (transmission,
        # specular reflection, PAS, matrix isolation, photothermal beam deflection, etc.), followed by appropriate
        # additional information, i.e., name and model of accessories, cell thickness, and window material for
        # fixed liquid cells, ATR plate material, angle and cone of incidence, and effective number of reflections
        # for ATR measurements, polarization, and special modulation techniques, as discussed by Grasselli et al.
        # data['##DATA PROCESSING'] = ""
        # (TEXT). Description of background correction, smoothing, subtraction,
        # deconvolution procedures, apodization function, zero - fill, or other data processing, together
        # with reference to original spectra used for subtractions.

        vx = np.float32(SpecimIQ.lambda_space)
        vy = self.spectrum

        data['##DELTAX'] = (vx[-1] - vx[0]) / (len(vx) - 1)
        data['##XUNITS'] = "NANOMETERS"
        data['##YUNITS'] = "REFLECTANCE"
        data['##XFACTOR'] = 1.0
        data['##YFACTOR'] = 1.0

        data['##FIRSTX'] = vx[0]
        data['##LASTX'] = vx[-1]
        data['##NPOINTS'] = len(vx)
        data['##FIRSTY'] = vy[0]
        data['##XYDATA'] = [xy for xy in zip(vx, vy)]

        data['##END'] = ''

        # write the file
        if not os.path.isdir(os.path.dirname(fileName)):
            os.makedirs(os.path.dirname(fileName))
        with open(fileName, 'w') as f:
            for k, v in data.items():
                if k == "##XYDATA":
                    f.write('##XYDATA= (X++(Y..Y))\n')
                    for x, y in v:
                        f.write('%s %s\n' % (str(x), str(y)))
                else:
                    f.write('%s= %s\n' % (k.replace('_', ' '), str(v)))

    def export_image(self):
        expdir = os.path.dirname(self.rawfile)
        basename = os.path.basename(self.rawfile).split('.')[0]
        if self.tabs_img_ctrl.currentIndex() == 0:
            suffix = 'rgb'
        elif self.tabs_img_ctrl.currentIndex() == 1:
            suffix = self.lbl_lambda.text()
        elif self.tabs_img_ctrl.currentIndex() == 2:
            if self.cmb_reference.currentData() == -1:
                suffix = 'sim(%d,%d)' % (self.x, self.y)
            else:
                suffix = 'sim(%s)' % self.cmb_reference.currentText()
        expfile = os.path.join(expdir, "%s_%s.png" % (basename, suffix))

        fileName, _ = QFileDialog.getSaveFileName(None, "Export image", expfile, "All Files (*)")
        if fileName:
            self.lbl_img.pixmap().save(fileName)

    def handle_btn_add_to_db_clicked(self):
        if self.spectrum is not None:
            name, ok = QInputDialog.getText(self,
                                            'Add spectrum to database',
                                            'sample name: ')
            if ok and name:
                if name in [n['name'] for n in self.anal.db]:
                    answer = QMessageBox.question(self,
                                                  'Name already exists!',
                                                  'A sample with the name %s already exists in the database. Overwrite?' % name
                                                  )
                    if answer == QMessageBox.Yes:
                        self.anal.add_to_db(name, self.spectrum)
                        self.anal.save_db()
                        self.cmb_reference.addItem(name, len(self.anal.db) - 1)

                else:
                    self.anal.add_to_db(name, self.spectrum)
                    self.anal.save_db()
                    self.cmb_reference.addItem(name, len(self.anal.db)-1)



    ###########
    # analysis
    ###########
    def handle_action_create_db(self):
        dirname = QFileDialog.getExistingDirectory(None, "Select root directory for database creation", "")
        if dirname:
            Analysis.create_database(dirname, True)

    def handle_action_load_db(self):
        filename, _ = QFileDialog.getOpenFileName(None, "Select file containing reference spectra",
                                                  "", "json files (*.json)")
        if filename:
            self.anal.load_db(filename)

    # def match_cube(self):
    #     vis_dir = os.path.join(os.path.dirname(self.rawfile), '..', 'pigment_maps')
    #     self.anal.compare_cube_to_db(self.cube,
    #                                  use_gradient=False,
    #                                  squared_errs=True,
    #                                  vis_dir=vis_dir)

    ###########
    # helpers
    ###########
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

    def get_lambda_slider_text(self, layer_idx):
        return '%.1fnm' % SpecimIQ.lambda_space[layer_idx]

    def visualize_error_map(self, error_map):
        # invert and map to [0, 1]:
        similarity_map = 1 - (error_map / error_map.max())
        # apply color map
        cm = plt.get_cmap('viridis')
        return cm(similarity_map)[:, :, :3]



# main
if __name__ == "__main__":
    app = QApplication([])
    win = MainWindow()
    sys.exit(app.exec())

