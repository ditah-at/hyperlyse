import numpy as np
import collections
import os

class Exports:
    @staticmethod
    def export_dpt(x_data,
                   y_data,
                   file_name):
        data = np.transpose([np.float32(x_data), np.float32(y_data)])
        np.savetxt(file_name, data, fmt='%.4f', delimiter=',')

    @staticmethod
    def export_jcamp(x_data,
                     y_data,
                     spectrum_name,
                     device_name,
                     file_name):
        # prepare output file content
        data = collections.OrderedDict()  # in jcamp, order of elements is kind of important..
        data['##TITLE'] = spectrum_name
        data['##JCAMP-DX'] = "5.1"
        data['##DATA TYPE'] = "UV/VIS SPECTRUM"
        data['##ORIGIN'] = "CIMA"
        data['##OWNER'] = "CIMA"

        data['##DATA CLASS'] = 'XYDATA'
        data['##SPECTROMETER/DATASYSTEM'] = device_name
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

        vx = np.float32(x_data)
        vy = np.float32(y_data)

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
        if not os.path.isdir(os.path.dirname(file_name)):
            os.makedirs(os.path.dirname(file_name))
        with open(file_name, 'w') as f:
            for k, v in data.items():
                if k == "##XYDATA":
                    f.write('##XYDATA= (X++(Y..Y))\n')
                    for x, y in v:
                        f.write('%s %s\n' % (str(x), str(y)))
                else:
                    f.write('%s= %s\n' % (k.replace('_', ' '), str(v)))