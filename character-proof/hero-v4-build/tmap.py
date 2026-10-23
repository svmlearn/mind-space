import numpy as np, time
from heroio import *
d=np.load('../work/geom1.npz'); P,UV,F=d['P'],d['UV'],d['F']
img=cv2.imread('../work/atlas_raw.png'); res=img.shape[0]; print(img.shape)
t=time.time(); pos,fid=texel_map(P,UV,F,res); print('raster',time.time()-t,(fid>=0).mean())
np.savez_compressed('../work/tmap.npz',pos=pos,fid=fid)
