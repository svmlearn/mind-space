# s3_face.py : project the painted turnaround's front face (eyes, brows, nose, smile, blush) onto the
# model's face, front-facing visible texels only, fading out towards the side of the face; texels
# where the painting shows hair but the model shows forehead get the painted skin tone.
# in: work/shape.npz base2k.png, painting front-white.png  out: work/atlas_face.png, facew.npy, face.json
import os
WK=os.environ.get('WORK','../work'); TEX=os.environ.get('TEX','base2k.png')   # high-res build: WORK=../work_hr TEX=basecolor_4k.png
import numpy as np, cv2, json, sys
from scipy.spatial import cKDTree
from heroio import texel_map, vnormals
from swr import render
PAINT=os.environ.get('PAINT','../inputs/front-white.png')   # front view cut from character-proof/assets/painted-turnaround.png
# landmarks (eye centres): painting px (460,295)/(565,293.3); model (-0.1225,1.6475)/(0.1175,1.6475)
SX,SY=0.24/105,0.00235; PC=(512.5,294.2); MC=(-0.0025,1.6475)
def p2m(px,py): return MC[0]+(px-PC[0])*SX, MC[1]-(py-PC[1])*SY
def m2p(x,y): return PC[0]+(x-MC[0])/SX, PC[1]-(y-MC[1])/SY
def sm(a,b,v): t=np.clip((v-a)/(b-a),0,1); return t*t*(3-2*t)
d=np.load(WK+'/shape.npz'); P,UV,F,weld=d['P'],d['UV'],d['F'],d['weld']
img=cv2.imread(WK+'/'+TEX); R=img.shape[0]
pos,fid=texel_map(P,UV,F,R)
np.savez_compressed(WK+'/tmap_shape.npz',pos=pos,fid=fid)
N,_=vnormals(P,F)
_,winv=np.unique(weld,return_inverse=True); NA=np.zeros((winv.max()+1,3)); np.add.at(NA,winv,N); N=(NA/np.linalg.norm(NA,axis=1,keepdims=True))[winv]
tv=fid>=0
nt=np.zeros((R,R,3),np.float32); nt[tv]=N[F[fid[tv]]].mean(1)
# front visibility: z-buffer of the head from the front
S=2000; col,zb,_,_=render(P,UV,F,img,0,1.65,S,1000)
px=((pos[...,0]-0)*S+500); py=(500-(pos[...,1]-1.65)*S)
inb=tv&(px>=0)&(px<999)&(py>=0)&(py<999)
zf=np.full((R,R),np.inf,np.float32); zf[inb]=zb[py[inb].astype(int),px[inb].astype(int)]
vis=inb&(pos[...,2]>=zf-0.006)
# painting: hair (big dark-teal regions) / background / skin masks
pt=cv2.imread(PAINT); ph=cv2.cvtColor(pt,cv2.COLOR_BGR2HSV).astype(int)
phair=((ph[...,0]>=80)&(ph[...,0]<=115)&(ph[...,1]>90)&(ph[...,2]<200)).astype(np.uint8)
n,lab,st,_=cv2.connectedComponentsWithStats(phair)
big=np.isin(lab,[i for i in range(1,n) if st[i,4]>1500]).astype(np.uint8)
big=cv2.morphologyEx(big,cv2.MORPH_OPEN,np.ones((3,3),np.uint8))
yy,xx=np.mgrid[:1024,:1024]
oval=((((xx-512)/104.0)**2+((yy-300)/86.0)**2)<1).astype(np.float32)
pskin=(ph[...,0]<25)&(ph[...,1]>40)&(ph[...,2]>150)
yy,xx=np.mgrid[:1024,:1024]
oval=((((xx-512)/104.0)**2+((yy-300)/86.0)**2)<1).astype(np.float32)
pskin=(ph[...,0]<25)&(ph[...,1]>40)&(ph[...,2]>150)
skin_p=np.median(pt[pskin&(oval>0)&(big==0)&(yy>300)&(yy<330)],0)
# the painted left brow is mostly under a bang: mirror the painted right brow over to the left
small=(phair>0)&(big==0)
rb=np.zeros_like(small); rb[228:262,540:605]=small[228:262,540:605]
rb=cv2.dilate(rb.astype(np.uint8),np.ones((3,3),np.uint8))>0
lb=rb[:,::-1]; sh=1024-2*512.5           # mirror about the eye midline x=512.5
M=np.float32([[1,0,-sh],[0,1,0]]); lb=cv2.warpAffine(lb.astype(np.uint8),M,(1024,1024))>0
src=cv2.warpAffine(pt[:,::-1].copy(),M,(1024,1024))
lbw=cv2.GaussianBlur(lb.astype(np.float32),(0,0),1.0)
pt=(pt*(1-lbw[...,None])+src*lbw[...,None]).astype(np.uint8)
# forehead band (brows .. upper lids): the painted bangs there are inpainted to skin, so the
# model's own bangs (geometry) decide where hair is, and the brows/lids come from the painting
band=(oval>0)&(yy>=226)&(yy<=276)&(big>0)&~lb
band=cv2.dilate(band.astype(np.uint8),np.ones((3,3),np.uint8))&(~lb).astype(np.uint8)&(oval>0)
pt[band>0]=skin_p; pt=np.where((band>0)[...,None],cv2.GaussianBlur(pt,(0,0),2.5),pt)
pt=(pt*(1-lbw[...,None])+src*lbw[...,None]).astype(np.uint8)
big[band>0]=0
pw=cv2.GaussianBlur(oval*(1-big),(0,0),2.0)          # painting weight: face oval, not hair
pw_hair=cv2.GaussianBlur(oval*big,(0,0),2.0)
# model texels
H=cv2.cvtColor(img,cv2.COLOR_BGR2HSV).astype(int)
hairf=d['hair'][F].all(1)                       # hair triangles (geometry), not dark texture spots
mhair=(tv&hairf[np.maximum(fid,0)]).astype(np.float32)
mhair=cv2.dilate(mhair,np.ones((3,3),np.uint8))
# a lock tip pokes into the left eye: inside the painted eyes the painting wins over hair
for ex,ey in ((460,295),(565,293.3)):
    mx_,my_=p2m(ex,ey); mhair[(((pos[...,0]-mx_)/(36*SX))**2+((pos[...,1]-my_)/(34*SY))**2<1)&(pos[...,2]>0.15)]=0
mskin=(H[...,0]<25)&(H[...,1]>40)&(H[...,2]>120)&tv
# map texels -> painting px
qx,qy=m2p(pos[...,0],pos[...,1])
samp=cv2.remap(pt,qx.astype(np.float32),qy.astype(np.float32),cv2.INTER_LINEAR,borderValue=(255,255,255)).astype(np.float32)
wp=cv2.remap(pw.astype(np.float32),qx.astype(np.float32),qy.astype(np.float32),cv2.INTER_LINEAR,borderValue=0)
wh=cv2.remap(pw_hair.astype(np.float32),qx.astype(np.float32),qy.astype(np.float32),cv2.INTER_LINEAR,borderValue=0)
nz=nt[...,2]
facing=sm(0.25,0.65,nz)
# creases under the bangs face up/down but are seen from the front: inside the central face take
# every front-visible texel (the side fall-off only matters on the cheeks)
facing=np.maximum(facing,sm(0.20,0.14,np.abs(pos[...,0]))*sm(1.62,1.66,pos[...,1])*(nz>-0.2))
base_w=vis*facing*(1-mhair)*sm(1.43,1.47,pos[...,1])
# colour match: painting skin -> model face skin (LAB mean/std on skin)
mfs=mskin&vis&(nz>0.6)&(pos[...,1]>1.5)&(pos[...,1]<1.62)
L1=cv2.cvtColor(pt,cv2.COLOR_BGR2LAB).astype(np.float32); L2=cv2.cvtColor(img,cv2.COLOR_BGR2LAB).astype(np.float32)
ps=L1[pskin&(oval>0)&(big==0)]; ms=L2[mfs]
mu1,sd1,mu2,sd2=ps.mean(0),ps.std(0),ms.mean(0),ms.std(0)
sl=cv2.cvtColor(np.clip(samp,0,255).astype(np.uint8),cv2.COLOR_BGR2LAB).astype(np.float32)
sh_=cv2.cvtColor(np.clip(samp,0,255).astype(np.uint8),cv2.COLOR_BGR2HSV).astype(np.float32)
skinness=sm(30,18,sh_[...,0])*sm(30,60,sh_[...,1])*sm(130,170,sh_[...,2])
sl=sl+(mu2-mu1)*skinness[...,None]
samp2=cv2.cvtColor(np.clip(sl,0,255).astype(np.uint8),cv2.COLOR_LAB2BGR).astype(np.float32)
skin_m=np.median(img[mfs],0).astype(np.float32)
out=img.astype(np.float32)
w1=(base_w*wp)[...,None]; w2=(base_w*wh*(1-wp)*(~(mhair>0)))[...,None]
out=out*(1-w1)+samp2*w1
out=out*(1-w2)+skin_m*w2
out=out.astype(np.uint8)
# pad edits into the gutters (mip/bilinear bleeding)
ed=((w1[...,0]+w2[...,0])>0.01)
acc=np.where(tv[...,None],out,0).astype(np.float32); m=tv.astype(np.float32)
for _ in range(6):
    a2=cv2.dilate(acc,np.ones((3,3),np.uint8)); m2=cv2.dilate(m,np.ones((3,3),np.uint8))
    acc=np.where((m>0)[...,None],acc,a2); m=np.maximum(m,m2)
near=cv2.dilate(ed.astype(np.uint8),np.ones((9,9),np.uint8))>0
out[~tv&near&(m>0)]=acc[~tv&near&(m>0)].astype(np.uint8)
cv2.imwrite(WK+'/atlas_face.png',out)
if 'dbg' in sys.argv: cv2.imwrite('../inspect/paint-mod.png',cv2.resize((pt*(0.4+0.6*pw[...,None])).astype(np.uint8)[200:400,400:630],None,fx=3,fy=3)); cv2.imwrite(WK+'/dbg_w.png',np.dstack([vis*255,(base_w*wp)*255,(base_w*wh*(1-wp))*255]).astype(np.uint8)); cv2.imwrite(WK+'/dbg_m.png',np.dstack([mhair*255,facing*255,wh*255]).astype(np.uint8))
np.save(WK+'/facew.npy',np.clip(w1[...,0]+w2[...,0],0,1).astype(np.float16))
# eyes for the blink shader (bind space): painted eye boxes -> model
eyes={}
for nm,(ex,ey) in (('L',(460,295)),('R',(565,293.3))):
    eyes[nm]=[round(v,4) for v in p2m(ex,ey)]
eyes['r']=[round(30*SX,4),round(34*SY,4)]
fz=pos[...,2][vis&(np.abs(pos[...,1]-1.65)<0.03)&(np.abs(np.abs(pos[...,0])-0.12)<0.03)]
eyes['zmin']=round(float(np.percentile(fz,5))-0.03,4)
sk=skin_m[::-1]/255.0
eyes['skin']=[round(0.94*float(((c+0.055)/1.055)**2.4),4) for c in sk]
json.dump(dict(eyes=eyes),open(WK+'/face.json','w'))
print(eyes, 'edited texels',ed.sum())
