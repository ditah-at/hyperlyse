import os
from matplotlib import pyplot as plt

this_dir = os.path.dirname(os.path.realpath(__file__))
fh = os.path.join(this_dir, 'bull_bottomrightpixel_hyperlyse.dpt')
fs = os.path.join(this_dir, 'bull_bottomrightpixel_specim.dpt')

with open(fh, 'r') as f:
    lines = f.read().splitlines()
    xh = [float(l.split(',')[0]) for l in lines]
    yh = [float(l.split(',')[1]) for l in lines]
    dxh = [xh[i]-xh[i-1] for i in range(1, len(xh))]

with open(fs, 'r') as f:
    lines = f.read().splitlines()
    xs = [float(l.split(',')[0]) for l in lines]
    ys = [float(l.split(',')[1]) for l in lines]
    dxs = [xs[i] - xs[i - 1] for i in range(1, len(xs))]

plt.plot(dxh)
plt.show()

plt.plot(dxs)
plt.show()