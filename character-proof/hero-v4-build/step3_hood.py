import numpy as np, cv2, scipy.sparse as sp
from heroio import *
import sys
PUSH=float(sys.argv[1]) if len(sys.argv)>1 else 0.55
SMI=int(sys.argv[2]) if len(sys.argv)>2 else 2
d=np.load('../work/geom1.npz'); P,UV,F=d['P'].copy(),d['UV'],d['F']
a=cv2.imread('../work/atlas_final.png'); r=a.shape[0]
c=a[np.clip((UV[:,1]*r).astype(int),0,r-1),np.clip((UV[:,0]*r).astype(int),0,r-1)]
H=cv2.cvtColor(c[None],cv2.COLOR_BGR2HSV)[0].astype(int)
hair=(H[:,0]>=92)&(H[:,0]<112)&(H[:,1]>110)
def sm(a,b,v): t=np.clip((v-a)/(b-a),0,1); return t*t*(3-2*t)
x=P[:,0]+0.025; y=P[:,1]; z=P[:,2]
zlim=-0.24+0.10*sm(1.25,1.52,y)+0.10*np.clip(np.abs(x)/0.3,0,1)**2
wy=sm(1.18,1.28,y)*(1-sm(1.52,1.58,y))
wx=1-sm(0.20,0.32,np.abs(x))
w=wy*wx*(~hair)
over=np.minimum(z-zlim,0)               # negative where behind the limit
P[:,2]=z-over*w*PUSH
moved=(w>0)&(over<-0.005); print('moved verts',moved.sum(),'max push %.3f'%(-over[moved]).max())
# laplacian smooth the touched band to remove creases
n=len(P); e=np.vstack([F[:,[0,1]],F[:,[1,2]],F[:,[2,0]]]); A=sp.coo_matrix((np.ones(len(e)*2),(np.r_[e[:,0],e[:,1]],np.r_[e[:,1],e[:,0]])),(n,n)).tocsr(); A.data[:]=1
deg=np.asarray(A.sum(1)).ravel()
band=(w>0.05)&(z<0.0)
for i in range(SMI):
    avg=(A@P)/deg[:,None]
    P[band]=P[band]*0.5+avg[band]*0.5
# --- texture: erase painted hood seams on the back (keep a soft fabric look)
t=np.load('../work/tmap.npz'); pos,fid=t['pos'],t['fid']; v=fid>=0
tx=pos[:,:,0]+0.025; ty=pos[:,:,1]; tz=pos[:,:,2]
Ht=cv2.cvtColor(a,cv2.COLOR_BGR2HSV).astype(int)
hairT=(Ht[:,:,0]>=92)&(Ht[:,:,0]<112)&(Ht[:,:,1]>110)&(ty>1.5)
wt=sm(1.08,1.18,ty)*(1-sm(1.54,1.6,ty))*(1-sm(0.22,0.34,np.abs(tx)))*sm(-0.05,-0.12,tz)*v*(~hairT)
sweT=v&(np.abs(Ht[:,:,0]-85)<10)&(Ht[:,:,1]>120)&(ty>1.0)&(ty<1.2)&(tz<-0.1)
base=np.median(a[sweT],0).astype(np.float32); print('back sweater base',base)
L=cv2.cvtColor(a,cv2.COLOR_BGR2GRAY).astype(np.float32); Lb=cv2.GaussianBlur(L,(0,0),3)
shade=np.clip(Lb/ max(np.median(L[sweT]),1),0.95,1.04)
tgt=base[None,None,:]*shade[...,None]
a=(a*(1-wt[...,None])+tgt*wt[...,None]).clip(0,255).astype(np.uint8)
cv2.imwrite('../work/atlas_final2.png',a)
np.savez('../work/geom2.npz',P=P,UV=UV,F=F)
N,_=vnormals(P,F)
save('../work/hero3.glb',P,UV,F,a,N=N)
