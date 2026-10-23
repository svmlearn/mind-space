import numpy as np, sys
from heroio import *
from scipy.spatial import ConvexHull
from scipy.spatial import Delaunay
P,UV,F,img=load('../gen/trellis-multi-s1.glb')
H0=P[:,1].max()-P[:,1].min(); S=2.3/H0
P=P*S; P[:,1]-=P[:,1].min()
H=P[:,1].max()
foot=P[P[:,1]<0.06*H]; P[:,0]-=np.median(foot[:,0]); 
# z center: center of shoe footprint
P[:,2]-=(foot[:,2].min()+foot[:,2].max())/2
print('height',H,'S',S)
# flange removal
low=P[:,1]<0.028*H
upper=(P[:,1]>0.035*H)&(P[:,1]<0.07*H)
keep_face=np.ones(len(F),bool)
for side in (-1,1):
    u=P[upper&(np.sign(P[:,0])==side)][:,[0,2]]
    hull=ConvexHull(u); poly=u[hull.vertices]
    c=poly.mean(0); poly=c+(poly-c)*1.0+ (poly-c)/np.linalg.norm(poly-c,axis=1,keepdims=True)*0.025
    inside=Delaunay(poly).find_simplex(P[:,[0,2]])>=0
    bad=low&(np.sign(P[:,0])==side)&~inside
    keep_face&=~bad[F].any(1)
    print('side',side,'removed verts',bad.sum())
F=F[keep_face]; print('faces',len(F))
# drop unused verts
used=np.unique(F); remap=-np.ones(len(P),int); remap[used]=np.arange(len(used))
P=P[used]; UV=UV[used]; F=remap[F]
np.savez('../work/geom1.npz',P=P,UV=UV,F=F); cv2.imwrite('../work/atlas_raw.png',img)
save('../work/hero1.glb',P,UV,F,img)
