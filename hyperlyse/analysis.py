import os
import json
import numpy as np
from hyperlyse import SpecimIQ
from matplotlib import pyplot as plt


class Analysis:

    def __init__(self):
        self.db = None
        self.db_file = None


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
                    cube = SpecimIQ.read(file_hsdata)
                except:
                    print('Error while trying to read HS data from %s. Skipping.' % file_hsdata)
                    continue

                # for visualization purposes..
                rgb = SpecimIQ.cube2rgb(cube)
                fig, axs = plt.subplots(1, 3, figsize=(15, 5))
                fig.suptitle('Spectra extracted from %s' % img_name)

                for lab in labels:
                    x = [int(lab['points'][0][0]), int(lab['points'][1][0])]
                    x.sort()
                    y = [int(lab['points'][0][1]), int(lab['points'][1][1])]
                    y.sort()

                    crop_to_label = cube[y[0]:y[1], x[0]:x[1]]
                    mean_spectrum = crop_to_label.mean((0, 1))
                    db_spectra.append({'name': lab['label'],
                                       'spectrum': mean_spectrum.tolist()})

                    if visualize:
                        axs[1].plot(SpecimIQ.lambda_space, mean_spectrum, label=lab['label'])
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
        self.db_file = file
        with open(self.db_file, 'r') as f:
            self.db = json.load(f)
        self.db.sort(key=lambda x: x['name'])

    def save_db(self, file=None):
        if file is None:
            file = self.db_file
        with open(file, 'w') as f:
            json.dump(self.db, f, indent=4)

    def add_to_db(self, name, spectrum):
        if isinstance(spectrum, np.ndarray):
            spectrum = [x.item() for x in spectrum]
        if name in [s['name'] for s in self.db]:
            # overwrite spectrum
            for s in self.db:
                if s['name'] == name:
                    s['spectrum'] = spectrum
        else:
            # insert new spectrum
            self.db.append({'name': name,
                            'spectrum': spectrum})


    def search_spectrum(self, query_spectrum, use_gradient=False, squared_errs=True):
        result = self.db.copy()
        for s in result:
            if use_gradient:
                errs = np.gradient(query_spectrum) - np.gradient(s['spectrum'])
            else:
                errs = query_spectrum - s['spectrum']

            if squared_errs:
                errs = np.power(errs, 2)
            else:
                errs = np.abs(errs)

            mean_err = np.sum(errs) # / len(query_spectrum)

            s['error'] = mean_err

        result.sort(key=lambda x: x['error'])

        return result

    def compare_cube_to_spectrum(self,
                                 cube,
                                 spectrum,
                                 use_gradient=False,
                                 squared_errs=True):

        if use_gradient:
            cube_diff = np.gradient(cube, axis=2) - np.gradient(spectrum)
        else:
            cube_diff = cube - spectrum
        if squared_errs:
            cube_diff = np.power(cube_diff, 2)
        else:
            cube_diff = np.abs(cube_diff)

        err_map = np.sum(cube_diff, 2) # / cube.shape[2]

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
