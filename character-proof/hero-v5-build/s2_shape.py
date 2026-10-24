# s2_shape.py [SHRINK] [BANG] : pull the hair volume in towards the skull (closer to the turnaround
# silhouette) while hair touching skin (hairline, sideburns, bangs on the forehead) stays put; and
# lift the long front lock off the left eye. in: work/dec.npz base2k.png  out: work/shape.npz
import os
WK=os.environ.get('WORK','../work'); TEX=os.environ.get('TEX','base2k.png')   # high-res build: WORK=../work_hr TEX=basecolor_4k.png
import numpy as np, cv2, sys
from scipy.spatial import cKDTree
SHR=float(sys.argv[1]) if len(sys.argv)>1 else 0.14
BANG=float(sys.argv[2]) if len(sys.argv)>2 else 0.0   # 1 = lift the front lock (leaves a crease; off)
d=np.load(WK+'/dec.npz'); P,UV,F,weld=d['P'].copy(),d['UV'],d['F'],d['weld']
img=cv2.imread(WK+'/'+TEX); h,w=img.shape[:2]
col=img[np.clip((UV[:,1]*h).astype(int),0,h-1),np.clip((UV[:,0]*w).astype(int),0,w-1)]
H=cv2.cvtColor(col[None],cv2.COLOR_BGR2HSV)[0].astype(int)
def sm(a,b,v): t=np.clip((v-a)/(b-a),0,1); return t*t*(3-2*t)
y=P[:,1]
hairv=(y>1.49)&(H[:,0]>=93)&(H[:,0]<=112)&(H[:,2]<140)
skinv=(H[:,0]<25)&(H[:,1]>40)&(H[:,2]>120)&(y>1.42)
# per geometric vertex (UV seams split vertices): hair if any copy is hair, skin if any copy is skin
ng=weld.max()+1
hg=np.zeros(ng,bool); np.logical_or.at(hg,weld,hairv); sg=np.zeros(ng,bool); np.logical_or.at(sg,weld,skinv)
hair=hg[weld]&~sg[weld]
# soft hair mask (16 nearest neighbours) so the shrink field has no steps between hair / non-hair
KNN=int(min(96,16*max(1,len(F)/55000)))   # same neighbourhood size on the 500k mesh
_,nn=cKDTree(P).query(P,k=KNN); hs=hair[nn].mean(1)
tree=cKDTree(P[skinv]); dsk,_=tree.query(P,k=1)
C=np.array([0.0,1.74,-0.07])            # skull centre (between the ears, eye height)
r=P-C
wgt=sm(0.012,0.09,dsk)*hs*sm(1.50,1.62,y)  # 0 on the hairline, full on the outer volume
# shrink more on the puffy sides/back/top than at the front fringe
front=sm(0.05,0.22,P[:,2])*(np.abs(P[:,0])<0.25)
amt=SHR*(1-0.6*front)
P=P-r*(amt*wgt)[:,None]
# long front lock over the (viewer's) left eye: hair in front of the face, below the brow line
lock=hair&(P[:,2]>0.18)&(P[:,0]>-0.27)&(P[:,0]<0.0)&(y<1.80)
lw=sm(1.80,1.68,y)*lock*BANG
P[:,1]+=0.05*lw; P[:,2]-=0.015*lw
# faces stretched into a curtain between the lifted lock and the forehead: drop them
P0=d['P']; e0=np.stack([np.linalg.norm(P0[F[:,i]]-P0[F[:,(i+1)%3]],axis=1) for i in range(3)],1).max(1)
e1=np.stack([np.linalg.norm(P[F[:,i]]-P[F[:,(i+1)%3]],axis=1) for i in range(3)],1).max(1)
bad=(e1>1.8*e0)&(e1>0.012)&(BANG>0)
F=F[~bad]; print('dropped stretched faces',bad.sum())
print('hair verts',hair.sum(),'moved',(wgt>0.05).sum(),'lock',(lw>0.05).sum())
# soften the front-face relief before the painted face is projected (Hunyuan sculpted a nose ridge,
# a mouth slit and eye pits: under the painted face they read as stiff, and from the high game camera
# the slit opened up the smile). Taubin smoothing on welded vertices keeps volume and silhouette.
FS=int(sys.argv[3]) if len(sys.argv)>3 else int(80*max(1,len(F)/55000))   # ~same smoothing radius at any density
ax=np.abs(P[:,0]); yy=P[:,1]
g=sm(0.20,0.13,ax)*sm(1.40,1.45,yy)*sm(1.86,1.80,yy)*sm(0.08,0.16,P[:,2])*(1-hs)
Pw=np.zeros((ng,3)); np.add.at(Pw,weld,P); cw=np.bincount(weld,minlength=ng); Pw/=cw[:,None]
gw=np.zeros(ng); np.maximum.at(gw,weld,g)
E=np.vstack([weld[F[:,[0,1]]],weld[F[:,[1,2]]],weld[F[:,[2,0]]]]); E=np.vstack([E,E[:,::-1]])
import scipy.sparse as sp
A=sp.csr_matrix((np.ones(len(E)),(E[:,0],E[:,1])),shape=(ng,ng))
deg=np.maximum(np.asarray(A.sum(1)).ravel(),1); A=sp.diags(1/deg)@A
act=np.nonzero(gw>0)[0]; Aa=A[act]
for it in range(FS):
    for lam in (0.55,-0.58):
        Pw[act]+=lam*gw[act,None]*(Aa@Pw-Pw[act])
# nose ball + mouth slit: Taubin keeps features that span many edges (on the 500k mesh the nose
# survives it), so refill that patch with a biharmonic surface (C1 to the surrounding cheeks):
# the painted nose dot and smile then sit on a smooth face like in the painting.
hw=np.zeros(ng); np.maximum.at(hw,weld,hs)
core=(np.abs(Pw[:,0])<0.11)&(Pw[:,1]>1.48)&(Pw[:,1]<1.63)&(Pw[:,2]>-0.05)&(hw<0.5)
if core.any():
    Lu=sp.eye(ng)-A; L2=(Lu@Lu).tocsr()
    I=np.nonzero(core)[0]; K=np.nonzero(~core)[0]
    from scipy.sparse.linalg import spsolve
    rhs=-(L2[I][:,K]@Pw[K]); Pw[I]=np.c_[[spsolve(L2[I][:,I].tocsc(),rhs[:,k]) for k in range(3)]].T
    print('biharmonic nose/mouth patch verts',len(I))
P=np.where(((gw>0)|core)[weld][:,None],Pw[weld],P)
# the mouth slit's inner faces now lie on the refilled surface facing backwards: drop them
Q=P[F]; fn=np.cross(Q[:,1]-Q[:,0],Q[:,2]-Q[:,0]); cf=core[weld][F].all(1)
inner=cf&(fn[:,2]<0); F=F[~inner]; print('dropped slit faces',int(inner.sum()))
print('face smoothing verts',int((gw>0.05).sum()))
np.savez(WK+'/shape.npz',P=P.astype(np.float32),UV=UV,F=F,weld=weld,hair=hair,dsk=dsk)
