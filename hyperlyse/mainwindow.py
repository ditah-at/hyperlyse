import os
import numpy as np
import numbers
from PyQt6.QtGui import QPixmap, QImage, QGuiApplication
from PyQt6.QtCore import Qt, QUrl, QRect, QPoint, QSize
from PyQt6.QtWidgets import QMainWindow, QFileDialog, QInputDialog, QMessageBox, QRubberBand, QDoubleSpinBox
from PyQt6.QtWidgets import QWidget, QLabel, QCheckBox, QSlider, QPushButton, QComboBox, QSpinBox, QFrame
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QGridLayout, QTabWidget, QScrollArea, QSizePolicy
import matplotlib.image
from matplotlib import pyplot as plt
from hyperlyse import Database, PlotCanvas, Cube, principal_component_analysis, Exports, QRangeSlider

hyper_quotes = ['"Hyper, hyper. We need the bass drum." - H.P. Baxxter',
                '"Travelling through hyper space ain\'t like dusting crops, boy!" - Han Solo']

class MainWindow(QMainWindow):
    def __init__(self, config, rawfile=None):
        super(MainWindow, self).__init__(None)

        self.config=config

        # data members
        self.cube = None
        self.rgb = None
        self.pca = None
        self.error_map = None
        self.error_map_recompute_flag = True    # do we have to recompute the error map?
        self.point_selection = None
        self.rect_selection = None
        self.spectrum = None
        self.rawfile = rawfile

        self.zoom = 1.0
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.drag_start_hs_v = 0
        self.drag_start_vs_v = 0

        self.db = Database()
        self.db.load_db(self.config.default_db_file)

        ########################
        ########################
        ####### setup ui #######
        ########################
        ########################
        self.setWindowTitle('Hyperlyse v%s' % self.config.version)

        ### central widget and outer layout
        cw = QWidget(self)
        self.setCentralWidget(cw)
        layout_outer = QHBoxLayout(cw)
        cw.setLayout(layout_outer)

        #####################
        ### image display ###
        #####################

        layout_img = QVBoxLayout(cw)
        layout_outer.addLayout(layout_img)

        self.lbl_img = QLabel(cw)
        self.lbl_img.mousePressEvent = self.handle_click_on_image
        self.lbl_img.mouseMoveEvent = self.handle_move_on_image
        self.lbl_img.mouseReleaseEvent = self.handle_release_on_image
        self.lbl_img.setAcceptDrops(True)
        self.lbl_img.dragEnterEvent = self.handle_drag_enter
        self.lbl_img.dropEvent = self.handle_drop
        self.rubberband_selector = QRubberBand(QRubberBand.Shape.Rectangle, self.lbl_img)
        self.rubberband_origin = QPoint(0, 0)
        self.rubberband_selector.setGeometry(QRect(0, 0, 0, 0))
        self.scroll_img = QScrollArea(cw)
        self.scroll_img.setWidget(self.lbl_img)
        self.scroll_img.mousePressEvent = self.handle_click_on_image_scroll
        self.scroll_img.mouseMoveEvent = self.handle_move_on_image_scroll
        self.scroll_img.wheelEvent = self.handle_wheel_on_image_scroll
        layout_img.addWidget(self.scroll_img)

        # viewing controls
        layout_img_ctrl = QGridLayout(cw)
        layout_img.addLayout(layout_img_ctrl)
        lbl_zoom_static = QLabel('Zoom:')
        layout_img_ctrl.addWidget(lbl_zoom_static, 0, 0)
        self.sl_zoom = QSlider(cw)
        self.sl_zoom.setOrientation(Qt.Orientation.Horizontal)
        self.sl_zoom.setMinimum(25)
        self.sl_zoom.setMaximum(800)
        self.sl_zoom.setValue(100)
        self.sl_zoom.valueChanged.connect(self.update_image_label)
        layout_img_ctrl.addWidget(self.sl_zoom, 0, 1)
        self.lbl_zoom = QLabel('100%')
        layout_img_ctrl.addWidget(self.lbl_zoom, 0, 2)

        layout_img.addLayout(layout_img_ctrl)
        lbl_brightness_static = QLabel('Brightness:')
        layout_img_ctrl.addWidget(lbl_brightness_static, 1, 0)
        self.sl_brightness = QSlider(cw)
        self.sl_brightness.setOrientation(Qt.Orientation.Horizontal)
        self.sl_brightness.setMinimum(0)
        self.sl_brightness.setMaximum(300)
        self.sl_brightness.setValue(100)
        self.sl_brightness.valueChanged.connect(self.update_image_label)
        layout_img_ctrl.addWidget(self.sl_brightness, 1, 1)
        self.lbl_brightness = QLabel('100%')
        layout_img_ctrl.addWidget(self.lbl_brightness, 1, 2)

        # content controls
        lbl_img_display = QLabel(cw)
        lbl_img_display.setText('Mode:')
        lbl_img_display.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout_img_ctrl.addWidget(lbl_img_display, 2, 0)

        self.tabs_img_ctrl = QTabWidget(cw)
        self.tabs_img_ctrl.currentChanged.connect(self.update_image_label)
        self.tabs_img_ctrl.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum))
        layout_img_ctrl.addWidget(self.tabs_img_ctrl, 2, 1)

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
        self.sl_lambda.setOrientation(Qt.Orientation.Horizontal)
        self.sl_lambda.valueChanged.connect(self.update_image_label)
        self.sl_lambda.setMinimumWidth(300)
        self.sl_lambda.setValue(0)
        tab_layers.layout().addWidget(self.sl_lambda)

        self.lbl_lambda = QLabel(tab_layers)
        self.lbl_lambda.setText("0")
        tab_layers.layout().addWidget(self.lbl_lambda)

        # similarity -> index 2
        tab_similarity = QWidget()
        tab_similarity.setLayout(QHBoxLayout())
        self.tabs_img_ctrl.addTab(tab_similarity, 'similarity')

        self.cmb_reference = QComboBox(tab_similarity)
        self.cmb_reference.addItem('SELECTED PIXEL', -1)
        for s, i in zip(self.db.data, range(len(self.db.data))):
            self.cmb_reference.addItem(s['name'], i)
        self.cmb_reference.currentIndexChanged.connect(self.update_image_label)
        self.cmb_reference.currentIndexChanged.connect(self.set_recompute_errmap_flag)
        tab_similarity.layout().addWidget(self.cmb_reference)

        lbl_sim_t = QLabel(tab_similarity)
        lbl_sim_t.setText('t=')
        tab_similarity.layout().addWidget(lbl_sim_t)

        self.sl_sim_t = QSlider(tab_similarity)
        self.sl_sim_t.setOrientation(Qt.Orientation.Horizontal)
        self.sl_sim_t.setMinimum(0)
        self.sl_sim_t.setMaximum(99)
        self.sl_sim_t.setValue(0)
        self.sl_sim_t.valueChanged.connect(self.update_image_label)
        tab_similarity.layout().addWidget(self.sl_sim_t)

        # PCA -> index 3
        tab_pca = QWidget()
        tab_pca.setLayout(QHBoxLayout())
        self.tabs_img_ctrl.addTab(tab_pca, 'pca')

        lbl_components = QLabel(tab_pca)
        lbl_components.setText('Select component:')
        tab_pca.layout().addWidget(lbl_components)

        self.sl_component = QSlider(tab_pca)
        self.sl_component.setOrientation(Qt.Orientation.Horizontal)
        self.sl_component.valueChanged.connect(self.update_image_label)
        self.sl_component.setMinimumWidth(300)
        self.sl_component.setMinimum(0)
        self.sl_component.setMaximum(9)
        self.sl_component.setValue(0)
        tab_pca.layout().addWidget(self.sl_component)

        self.lbl_component = QLabel(tab_pca)
        self.lbl_component.setText("0")
        tab_pca.layout().addWidget(self.lbl_component)

        # save image
        self.btn_save_img = QPushButton('Save\nImage')
        self.btn_save_img.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum))
        layout_img_ctrl.addWidget(self.btn_save_img, 2, 2)
        self.btn_save_img.pressed.connect(self.export_image)


        # add separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout_outer.addWidget(line)

        ########################
        ### specrtra display ###
        ########################
        layout_spectra = QVBoxLayout(cw)
        layout_outer.addLayout(layout_spectra)

        # db search controls
        layout_search_ctrls = QHBoxLayout(self)
        layout_spectra.addLayout(layout_search_ctrls)
        layout_search_ctrls.addStretch()
        layout_search_ctrls.addWidget(QLabel('show'))
        self.sb_nspectra = QSpinBox(self)
        self.sb_nspectra.setMinimum(0)
        self.sb_nspectra.setMaximum(10)
        self.sb_nspectra.setValue(0)
        self.sb_nspectra.valueChanged.connect(self.update_spectrum_plot)
        layout_search_ctrls.addWidget(self.sb_nspectra)
        layout_search_ctrls.addWidget(QLabel('most similar spectra'))

        #### plot canvas & range controls
        layout_plot = QHBoxLayout(cw)
        layout_spectra.addLayout(layout_plot)

        # y-range control
        layout_yrangecontrol = QVBoxLayout(cw)
        layout_plot.addLayout(layout_yrangecontrol)

        self.lbl_ymax = QLabel('ymax')
        layout_yrangecontrol.addWidget(self.lbl_ymax)
        self.sb_ymax = QDoubleSpinBox(cw)
        self.sb_ymax.setMinimum(0.5)
        self.sb_ymax.setMaximum(1.5)
        self.sb_ymax.setValue(1)
        self.sb_ymax.setSingleStep(0.1)
        self.sb_ymax.valueChanged.connect(self.update_spectrum_plot)
        layout_yrangecontrol.addWidget(self.sb_ymax)

        layout_yrangecontrol.addStretch()

        self.lbl_ymin = QLabel('ymin')
        layout_yrangecontrol.addWidget(self.lbl_ymin)
        self.sb_ymin = QDoubleSpinBox(cw)
        self.sb_ymin.setMinimum(0)
        self.sb_ymin.setMaximum(1)
        self.sb_ymin.setValue(0)
        self.sb_ymin.setSingleStep(0.1)
        self.sb_ymin.valueChanged.connect(self.update_spectrum_plot)
        layout_yrangecontrol.addWidget(self.sb_ymin)

        # plot
        self.plot = PlotCanvas(cw)
        layout_plot.addWidget(self.plot)


        # x-range control
        layout_compare_ctrl = QHBoxLayout(cw)
        layout_spectra.addLayout(layout_compare_ctrl)

        layout_compare_ctrl.addWidget(QLabel('Range'))
        self.rs_xrange = QRangeSlider(cw)
        self.rs_xrange.setRange(0, 1000)
        self.rs_xrange.setMin(0)
        self.rs_xrange.setMax(1000)
        self.rs_xrange.startValueChanged.connect(self.update_spectrum_plot)
        self.rs_xrange.endValueChanged.connect(self.update_spectrum_plot)
        self.rs_xrange.startValueChanged.connect(self.set_recompute_errmap_flag)
        self.rs_xrange.endValueChanged.connect(self.set_recompute_errmap_flag)

        layout_compare_ctrl.addWidget(self.rs_xrange)

        self.cb_squared = QCheckBox(self)
        self.cb_squared.setText('squared errors')
        self.cb_squared.setChecked(True)
        self.cb_squared.stateChanged.connect(self.update_spectrum_plot)
        self.cb_squared.stateChanged.connect(self.set_recompute_errmap_flag)
        layout_compare_ctrl.addWidget(self.cb_squared)

        self.cb_gradient = QCheckBox(self)
        self.cb_gradient.setText('compare gradients')
        self.cb_gradient.setChecked(True)
        self.cb_gradient.stateChanged.connect(self.update_spectrum_plot)
        self.cb_gradient.stateChanged.connect(self.set_recompute_errmap_flag)
        layout_compare_ctrl.addWidget(self.cb_gradient)


        ### export controls
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
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        layout_export_ctrl.addWidget(sep)

        btn_add_to_db = QPushButton(cw)
        btn_add_to_db.setText('Add to DB..')
        btn_add_to_db.clicked.connect(self.handle_btn_add_to_db_clicked)
        layout_export_ctrl.addWidget(btn_add_to_db)

        ###################
        ### create menu ###
        ###################
        menubar = self.menuBar()

        # file menu
        menu_file = menubar.addMenu('&File')

        action_load_data = menu_file.addAction('&Load Hyperspectral Image...')
        action_load_data.triggered.connect(self.handle_action_load_data)

        self.action_save_img = menu_file.addAction('&Save current image...')
        self.action_save_img.setEnabled(False)
        self.action_save_img.triggered.connect(self.export_image)

        action_export_spectrum = menu_file.addAction('&Save selected spectrum...')
        action_export_spectrum.triggered.connect(self.handle_action_export_spectrum)

        # info menu
        menu_info = menubar.addMenu('&?')
        action_info = menu_info.addAction('&Show info')
        action_info.triggered.connect(self.show_info)

        # very important
        quote = np.random.randint(0,len(hyper_quotes))
        self.statusBar().showMessage(hyper_quotes[quote])

        # additional windows (define here for better readability only)
        self.match_point_win = None

        # finito!
        ss = QGuiApplication.screens()[0].availableSize()
        self.setGeometry(int(ss.width() * 0.1), int(ss.height() * 0.1),
                         int(ss.width() * 0.8), int(ss.height() * 0.8))

        if self.rawfile is None:
            img_startup = QPixmap()
            img_startup.load('startup.png')
            wi = int(self.width() * self.config.initial_image_width_ratio)
            img_startup = img_startup.scaled(wi, wi, transformMode=Qt.TransformationMode.SmoothTransformation)
            self.lbl_img.setPixmap(img_startup)
            self.lbl_img.resize(wi, wi)
        else:
            self.load_data(self.rawfile)
        self.show()

    def show_info(self):
        mb = QMessageBox(QMessageBox.Icon.Information,
                         "About this software",
                         self.config.infotext(),
                         QMessageBox.StandardButton.Close)
        mb.exec()

    ##############
    # UI updates
    ##############
    def reset_ui(self):
        self.point_selection = None
        self.rect_selection = None
        self.error_map = None
        self.error_map_recompute_flag = True
        self.tabs_img_ctrl.setCurrentIndex(0)
        self.sl_lambda.setValue(0)
        self.lbl_lambda.setText(self.get_lambda_slider_text(0))
        if self.cube is not None:
            self.sl_lambda.setMaximum(self.cube.nbands - 1)
            # self.sl_xmin.setMinimum(self.cube.bands[0])
            # self.sl_xmin.setMaximum(self.cube.bands[-1])
            # self.sl_xmax.setMinimum(self.cube.bands[0])
            # self.sl_xmax.setMaximum(self.cube.bands[-1])
            self.rs_xrange.setMin(self.cube.bands[0])
            self.rs_xrange.setMax(self.cube.bands[-1])
            self.rs_xrange.setRange(self.cube.bands[0], self.cube.bands[-1])

        self.sl_component.setValue(0)
        self.plot.reset()

    def set_recompute_errmap_flag(self):
        self.error_map_recompute_flag = True

    def update_image_label(self):
        print('update_image_label')
        img = None
        # I. get base image, depending on selected tab
        # 0 - RGB image
        if self.tabs_img_ctrl.currentIndex() == 0:
            if self.rgb is not None:
                img = self.rgb
        # 1 - single layer
        elif self.tabs_img_ctrl.currentIndex() == 1:
            layer = self.sl_lambda.value()
            if self.cube is not None:
                if 0 <= layer < self.cube.nbands:
                    img = self.cube.data[:, :, layer]
                    self.lbl_lambda.setText(self.get_lambda_slider_text(layer))
        # 2 - similarity
        elif self.tabs_img_ctrl.currentIndex() == 2:
            ref_spec = None
            ref_bands = None
            if self.cmb_reference.currentData() == -1:
                if self.spectrum is not None:
                    ref_spec = self.spectrum
                    ref_bands = self.cube.bands
            else:
                ref_spec = self.db.data[self.cmb_reference.currentData()]['spectrum']
                ref_bands = self.db.data[self.cmb_reference.currentData()]['bands']
            if ref_spec is not None and self.cube is not None:
                if self.error_map_recompute_flag:
                    self.error_map_recompute_flag = False
                    self.error_map = self.db.compare_spectra(np.array(self.cube.bands),
                                                             self.cube.data,
                                                             np.array(ref_bands),
                                                             ref_spec,
                                                             custom_range=(self.rs_xrange.start(), self.rs_xrange.end()),
                                                             use_gradient=self.cb_gradient.isChecked(),
                                                             squared_errs=self.cb_squared.isChecked())

                err_map_t = self.error_map.copy()
                t = (100 - self.sl_sim_t.value()) / 100 * err_map_t.max()
                err_map_t[err_map_t > t] = t
                img = self.visualize_error_map(err_map_t)

        # 3 - PCA
        elif self.tabs_img_ctrl.currentIndex() == 3:
            component = self.sl_component.value()
            if self.cube is not None:
                if self.pca is None:
                    self.pca = principal_component_analysis(self.cube.data, p_keep=0.01, n_components=10)
                if 0 <= component < self.pca.shape[2]:
                    img = self.pca[:, :, component]
                    img = (img - img.min()) / (img.max() - img.min())
                    self.lbl_component.setText(f'PC {component}')

        # II. if we have an image, draw the selected pixel and render it.
        if img is not None:
            # adjust brightness
            img = img * self.sl_brightness.value() / 100
            self.lbl_brightness.setText(f'{self.sl_brightness.value()}%')
            # clip
            img = np.clip(img, 0, 1)
            # float to normalized 8 bit
            img = np.uint8(img * 255)

            # draw cross
            img = self.draw_marker(img, fatten=True)

            width = img.shape[1]
            height = img.shape[0]
            if len(img.shape) == 3:
                qImg = QImage(img.tobytes(), width, height, 3 * width, QImage.Format.Format_RGB888)
            else:
                qImg = QImage(img.tobytes(), width, height, width, QImage.Format.Format_Grayscale8)

            if qImg is not None:
                qPixmap = QPixmap.fromImage(qImg)
                # handle scaling
                self.lbl_zoom.setText(f'{self.sl_zoom.value()}%')
                scale = self.sl_zoom.value() / 100
                qPixmap = qPixmap.scaled(int(width * scale), int(height * scale),
                                         transformMode=Qt.TransformationMode.FastTransformation)
                # set image
                self.lbl_img.setPixmap(qPixmap)
                self.lbl_img.resize(int(width * scale), int(height * scale))

    def update_spectrum_plot(self):

        self.plot.set_ranges(self.rs_xrange.start(),
                             self.rs_xrange.end(),
                             self.sb_ymin.value(),
                             self.sb_ymax.value())

        if self.spectrum is not None:
            self.plot.plot(self.cube.bands,
                           self.spectrum,
                           label='query',
                           hold=False)

            if self.sb_nspectra.value() > 0:
                result = self.db.search_spectrum(self.cube.bands,
                                                 self.spectrum,
                                                 custom_range=(self.rs_xrange.start(), self.rs_xrange.end()),
                                                 use_gradient=self.cb_gradient.isChecked(),
                                                 squared_errs=self.cb_squared.isChecked())
                for s in result[:self.sb_nspectra.value()]:
                    self.plot.plot(s['bands'],
                                   s['spectrum'],
                                   label='%s (e=%.3f)' % (s['name'], s['error']),
                                   linewidth=1,
                                   hold=True)

    ##################
    # loading HS data
    ##################
    def load_data(self, filename):
        try:
            self.cube = Cube(filename)
            self.rgb = self.cube.to_rgb()
            self.pca = None
            self.reset_ui()
            self.update_image_label()
            self.rawfile = filename
            self.action_save_img.setEnabled(True)
            # self.action_match_cube.setEnabled(True)
            self.statusBar().showMessage(f'Loaded: {os.path.basename(filename)} | '
                                         f'{self.cube.ncols} x {self.cube.nrows} px | '
                                         f'{self.cube.nbands} bands.')
            self.sl_zoom.setValue(int(self.width() * self.config.initial_image_width_ratio / self.cube.ncols * 100))

        except Exception as e:
            print("Error loading file: ")
            print(e)

    def handle_action_load_data(self):
        filename, _ = QFileDialog.getOpenFileName(None, "Select ENVI data file", "")
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
        filename = urls[0].url(QUrl.UrlFormattingOption.RemoveScheme)
        # remove leading slashes
        while filename.startswith('/'):
            filename = filename[1:]
        self.load_data(filename)

    #############################
    # image & spectra operations
    #############################
    def handle_click_on_image(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.cube is not None:
            self.rubberband_origin = event.pos()
            self.rubberband_selector.setGeometry(QRect(self.rubberband_origin, QSize()))
            self.rubberband_selector.show()
        else:
            event.ignore()
    def handle_move_on_image(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.cube is not None:
            x = np.clip(event.pos().x(), 0, self.lbl_img.width()-1)
            y = np.clip(event.pos().y(), 0, self.lbl_img.height()-1)
            self.rubberband_selector.setGeometry(QRect(self.rubberband_origin, QPoint(x, y)).normalized())
        else:
            event.ignore()
    def handle_release_on_image(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.cube is not None:
                rect = self.m2i(self.rubberband_selector.geometry())
                if rect.width() > 1 and rect.height() > 1:
                    cube_slice = self.cube.data[rect.y():rect.y()+rect.height(),
                                                rect.x():rect.x()+rect.width(),
                                                :]
                    self.spectrum = np.mean(cube_slice, axis=(0, 1))
                    self.rect_selection = rect
                    self.point_selection = None
                else:
                    pos_img = self.m2i(event.pos())
                    if 0 <= pos_img.x() < self.cube.ncols and 0 <= pos_img.y() < self.cube.nrows:
                        print(f"Selected point: ({pos_img.x()}, {pos_img.y()})")
                        self.spectrum = self.cube.data[pos_img.y(), pos_img.x(), :]
                        self.point_selection = pos_img
                        self.rect_selection = None
                # update ui
                self.set_recompute_errmap_flag()
                self.update_image_label()
                self.update_spectrum_plot()
                self.rubberband_selector.hide()
        else:
            event.ignore()

    def handle_click_on_image_scroll(self, event):
        self.drag_start_x = event.pos().x()
        self.drag_start_y = event.pos().y()
        if event.buttons() == Qt.MouseButton.RightButton:
            self.drag_start_hs_v = self.scroll_img.horizontalScrollBar().value()
            self.drag_start_vs_v = self.scroll_img.verticalScrollBar().value()
        else:
            event.ignore()
    def handle_move_on_image_scroll(self, event):
        if event.buttons() == Qt.MouseButton.RightButton:
            # drag image
            hs_max = self.scroll_img.horizontalScrollBar().maximum()
            vs_max = self.scroll_img.verticalScrollBar().maximum()
            hs_min = self.scroll_img.horizontalScrollBar().minimum()
            vs_min = self.scroll_img.verticalScrollBar().minimum()

            dh = int(self.drag_start_x - event.position().x())
            dv = int(self.drag_start_y - event.position().y())

            self.scroll_img.horizontalScrollBar().setValue(min(hs_max, max(hs_min, self.drag_start_hs_v + dh)))
            self.scroll_img.verticalScrollBar().setValue(min(vs_max, max(vs_min, self.drag_start_vs_v + dv)))
        else:
            event.ignore()
    def handle_wheel_on_image_scroll(self, event):
        if self.scroll_img.horizontalScrollBar().maximum() > 0:
            hs_r = self.scroll_img.horizontalScrollBar().value() / self.scroll_img.horizontalScrollBar().maximum()
        else:
            hs_r = 0.5
        if self.scroll_img.verticalScrollBar().maximum() > 0:
            vs_r = self.scroll_img.verticalScrollBar().value() / self.scroll_img.verticalScrollBar().maximum()
        else:
            vs_r = 0.5
        s = event.angleDelta().y() * self.config.scroll_speed
        if s < 0:
            s = -1 / s
        self.sl_zoom.setValue(int(self.sl_zoom.value() * s))
        self.scroll_img.horizontalScrollBar().setValue(int(self.scroll_img.verticalScrollBar().maximum() * hs_r))
        self.scroll_img.verticalScrollBar().setValue(int(self.scroll_img.verticalScrollBar().maximum() * vs_r))

    def handle_action_export_spectrum(self):
        if self.spectrum is not None:
            expdir = os.path.dirname(self.rawfile)
            basename = os.path.splitext(os.path.basename(self.rawfile))[0]
            sel_str = self.selection_str()
            expfile = os.path.join(expdir, f"{basename}_{sel_str}.jdx")

            file_name, _ = QFileDialog.getSaveFileName(None, "Save spectrum", expfile,
                                                      "JCAMP-DX (*.jdx *.dx *jcm);;Plain x,y pairs (*.dpt *.csv *.txt )")
            if file_name:
                valid = False
                if os.path.splitext(file_name)[1] in ['.dx', '.jdx', '.jcm']:
                    Exports.export_jcamp(x_data=self.cube.bands,
                                    y_data=self.spectrum,
                                    spectrum_name=f"{os.path.basename(self.rawfile).split('.')[0]}, at {sel_str}",
                                    device_name=f"SpecimIQ/Hyperlyse{self.config.version}",
                                    file_name=file_name)
                    valid = True
                elif os.path.splitext(file_name)[1] in ['.dpt', '.txt', '.csv']:
                    Exports.export_dpt(self.cube.bands, self.spectrum, file_name)
                    valid = True

                if valid:
                    if self.cb_incl_img.isChecked() and self.rgb is not None:
                        img = self.rgb
                        img = np.uint8(img * (255 / img.max()))
                        img = self.draw_marker(img, self.config.cross_size)
                        base, ext = os.path.splitext(file_name)
                        matplotlib.image.imsave(base + '.png', img.astype(np.uint8))

                    if self.cb_incl_graph.isChecked():
                        base, ext = os.path.splitext(file_name)
                        self.plot.save(base + '_graph.png')
                else:
                    print('warning: invalid file extension given. spectrum not saved. allowed: '
                          '.dpt, .txt (plain comma-separated x,y values), .dx, .jdx, .jcm (JCAMP-DX)')



    def export_image(self):
        expdir = os.path.dirname(self.rawfile)
        basename = os.path.basename(self.rawfile).split('.')[0]
        if self.tabs_img_ctrl.currentIndex() == 0:
            suffix = 'rgb'
        elif self.tabs_img_ctrl.currentIndex() == 1:
            suffix = self.lbl_lambda.text()
        elif self.tabs_img_ctrl.currentIndex() == 2:
            if self.cmb_reference.currentData() == -1:
                suffix = f'sim{self.selection_str()}'
            else:
                suffix = f'sim({self.cmb_reference.currentText()})'
        elif self.tabs_img_ctrl.currentIndex() == 3:
            suffix = f'pc{self.sl_component.value()}'
        else:
            print("Your argument is invalid!")
            return
        expfile = os.path.join(expdir, f"{basename}_{suffix}.png")

        fileName, _ = QFileDialog.getSaveFileName(None, "Export image", expfile, "All Files (*)")
        if fileName:
            self.lbl_img.pixmap().save(fileName)

    def handle_btn_add_to_db_clicked(self):
        if self.spectrum is not None:
            name, ok = QInputDialog.getText(self,
                                            'Add spectrum to database',
                                            'sample name: ')
            if ok and name:
                if name in [n['name'] for n in self.db.data]:
                    answer = QMessageBox.question(self,
                                                  'Name already exists!',
                                                  'A sample with the name %s already exists in the database. Overwrite?' % name
                                                  )
                    if answer == QMessageBox.StandardButton.Yes:
                        self.db.add_to_db(name, self.spectrum, self.cube.bands)
                        self.db.save_db()
                        self.cmb_reference.addItem(name, len(self.db.data) - 1)

                else:
                    self.db.add_to_db(name, self.spectrum, self.cube.bands)
                    self.db.save_db()
                    self.cmb_reference.addItem(name, len(self.db.data) - 1)

    ###########
    # analysis
    ###########
    def handle_action_create_db(self):
        dirname = QFileDialog.getExistingDirectory(None, "Select root directory for database creation", "")
        if dirname:
            Database.create_database(dirname, True)

    def handle_action_load_db(self):
        filename, _ = QFileDialog.getOpenFileName(None, "Select file containing reference spectra",
                                                  "", "json files (*.json)")
        if filename:
            self.db.load_db(filename)

    ###########
    # helpers
    ##########
    def m2i(self, object):
        # convert mouse coordinates on scaled image label to image coordinates
        if isinstance(object, numbers.Number):
            return int(object / self.sl_zoom.value() * 100)
        if isinstance(object, QPoint):
            return QPoint(self.m2i(object.x()), self.m2i(object.y()))
        elif isinstance(object, QSize):
            return QSize(self.m2i(object.width()), self.m2i(object.height()))
        elif isinstance(object, QRect):
            return QRect(self.m2i(object.topLeft()), self.m2i(object.size()))
        else:
            raise ValueError()

    def draw_marker(self, img, fatten=False):
        """
        Draws a cross (if a point is selected) or a rectangle (if an area is selected) onto an image
        :param img: numpy array, r*c or r*c*3
        :param fatten: make the marker fatter for small scales, such that it remais visible
        :return:
        """
        if len(img.shape) == 2:
            img = np.dstack([img, img, img])
        img_marker = img.copy()

        scale = self.sl_zoom.value() / 100
        if scale < 1:
            padding = int(np.ceil(1 / scale - 1))
            cross_size = int(np.ceil(self.config.cross_size / scale))
        else:
            padding = 0
            cross_size = self.config.cross_size

        if self.rect_selection is not None:
            # RECT
            r = self.rect_selection
            # top line
            img_marker[max(r.top() - padding, 0):min(r.top() + padding + 1, self.cube.nrows - 1),
                       max(r.left(), 0):min(r.right(), self.cube.ncols - 1)] = self.config.marker_colors[0]
            # bottom line
            img_marker[max(r.bottom() - padding, 0):min(r.bottom() + padding + 1, self.cube.nrows - 1),
                       max(r.left(), 0):min(r.right(), self.cube.ncols - 1)] = self.config.marker_colors[1]
            # left line
            img_marker[max(r.top(), 0):min(r.bottom()+1, self.cube.nrows - 1),
                       max(r.left() - padding, 0):min(r.left() + padding + 1, self.cube.ncols - 1)] = self.config.marker_colors[0]
            # left line
            img_marker[max(r.top(), 0):min(r.bottom()+1, self.cube.nrows - 1),
            max(r.right() - padding, 0):min(r.right() + padding + 1, self.cube.ncols - 1)] = self.config.marker_colors[1]
        elif self.point_selection is not None:
            # CROSS
            p = self.point_selection
            # horizontal line
            img_marker[max(p.y() - padding, 0):min(p.y() + padding + 1, self.cube.nrows - 1),
                      max(p.x() - cross_size, 0):min(p.x() + cross_size + 1, self.cube.ncols - 1)] = self.config.marker_colors[0]
            # vertical line
            img_marker[max(p.y() - cross_size, 0):min(p.y() + cross_size + 1, self.cube.nrows - 1),
                      max(p.x() - padding, 0):min(p.x() + padding + 1, self.cube.ncols - 1)] = self.config.marker_colors[1]
            # central dot
            img_marker[max(p.y() - padding, 0):min(p.y() + padding + 1, self.cube.nrows - 1),
                      max(p.x() - padding, 0):min(p.x() + padding + 1, self.cube.ncols - 1)] = self.config.marker_colors[2]

        else:
            #nothing
            return img

        img = img * (1 - self.config.marker_alpha) + img_marker * self.config.marker_alpha
        return img.astype(np.uint8)

    def selection_str(self):
        if self.rect_selection is not None:
            r = self.rect_selection
            return f'({r.left()},{r.top()},{r.width()},{r.height})'
        elif self.point_selection is not None:
            p = self.point_selection
            return f'({p.x()},{p.y()})'
        else:
            return '(unknown)'  # can that happen?

    def get_lambda_slider_text(self, layer_idx):
        return '%.1fnm' % self.cube.bands[layer_idx]

    def visualize_error_map(self, error_map):
        # invert and map to [0, 1]:
        similarity_map = 1 - (error_map / error_map.max())
        # apply color map
        cm = plt.get_cmap('viridis')
        return cm(similarity_map)[:, :, :3]
