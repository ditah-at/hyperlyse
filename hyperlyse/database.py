import os
import json
import numpy as np
from matplotlib import pyplot as plt
from hyperlyse import Cube
from scipy.signal import resample


class Database:

    def __init__(self):
        self.data = None
        self.file_data = None


    @staticmethod
    def create_database(dir_root: str, visualize=False):
        db_spectra = []

        dir_vis = os.path.join(dir_root, 'db_visualizations')
        if visualize and not os.path.exists(dir_vis):
            os.makedirs(dir_vis)

        for img_name in os.listdir(dir_root):
            cur_dir = os.path.join(dir_root, img_name)
            if os.path.isdir(cur_dir):
                file_labels = os.path.join(cur_dir, img_name+'.json')
                labels = None
                try:
                    with open(file_labels, 'r') as f:
                        labels = json.load(f)['shapes']
                except:
                    print('Error while trying to read labels from %s. Skipping.' % file_labels)
                    continue

                file_hsdata = os.path.join(cur_dir, 'capture', img_name+'.raw')
                cube = None
                try:
                    cube = Cube(file_hsdata)
                except:
                    print('Error while trying to read HS data from %s. Skipping.' % file_hsdata)
                    continue

                # for visualization purposes..
                rgb = cube.to_rgb()
                fig, axs = plt.subplots(1, 3, figsize=(15, 5))
                fig.suptitle('Spectra extracted from %s' % img_name)

                for lab in labels:
                    x = [int(lab['points'][0][0]), int(lab['points'][1][0])]
                    x.sort()
                    y = [int(lab['points'][0][1]), int(lab['points'][1][1])]
                    y.sort()

                    crop_to_label = cube.data[y[0]:y[1], x[0]:x[1], :]
                    mean_spectrum = crop_to_label.mean((0, 1))
                    db_spectra.append({'name': lab['label'],
                                       'spectrum': mean_spectrum.tolist(),
                                       'bands': cube.bands})

                    if visualize:
                        axs[1].plot(cube.bands, mean_spectrum, label=lab['label'])
                        rect_color = [0, 1, 0]
                        rgb[y[0]:y[1], x[0]] = rect_color
                        rgb[y[0]:y[1], x[1]] = rect_color
                        rgb[y[0], x[0]:x[1]] = rect_color
                        rgb[y[1], x[0]:x[1]] = rect_color

                if visualize:
                    axs[0].imshow(rgb)
                    axs[1].legend(bbox_to_anchor=(1.05, 1), loc='upper left')
                    axs[2].axis('off')
                    plt.savefig(os.path.join(dir_vis, img_name+'_spectra.png'), transparent=True)

        if db_spectra:
            file_db = os.path.join(dir_root, os.path.basename(dir_root)+'_spectra-db.json')
            with open(file_db, 'w') as f:
                json.dump(db_spectra, f, indent=4)

    def load_db(self, file):
        self.file_data = file
        with open(self.file_data, 'r') as f:
            self.data = json.load(f)
        self.data.sort(key=lambda x: x['name'])

    def save_db(self, file=None):
        if file is None:
            file = self.file_data
        with open(file, 'w') as f:
            json.dump(self.data, f, indent=4)

    def add_to_db(self, name, spectrum, bands):
        if isinstance(spectrum, np.ndarray):
            spectrum = [x.item() for x in spectrum]
        if name in [s['name'] for s in self.data]:
            # overwrite spectrum
            for s in self.data:
                if s['name'] == name:
                    s['spectrum'] = spectrum
                    s['bands'] = bands
        else:
            # insert new spectrum
            self.data.append({'name': name,
                              'spectrum': spectrum,
                              'bands': bands})

    @staticmethod
    def compare_spectra(x1, y1,
                        x2, y2,
                        custom_range=None,
                        use_gradient=False,
                        squared_errs=True):
        """
        compares 2 spectra
        :param x1: np.array, wavelength array of spectrum 1
        :param y1: np.array, intensity array of spectrum 1 - can be 1d (simple spectrum) or 3d (cube)
        :param x2: np.array, wavelength array of spectrum 2
        :param y2: np.array, intensity array of spectrum 2 - must be 1d, is re-sampled if required
        :param custom_range: (x_min, x_max), a custom range of wavelengths used for comparison
        :param use_gradient: compare gradients instead of absolute differences
        :param squared_errs: use squared differences (or absolute differences)
        :return: mean error/distance; scalar or 2d np.array, depending on shape of y1
        """
        x1 = np.array(x1)
        x2 = np.array(x2)
        y1 = np.array(y1)
        y2 = np.array(y2)

        is_cube = len(y1.shape) == 3

        lambda_min = max(x1[0], x2[0])
        lambda_max = min(x1[-1], x2[-1])
        if custom_range is not None:
            lambda_min = max(lambda_min, custom_range[0])
            lambda_max = min(lambda_max, custom_range[1])

        mask1 = np.logical_and(x1 >= lambda_min, x1 <= lambda_max)
        if is_cube:
            y1_masked = y1[:, :, mask1]
        else:
            y1_masked = y1[mask1]

        mask2 = np.logical_and(x2 >= lambda_min, x2 <= lambda_max)
        y2_masked = y2[mask2]

        if y1_masked.size < 2 > y2_masked.size:
            print('WARNING: compared spectra do not have sufficient overlap. Returning None')
            return None

        if not np.array_equal(x1[mask1], x2[mask2]):
            y2_masked = resample(y2_masked, mask1.sum())

        if use_gradient:
            if is_cube:
                errs = np.gradient(y1_masked, axis=2) - np.gradient(y2_masked)
            else:
                errs = np.gradient(y1_masked) - np.gradient(y2_masked)
        else:
            errs = y1_masked - y2_masked

        if squared_errs:
            errs = np.power(errs, 2)
        else:
            errs = np.abs(errs)

        if is_cube:
            return np.mean(errs, axis=2)
        else:
            return np.mean(errs)

    def search_spectrum(self,
                        x,
                        y,
                        custom_range=None,
                        use_gradient=False,
                        squared_errs=True):


        bands_query = x
        spectrum_query = y
        results = []
        for d in self.data:
            bands_db = np.array(d['bands'])
            spectrum_db = np.array(d['spectrum'])
            error = Database.compare_spectra(bands_query,
                                             spectrum_query,
                                             bands_db,
                                             spectrum_db,
                                             custom_range=custom_range,
                                             use_gradient=use_gradient,
                                             squared_errs=squared_errs)
            if error is not None:
                result = d
                result['error'] = error
                results.append(result)

        results.sort(key=lambda v: v['error'])
        return results
