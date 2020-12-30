import os
import json
import numpy as np
import hyperlyse.specim as specim
from matplotlib import pyplot as plt

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
                cube = specim.read(file_hsdata)
            except:
                print('Error while trying to read HS data from %s. Skipping.' % file_hsdata)
                continue

            # for visualization purposes..
            rgb = specim.cube2rgb(cube)
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
                                'spectrum': mean_spectrum.tolist(),
                                'lambda_min': specim.lambda_min,
                                'lambda_max': specim.lambda_max,
                                'lambda_delta': specim.lambda_delta})

                if visualize:
                    axs[1].plot(specim.lambda_space, mean_spectrum, label=lab['label'])
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
