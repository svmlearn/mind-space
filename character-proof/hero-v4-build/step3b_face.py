# Face readability pass: flatten the front hair/bangs onto the forehead so the eyes read from the
# ~35-45 deg game camera, shrink the ears, clamp the leftover hood lip, then repaint the face from
# the front painting on the new geometry and clean nape/cuff/hair specks.
import numpy as np, cv2, sys
from heroio import *
from scipy.interpolate import griddata
from scipy.ndimage import gaussian_filter
def sm(a,b,v): t=np.clip((v-a)/(b-a),0,1); return t*t*(3-2*t)
d=np.load('../work/geom2.npz'); P0=d['P'].copy(); UV=d['UV']; F=d['F']
a=cv2.imread('../work/atlas_final2.png'); r=a.shape[0]
XC=-0.01
c=a[np.clip((UV[:,1]*r).astype(int),0,r-1),np.clip((UV[:,0]*r).astype(int),0,r-1)]
Hv=cv2.cvtColor(c[None],cv2.COLOR_BGR2HSV)[0].astype(int)
skinv=(Hv[:,0]<25)&(Hv[:,1]>40)&(P0[:,1]>1.45)
# --- face surface z(x,y) from skin verts (front only), extended upward under the hair
fs=skinv&(P0[:,2]>0.12)&(P0[:,1]<1.80)&(np.abs(P0[:,0]-XC)<0.26)
gx=np.linspace(-0.40,0.40,41)+XC; gy=np.linspace(1.45,2.30,44)
GX,GY=np.meshgrid(gx,gy)
zs=griddata(P0[fs][:,[0,1]],P0[fs][:,2],(GX,np.minimum(GY,1.79)),method='linear')
zn=griddata(P0[fs][:,[0,1]],P0[fs][:,2],(GX,np.minimum(GY,1.79)),method='nearest')
zs=np.where(np.isnan(zs),zn-0.6*np.maximum(np.abs(GX-XC)-0.22,0),zs)
# skull curves back above the brow
zs=zs-0.9*np.maximum(GY-1.92,0)**2*4
zs=gaussian_filter(zs,1.0)
# smooth parametric face surface (quadratic in x,y, fitted on the visible face skin); the
# grid version above trusted the face centre too far out to the temples
fs2=skinv&(P0[:,1]>1.5)&(P0[:,1]<1.80)&(P0[:,2]>0.05)&(np.abs(P0[:,0]-XC)<0.27)
_dx=P0[fs2,0]-XC; _dy=P0[fs2,1]-1.65
CO=np.linalg.lstsq(np.c_[np.ones_like(_dx),_dx,_dx**2,_dy,_dy**2,_dx*_dy],P0[fs2,2],rcond=None)[0]
def zface(x,y):
    dx=x-XC; dy=np.minimum(y,1.78)-1.65
    zz=CO[0]+CO[1]*dx+CO[2]*dx**2+CO[3]*dy+CO[4]*dy**2+CO[5]*dx*dy
    return zz-3.6*np.maximum(y-1.92,0)**2
BANG=float(sys.argv[1]) if len(sys.argv)>1 else 0.12   # how much of the hair's forward overhang survives just above the eyes
KA=float(sys.argv[4]) if len(sys.argv)>4 else 1.95
KB=float(sys.argv[5]) if len(sys.argv)>5 else 2.30
EAR=float(sys.argv[2]) if len(sys.argv)>2 else 0.80
def deform(X):
    X=X.copy(); x,y,z=X[...,0],X[...,1],X[...,2]
    zf=zface(x,y)+0.012
    # keep (survive) fraction of forward overhang: tiny over the eyes, back to full on the crown
    keep=BANG+(1-BANG)*sm(KA,KB,y)
    lat=1-sm(0.34,0.46,np.abs(x-XC))
    band=sm(1.60,1.68,y)*lat*sm(0.0,0.10,z)
    over=np.maximum(z-zf,0)
    z2=z-over*(1-keep)*band
    # ears: shrink toward the root
    ax=np.abs(x-XC); sg=np.sign(x-XC)
    we=sm(0.22,0.28,ax)*sm(1.50,1.56,y)*(1-sm(1.80,1.86,y))*(1-sm(0.10,0.18,z))*sm(-0.16,-0.10,z)
    s=1-(1-EAR)*we
    root=XC+sg*0.24
    x2=root+(x-root)*s; y2=1.66+(y-1.66)*s; z2=-0.02+(z2+0.02)*(1-(1-s)*0.6)+ (z2)*(1-0.6)*0  # mild in depth
    z2=np.where(we>0,-0.02+(z2+0.02)*(1-(1-EAR)*0.6*we),z2)
    # hood lip seen in profile / hood dome on the back: hard clamp the back collar to a turtleneck
    xx=np.abs(x2+0.025)
    zl=-0.21+0.06*sm(1.25,1.52,y2)+0.12*np.clip(xx/0.3,0,1)**2
    wl=sm(1.12,1.22,y2)*(1-sm(1.53,1.58,y2))*(1-sm(0.40,0.46,xx))
    z2=np.where(z2<zl,z2+(zl-z2)*wl,z2)
    X[...,0]=x2; X[...,1]=y2; X[...,2]=z2
    return X
hairv=(Hv[:,0]>=92)&(Hv[:,0]<112)&(Hv[:,1]>110)
P=deform(P0)
olw=1-(1-sm(0.03,0.06,np.abs(P[:,2]-zface(P[:,0],P[:,1]))))*sm(1.58,1.64,P[:,1])*(1-sm(1.92,2.0,P[:,1]))*(1-sm(0.30,0.38,np.abs(P[:,0]-XC)))*(P[:,2]>0.05)
print('no-outline verts',(olw<0.5).sum())
# step3 hair exclusion for the lip clamp: undo it on hair verts
P[hairv,2]=np.where(P0[hairv,1]>1.5,P[hairv,2],P0[hairv,2]) if False else P[hairv,2]
mv=np.linalg.norm(P-P0,axis=1); print('moved>2mm',(mv>0.002).sum(),'max',mv.max().round(3))
# ---------------- texture
t=np.load('../work/tmap.npz'); pos0,fid=t['pos'],t['fid']; v=fid>=0
pos=deform(pos0)
N,FN=vnormals(P,F); nrm=np.zeros_like(pos); nrm[v]=FN[fid[v]]
out=a.copy()
pa=cv2.imread('../inputs/front.png',cv2.IMREAD_UNCHANGED)
k,cx,by,mx=372.0,513.0,930.0,-0.054
# seen from ~40 deg above the eyes foreshorten into slits: stretch the painted eyes vertically
# (sample the painting closer to the eye line) so they still read open in the game view
EYS=float(sys.argv[6]) if len(sys.argv)>6 else 1.18
dy=pos[:,:,1]-1.695
win=(1-sm(0.075,0.125,np.abs(dy)))*(1-sm(0.26,0.33,np.abs(pos[:,:,0]+0.062)))
ys=pos[:,:,1]-dy*(1-1/EYS)*win
px=cx+(pos[:,:,0]-mx)*k; py=by-ys*k
samp=cv2.remap(pa,px.astype(np.float32),py.astype(np.float32),cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT,borderValue=(0,0,0,0))
fc=pos[:,:,0]-XC
# taller ellipse: now covers the brow and the painted bang line, which sits flush on the face
ell=(fc/0.31)**2+((pos[:,:,1]-1.69)/np.where(pos[:,:,1]>1.69,0.22,0.25))**2
front_ok=pos[:,:,2]>zface(pos[:,:,0],pos[:,:,1])-0.06
flush=1-sm(0.035,0.07,np.abs(pos[:,:,2]-zface(pos[:,:,0],pos[:,:,1])))
# front visibility: a texel gets the painting if it is the frontmost surface along the front view
# (depth map from the dense texel cloud), so stray strands that end up in front of the eyes are
# painted as face too
BIN=0.006
hv=v&(pos[:,:,1]>1.45)&(pos[:,:,2]>-0.1)
bx=np.floor((pos[:,:,0]+0.6)/BIN).astype(int); byy=np.floor((pos[:,:,1]-1.4)/BIN).astype(int)
dm=np.full((300,200),-9.0)
np.maximum.at(dm,(bx[hv].clip(0,299),byy[hv].clip(0,199)),pos[:,:,2][hv])
from scipy.ndimage import maximum_filter
dm=maximum_filter(dm,size=3)
front_vis=np.zeros_like(v)
front_vis[hv]=pos[:,:,2][hv]>=dm[bx[hv].clip(0,299),byy[hv].clip(0,199)]-0.025
wf=(1-sm(0.6,1.0,ell))*np.maximum(np.maximum(sm(0.30,0.65,nrm[:,:,2]),flush)*front_ok,front_vis*sm(0.0,0.25,nrm[:,:,2]))*(samp[:,:,3]/255.0)*v*sm(1.49,1.55,pos[:,:,1])
def hsv(b): return cv2.cvtColor(b,cv2.COLOR_BGR2HSV).astype(np.float32)
Hs=hsv(samp[:,:,:3]); H3=hsv(out)
ring=v&(wf>0.05)&(wf<0.4)&(Hs[:,:,0]<30)&(H3[:,:,0]<30)
gain=np.median(H3[:,:,2][ring])/max(np.median(Hs[:,:,2][ring]),1); print('face V gain',gain)
GAIN=float(sys.argv[3]) if len(sys.argv)>3 else 0.9
sb=samp[:,:,:3].astype(np.float32)*GAIN
out=(out.astype(np.float32)*(1-wf[...,None])+sb*wf[...,None]).clip(0,255).astype(np.uint8)
np.save('../work/facew3.npy',wf)
# ---------------- specks
H=hsv(out); x,y,z=pos[...,0],pos[...,1],pos[...,2]
def fill_from(img_,known,todo,iters=60):
    m=known.astype(np.float32); acc=img_.astype(np.float32)*m[...,None]; todo=todo.copy()
    for i in range(iters):
        if not todo.any(): break
        bs=cv2.blur(acc,(5,5)); bm=cv2.blur(m,(5,5))
        g=todo&(bm>0.05); acc[g]=bs[g]/bm[g][:,None]; m[g]=1; todo&=~g
    o=img_.copy(); o[m>0]=acc[m>0].clip(0,255).astype(np.uint8); return o
hairT=(H[:,:,0]>=88)&(H[:,:,0]<115)&(H[:,:,1]>90)
# 1) nape: dark dots on the back collar/neck
nape=v&(z<-0.04)&(y>1.40)&(y<1.64)&(np.abs(x+0.02)<0.34)&(wf<0.05)
hairStrict=(H[:,:,0]>=92)&(H[:,:,0]<112)&(H[:,:,1]>110)&(H[:,:,2]>60)
darkd=nape&~hairStrict&((H[:,:,2]<60)|(H[:,:,1]<45))
darkd=cv2.dilate(darkd.astype(np.uint8),np.ones((3,3),np.uint8),iterations=2).astype(bool)&nape&~hairStrict
swe=v&(y>1.15)&(y<1.35)&(z<-0.1)&(np.abs(H[:,:,0]-82)<10)&(H[:,:,1]>90)
print('nape dark',darkd.sum())
# 2) yellow / ochre specks inside the hair (outside the face and the sweater diamond)
hairzone=v&(y>1.55)&(wf<0.05)
yel=hairzone&(H[:,:,0]>=12)&(H[:,:,0]<52)&(H[:,:,1]>50)
skinish=(H[:,:,0]<25)
# keep ears/face skin: only specks surrounded by hair
hairfrac=cv2.blur(hairT.astype(np.float32),(15,15))
yel&=hairfrac>0.45
yel=cv2.dilate(yel.astype(np.uint8),np.ones((3,3),np.uint8),iterations=1).astype(bool)&hairzone&~(hairfrac<0.3)
print('hair specks',yel.sum())
# 3) cuffs: brown/skin fringe on the sleeve end, dark fingertip specks
handz=v&(np.abs(x+0.025)>0.33)&(y>0.6)&(y<1.0)
sleeveT=(np.abs(H[:,:,0]-80)<14)&(H[:,:,1]>70)
sleevefrac=cv2.blur(sleeveT.astype(np.float32),(13,13))
fringe=handz&~sleeveT&(sleevefrac>0.35)&(sleevefrac<0.95)&((H[:,:,2]<170)|(H[:,:,1]<90))
darkh=handz&~sleeveT&(H[:,:,2]<95)&(sleevefrac<0.2)
print('cuff fringe',fringe.sum(),'dark hand',darkh.sum())
bad=darkd|yel|fringe|darkh
known=v&~bad
# fringe: grow from sleeve side preferentially
out=fill_from(out,known&~(handz&~sleeveT&(sleevefrac>0.1)) | (known&sleeveT),fringe)
out=fill_from(out,v&~(darkd|yel|darkh),darkd|yel|darkh)
# back: the painted hood arc is low-frequency shading -> flatten it, keep the fabric grain
Hb=hsv(out)
hairB=(Hb[:,:,0]>=92)&(Hb[:,:,0]<112)&(Hb[:,:,1]>110)&(y>1.45)
wb=v*sm(-0.04,-0.10,z)*sm(1.02,1.10,y)*(1-sm(1.50,1.56,y))*(1-sm(0.28,0.38,np.abs(x+0.02)))*(~hairB)
sweB=v&(y>1.0)&(y<1.12)&(z<-0.1)&(np.abs(x+0.02)<0.2)
baseB=np.median(out[sweB],0).astype(np.float32)
o32=out.astype(np.float32); grain=o32-cv2.GaussianBlur(o32,(0,0),2.5)
flat=baseB[None,None,:]+grain*0.7
out=(o32*(1-wb[...,None])+flat*wb[...,None]).clip(0,255).astype(np.uint8)
# pad gutter
m=v.astype(np.float32); acc=out.astype(np.float32)*m[...,None]
for i in range(12):
    bs=cv2.blur(acc,(3,3)); bm=cv2.blur(m,(3,3)); g=(m==0)&(bm>0); acc[g]=bs[g]/bm[g][:,None]; m[g]=1
out=np.where(v[...,None],out,acc.clip(0,255).astype(np.uint8))
cv2.imwrite('../work/atlas_final3.png',out)
np.savez('../work/geom3.npz',P=P,UV=UV,F=F,olw=olw)
np.savez('../work/tpos3.npz',pos=pos)
save('../work/hero3b.glb',P,UV,F,out,N=N)
# ---------------- sliver faces: UV triangles too small to own texels sample the gutter/neighbour
# charts (the dark/white specks at the nape and cuffs). Paint their UV footprint with the colour of
# the nearest well-rasterized 3D neighbours.
from scipy.spatial import cKDTree
out=cv2.imread('../work/atlas_final3.png')
T=UV[F]*r; uvA=0.5*np.abs((T[:,1,0]-T[:,0,0])*(T[:,2,1]-T[:,0,1])-(T[:,2,0]-T[:,0,0])*(T[:,1,1]-T[:,0,1]))
cen3=P[F].mean(1)
def samp_face(fs):
    c=T[fs].mean(1); xs=np.clip(c[:,0].astype(int),0,r-1); ys=np.clip(c[:,1].astype(int),0,r-1)
    return out[ys,xs].astype(np.float32)
good=np.where(uvA>=6)[0]; tiny=np.where(uvA<6)[0]
kd=cKDTree(cen3[good]); dd,nn=kd.query(cen3[tiny],k=6)
ref=samp_face(good)[nn].mean(1); cur=samp_face(tiny)
diff=np.abs(ref-cur).sum(1); fix=tiny[diff>60]; refc=ref[diff>60]
print('tiny faces',len(tiny),'repainted',len(fix))
for f,cc in zip(fix,refc):
    tri=T[f]
    pts=np.round(tri).astype(np.int32)
    cv2.fillConvexPoly(out,pts,tuple(float(v) for v in cc))
    for p_ in pts: cv2.circle(out,tuple(int(v) for v in p_),1,tuple(float(v) for v in cc),-1)
cv2.imwrite('../work/atlas_final3.png',out)
save('../work/hero3b.glb',P,UV,F,out,N=N)
