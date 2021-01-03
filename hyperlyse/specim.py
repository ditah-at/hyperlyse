import os
import numpy as np
import matplotlib.pyplot as plt

#http://www.specim.fi/iq/tech-specs/
rows = cols = 512
bands = 204
bits = 16
lambda_min = 397
lambda_max = 1004
lambda_delta = (lambda_max - lambda_min) / bands
lambda_space = np.linspace(lambda_min, lambda_max, bands)

def cube2rgb(cube):
    # wavelengths of red, green, blue
    r = 598
    g = 548
    b = 449
    rgb = np.dstack((cube[:, :, int((r - lambda_min) / lambda_delta)],
                     cube[:, :, int((g - lambda_min) / lambda_delta)],
                     cube[:, :, int((b - lambda_min) / lambda_delta)]))
    # clip anything above white
    rgb[rgb > 1] = 1
    return rgb


def read(raw_file, verbose=False):

    raw_dir = os.path.dirname(raw_file)
    capture_id = os.path.basename(raw_file)
    dref_file = os.path.join(raw_dir, 'DARKREF_%s' % capture_id)
    wref_file = os.path.join(raw_dir, 'WHITEREF_%s' % capture_id)

    #read data
    with open(raw_file, mode='rb') as file: # b is important -> binary
        raw_bts = file.read()

    #reshape raw cube
    raw_data = np.float32(np.frombuffer(raw_bts, dtype=np.float16))
    raw_data = np.reshape(raw_data, (rows, bands, cols))
    raw_data = np.rot90(raw_data, k=3, axes=(0,2))

    #read white and black ref
    try:
        with open(dref_file, mode='rb') as file:  # b is important -> binary
            dref_bts = file.read()
        with open(wref_file, mode='rb') as file:  # b is important -> binary
            wref_bts = file.read()

        dref_data = np.float32(np.frombuffer(dref_bts, dtype=np.float16))
        wref_data = np.float32(np.frombuffer(wref_bts, dtype=np.float16))

        ref_size = int(len(dref_data)/(bands))


        #http://www.specim.fi/iq/manual/software/iq/topics/data-cube.html
        dref_data = np.reshape(dref_data, (bands, ref_size))
        wref_data = np.reshape(wref_data, (bands, ref_size))
        dref = np.mean(dref_data, axis=1)
        wref = np.mean(wref_data, axis=1)



        #plot white and dark references
        if verbose:
            f, (dplot, wplot) = plt.subplots(1,2)
            dplot.plot(range(bands),dref)
            # for i in range(ref_size):
            #     dplot.plot(range(bands), dref_data[:, i])
            dplot.set_title('dark reference')
            wplot.plot(range(bands),wref)
            # for i in range(ref_size):
            #     wplot.plot(range(bands), wref_data[:, i])
            wplot.set_title('white reference')
            #f.set_figwidth('20')
            plt.show()


        refl = raw_data*0
        # use mean?
        # for i in range(bands):
        #     refl[:, i, :] = (raw_data[:, i, :]-dref[i]) / (wref[i]-dref[i])
        # or use all values? who knows?
        for i in range(bands):
            for j in range(ref_size):
                refl[j, i, :] = (raw_data[j, i, :]-dref_data[i, :]) / (wref_data[i, :]-dref_data[i, :])


    except:
        refl = raw_data / raw_data.max()
        print("WARNING: No reference spectra found, cube is uncalibrated!!")

    # #plot some layers
    # if verbose:
    #     f, axarr = plt.subplots(1,4)
    #     for i in range(4):
    #         layer = (i+1)*50
    #         axarr[i].imshow(refl[:,layer ,:], cmap='gray')
    #         axarr[i].set_title('%d nm' % (lambda_min+layer*lambda_step))
    #     #f.set_figwidth('20')
    #     plt.show()

    refl = np.transpose(refl,(0,2,1))

    if verbose:
        rgb = cube2rgb(refl)
        plt.figure(figsize=(10, 10))
        plt.title('Composed RGB image')
        plt.imshow(rgb, extent=(0,50,0,50))
        plt.show()

    return refl

