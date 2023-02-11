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


    def search_spectrum(self,
                        query_spectrum,
                        query_bands,
                        custom_range=None,
                        use_gradient=False,
                        squared_errs=True):
        result = self.data.copy()
        query_bands = np.array(query_bands)
        query_spectrum = np.array(query_spectrum)

        # if no query range is specified (or it is invalid), use range of query spectrum
        if custom_range is None:
            custom_range = (query_bands[0], query_bands[-1])
        elif custom_range[0] > custom_range[1]:
            custom_range = (query_bands[0], query_bands[-1])


        for s in result:
            s_bands = np.array(s['bands'])
            s_spectrum = np.array(s['spectrum'])

            lambda_min = max(custom_range[0], s_bands[0])
            lambda_max = min(custom_range[1], s_bands[-1])

            query_range = np.logical_and(query_bands >= lambda_min, query_bands <= lambda_max)
            query_spectrum_w = query_spectrum[query_range]

            s_window = np.logical_and(s_bands >= lambda_min, s_bands <= lambda_max)
            s_spectrum_w = s_spectrum[s_window]

            query_spectrum_r = resample(query_spectrum_w, 100)
            s_spectrum_r = resample(s_spectrum_w, 100)

            if use_gradient:
                errs = np.gradient(query_spectrum_r) - np.gradient(s_spectrum_r)
            else:
                errs = query_spectrum_r - s_spectrum_r

            if squared_errs:
                errs = np.power(errs, 2)
            else:
                errs = np.abs(errs)

            mean_err = np.sum(errs) # / len(query_spectrum)

            s['error'] = mean_err

        result.sort(key=lambda x: x['error'])

        return result


    @staticmethod
    def compare_cube_to_spectrum(cube,
                                 spectrum,
                                 bands,
                                 custom_range=None,
                                 use_gradient=False,
                                 squared_errs=True):

        bands = np.array(bands)
        spectrum = np.array(spectrum)
        c_bands = np.array(cube.bands)

        # resample if required
        if not np.array_equal(bands, c_bands) or custom_range is not None:

            if custom_range is None:
                custom_range = (c_bands[0], c_bands[-1])
            elif custom_range[0] >= custom_range[1]:
                custom_range = (c_bands[0], c_bands[-1])

            lambda_min = max(bands[0], custom_range[0])
            lambda_max = min(bands[-1], custom_range[1])

            query_window = np.logical_and(bands >= lambda_min, bands <= lambda_max)
            spectrum_w = spectrum[query_window]

            c_window = np.logical_and(c_bands >= lambda_min, c_bands <= lambda_max)
            cube_data = cube.data[:, :, c_window]

            spectrum = resample(spectrum_w, cube_data.shape[2])
        else:
            cube_data = cube.data


        if use_gradient:
            cube_diff = np.gradient(cube_data, axis=2) - np.gradient(spectrum)
        else:
            cube_diff = cube_data - np.array(spectrum)
        if squared_errs:
            cube_diff = np.power(cube_diff, 2)
        else:
            cube_diff = np.abs(cube_diff)

        err_map = np.sum(cube_diff, 2)      # / cube.shape[2]

        return err_map



    # def compare_cube_to_db(self,
    #                          cube,
    #                          use_gradient=False,
    #                          squared_errs=True,
    #                          r_first_to_second=0.5,
    #                          r_gt_zero=0.01,
    #                          vis_dir=None):
    #
    #     map_stack = None
    #     for s, i in zip(self.db, range(len(self.db))):
    #         print('Computing differences with %s (%d/%d)...' % (s['name'], i+1, len(self.db)))
    #
    #         if use_gradient:
    #             cube = np.gradient(cube, axis=2)
    #             cube_diff = cube - s['gradient']
    #         else:
    #             cube_diff = cube - s['spectrum']
    #         if squared_errs:
    #             cube_diff = np.power(cube_diff, 2)
    #         else:
    #             cube_diff = np.abs(cube_diff)
    #
    #         cube_diff = np.sum(cube_diff, 2)
    #         if squared_errs:
    #             cube_diff = np.sqrt(cube_diff)
    #
    #         map_stack = cube_diff if map_stack is None else np.dstack((map_stack, cube_diff))
    #
    #
    #     map_stack = map_stack*(-1) + map_stack.max()    # reverse
    #     winner_map = np.argmax(map_stack, 2)
    #     max_map = np.max(map_stack, 2)
    #     map_stack_largestremoved = map_stack.copy()
    #     for s, i in zip(self.db, range(len(self.db))):
    #         map_stack_largestremoved[i == winner_map] = -1
    #     max_map_second = np.max(map_stack_largestremoved, 2)
    #
    #     has_unique_winner = np.divide(max_map_second, max_map) < r_first_to_second
    #
    #     print('Creating visualizations...')
    #     for s, i in zip(self.db, range(len(self.db))):
    #         is_largest = winner_map == i
    #         #set_zero = np.logical_not(is_largest)
    #         set_zero = np.logical_not(np.logical_and(is_largest, has_unique_winner))
    #         img = map_stack[:, :, i]
    #         img[set_zero] = 0
    #         # visualizations
    #         n_gt_zero = np.sum(img[img>0])
    #         if n_gt_zero / img.size > r_gt_zero:
    #             if vis_dir is not None:
    #                 if not os.path.exists(vis_dir):
    #                     os.makedirs(vis_dir)
    #                 plt.clf()
    #                 plt.imshow(img)
    #                 plt.colorbar()
    #                 plt.title(s['name'])
    #                 plt.savefig(os.path.join(vis_dir, s['name'] + '_bestmatch.png'))
    #     print('Done!')
