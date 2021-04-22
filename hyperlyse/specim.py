import os
import numpy as np
import matplotlib.pyplot as plt


class SpecimIQ:
    #http://www.specim.fi/iq/tech-specs/
    rows = cols = 512
    bands = 204
    bits = 16
    # lambda_min = 397
    # lambda_max = 1004
    # lambda_delta = (lambda_max - lambda_min) / bands
    # lambda_space = np.linspace(lambda_min, lambda_max, bands)

    # according to exports from SpecimQI Studio:
    lambda_space = [397.32000732421875, 400.20001220703125, 403.08999633789062, 405.97000122070312, 408.85000610351562,
                    411.739990234375, 414.6300048828125, 417.51998901367188, 420.39999389648438, 423.29000854492188,
                    426.19000244140625, 429.07998657226562, 431.97000122070312, 434.8699951171875, 437.760009765625,
                    440.66000366210938, 443.55999755859375, 446.45001220703125, 449.35000610351562, 452.25,
                    455.16000366210938, 458.05999755859375, 460.95999145507812, 463.8699951171875, 466.76998901367188,
                    469.67999267578125, 472.58999633789062, 475.5, 478.41000366210938, 481.32000732421875,
                    484.23001098632812, 487.1400146484375, 490.05999755859375, 492.97000122070312, 495.8900146484375,
                    498.79998779296875, 501.72000122070312, 504.6400146484375, 507.55999755859375, 510.48001098632812,
                    513.4000244140625, 516.33001708984375, 519.25, 522.17999267578125, 525.0999755859375,
                    528.030029296875, 530.96002197265625, 533.8900146484375, 536.82000732421875, 539.75,
                    542.67999267578125, 545.6199951171875, 548.54998779296875, 551.489990234375, 554.42999267578125,
                    557.3599853515625, 560.29998779296875, 563.239990234375, 566.17999267578125, 569.1199951171875,
                    572.07000732421875, 575.010009765625, 577.96002197265625, 580.9000244140625, 583.8499755859375,
                    586.79998779296875, 589.75, 592.70001220703125, 595.6500244140625, 598.5999755859375,
                    601.54998779296875, 604.510009765625, 607.46002197265625, 610.41998291015625, 613.3800048828125,
                    616.34002685546875, 619.29998779296875, 622.260009765625, 625.219970703125, 628.17999267578125,
                    631.1500244140625, 634.1099853515625, 637.08001708984375, 640.03997802734375, 643.010009765625,
                    645.97998046875, 648.95001220703125, 651.91998291015625, 654.8900146484375, 657.8699951171875,
                    660.84002685546875, 663.80999755859375, 666.78997802734375, 669.77001953125, 672.75,
                    675.72998046875, 678.71002197265625, 681.69000244140625, 684.66998291015625, 687.6500244140625,
                    690.6400146484375, 693.6199951171875, 696.6099853515625, 699.5999755859375, 702.58001708984375,
                    705.57000732421875, 708.57000732421875, 711.55999755859375, 714.54998779296875, 717.53997802734375,
                    720.53997802734375, 723.530029296875, 726.530029296875, 729.530029296875, 732.530029296875,
                    735.530029296875, 738.530029296875, 741.530029296875, 744.530029296875, 747.53997802734375,
                    750.53997802734375, 753.54998779296875, 756.55999755859375, 759.55999755859375, 762.57000732421875,
                    765.58001708984375, 768.5999755859375, 771.6099853515625, 774.6199951171875, 777.6400146484375,
                    780.6500244140625, 783.66998291015625, 786.67999267578125, 789.70001220703125, 792.719970703125,
                    795.739990234375, 798.77001953125, 801.78997802734375, 804.80999755859375, 807.84002685546875,
                    810.8599853515625, 813.8900146484375, 816.91998291015625, 819.95001220703125, 822.97998046875,
                    826.010009765625, 829.03997802734375, 832.07000732421875, 835.1099853515625, 838.1400146484375,
                    841.17999267578125, 844.219970703125, 847.25, 850.28997802734375, 853.33001708984375,
                    856.3699951171875, 859.41998291015625, 862.46002197265625, 865.5, 868.54998779296875,
                    871.5999755859375, 874.6400146484375, 877.69000244140625, 880.739990234375, 883.78997802734375,
                    886.84002685546875, 889.9000244140625, 892.95001220703125, 896.010009765625, 899.05999755859375,
                    902.1199951171875, 905.17999267578125, 908.239990234375, 911.29998779296875, 914.3599853515625,
                    917.41998291015625, 920.47998046875, 923.54998779296875, 926.6099853515625, 929.67999267578125,
                    932.739990234375, 935.80999755859375, 938.8800048828125, 941.95001220703125, 945.02001953125,
                    948.0999755859375, 951.16998291015625, 954.239990234375, 957.32000732421875, 960.4000244140625,
                    963.469970703125, 966.54998779296875, 969.6300048828125, 972.71002197265625, 975.78997802734375,
                    978.8800048828125, 981.96002197265625, 985.04998779296875, 988.1300048828125, 991.219970703125,
                    994.30999755859375, 997.4000244140625, 1000.489990234375, 1003.5800170898438]

    # lambda_min = lambda_space
    # lambda_max = 1004
    # lambda_delta = (lambda_max - lambda_min) / bands
    # lambda_space = np.linspace(lambda_min, lambda_max, bands)

    @staticmethod
    def lambda2layer(lmd):
        diffs = [abs(lmd-l) for l in SpecimIQ.lambda_space]
        return diffs.index(min(diffs))

    @staticmethod
    def cube2rgb(cube):
        # wavelengths of red, green, blue (standard settings in SpecimIQ Studio)
        r = 598
        g = 548
        b = 449
        # rgb = np.dstack((cube[:, :, int((r - lambda_min) / lambda_delta)],
        #                  cube[:, :, int((g - lambda_min) / lambda_delta)],
        #                  cube[:, :, int((b - lambda_min) / lambda_delta)]))
        rgb = np.dstack((cube[:, :, SpecimIQ.lambda2layer(r)],
                         cube[:, :, SpecimIQ.lambda2layer(g)],
                         cube[:, :, SpecimIQ.lambda2layer(b)]))

        # clip anything above white
        rgb[rgb > 1] = 1
        return rgb

    @staticmethod
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
        raw_data = np.reshape(raw_data, (SpecimIQ.rows, SpecimIQ.bands, SpecimIQ.cols))
        raw_data = np.rot90(raw_data, k=3, axes=(0,2))

        #read white and black ref
        try:
            with open(dref_file, mode='rb') as file:  # b is important -> binary
                dref_bts = file.read()
            with open(wref_file, mode='rb') as file:  # b is important -> binary
                wref_bts = file.read()

            dref_data = np.float32(np.frombuffer(dref_bts, dtype=np.float16))
            wref_data = np.float32(np.frombuffer(wref_bts, dtype=np.float16))

            ref_size = int(len(dref_data)/(SpecimIQ.bands))


            #http://www.specim.fi/iq/manual/software/iq/topics/data-cube.html
            dref_data = np.reshape(dref_data, (SpecimIQ.bands, ref_size))
            wref_data = np.reshape(wref_data, (SpecimIQ.bands, ref_size))
            dref = np.mean(dref_data, axis=1)
            wref = np.mean(wref_data, axis=1)



            #plot white and dark references
            if verbose:
                f, (dplot, wplot) = plt.subplots(1,2)
                dplot.plot(range(SpecimIQ.bands),dref)
                # for i in range(ref_size):
                #     dplot.plot(range(bands), dref_data[:, i])
                dplot.set_title('dark reference')
                wplot.plot(range(SpecimIQ.bands),wref)
                # for i in range(ref_size):
                #     wplot.plot(range(bands), wref_data[:, i])
                wplot.set_title('white reference')
                #f.set_figwidth('20')
                plt.show()

            refl = raw_data * 0
            # use mean?
            # for i in range(bands):
            #     refl[:, i, :] = (raw_data[:, i, :]-dref[i]) / (wref[i]-dref[i])
            # or use all values? who knows?
            for i in range(SpecimIQ.bands):
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
            rgb = SpecimIQ.cube2rgb(refl)
            plt.figure(figsize=(10, 10))
            plt.title('Composed RGB image')
            plt.imshow(rgb, extent=(0,50,0,50))
            plt.show()

        return refl

