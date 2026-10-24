import numpy as np, cv2
from heroio import *
d=np.load('../work/geom1.npz'); P,UV,F=d['P'],d['UV'],d['F']
t=np.load('../work/tmap.npz'); pos,fid=t['pos'],t['fid']
img=cv2.imread('../work/atlas_raw.png'); res=img.shape[0]
N,FN=vnormals(P,F)
valid=fid>=0
nrm=np.zeros_like(pos); nrm[valid]=FN[fid[valid]]
x=pos[:,:,0]+0.025; y=pos[:,:,1]; z=pos[:,:,2]
def hsv(b): return cv2.cvtColor(b,cv2.COLOR_BGR2HSV).astype(np.float32)
out=img.copy()
H=hsv(img)
def sm(a,b,v): t=np.clip((v-a)/(b-a),0,1); return t*t*(3-2*t)
# --- regions
hand=valid&(np.abs(x)>0.34)&(y>0.6)&(y<0.93)
skinlike=(H[:,:,0]<35)&(H[:,:,1]>50)
legs=valid&(y>0.17)&(y<0.86)&~hand
shoe=valid&(y<0.2)
sweater=valid&(y>0.8)&(y<1.5)&~(hand&skinlike)
facecore=valid&(y>1.45)&(y<1.85)&(np.abs(x)<0.32)&(z>0)
def fixregion(mask,name,lowsat=True,hue=False,hue_ok=True):
    vals=img[mask]; med=np.median(hsv(vals[None])[0],0)
    Hm=H.copy()
    bad=mask&(((Hm[:,:,1]<med[1]*0.65)&lowsat)|(Hm[:,:,2]>med[2]*1.35+10))
    if hue:
        dh=np.abs(Hm[:,:,0]-med[0]); dh=np.minimum(dh,180-dh)
        bad|=mask&(dh>18)&hue_ok
    bad=cv2.dilate(bad.astype(np.uint8)*255,np.ones((3,3),np.uint8),iterations=2)>0
    bad&=mask&hue_ok
    print(name,'median hsv',med,'bad %.1f%%'%(100*bad.sum()/mask.sum()))
    return bad,med
bad_l,med_l=fixregion(legs,'pants',hue=True); bad_s,med_s=fixregion(sweater,'sweater',hue=True,hue_ok=~(valid&(np.abs(x)<0.16)&(z>0)&(y>1.0)&(y<1.35))); bad_sh,med_sh=fixregion(shoe,'shoe',False)
# soles: downward facing low texels -> shoe colour
sole=valid&(((nrm[:,:,1]<-0.5)&(y<0.08))|(y<0.04))
bad=(bad_l|bad_s|bad_sh)&~sole
def fill_from(img_,known,todo,iters=200):
    m=known.astype(np.float32); acc=img_.astype(np.float32)*m[...,None]; todo=todo.copy()
    for i in range(iters):
        if not todo.any(): break
        bs=cv2.blur(acc,(5,5)); bm=cv2.blur(m,(5,5))
        grow=todo&(bm>0.05)
        acc[grow]=bs[grow]/bm[grow][:,None]; m[grow]=1; todo&=~grow
    r=img_.copy(); r[m>0]=acc[m>0].clip(0,255).astype(np.uint8); return r, todo
out,left=fill_from(out,valid&~bad,bad&~sole); print('unfilled',left.sum())
for msk in (legs,sweater,shoe):
    good=msk&~bad&valid; L=left&msk
    if L.any(): out[L]=(np.median(img[good],0)*0.85).astype(np.uint8)
    left&=~msk
print('still left',left.sum())
# fill sole with shoe median (darker)
shoe_bgr=cv2.cvtColor(np.uint8([[med_sh*[1,1,0.8]]]),cv2.COLOR_HSV2BGR)[0,0]
out[sole]=shoe_bgr
# --- hands: hue/sat towards skin
H2=hsv(out)
skin_ref=H2[facecore&skinlike&(np.abs(x)<0.15)&(y<1.62)]
sk=np.median(skin_ref,0); print('skin hsv',sk)
hm=hand&(H2[:,:,0]<40)&(H2[:,:,1]>40)
wgt=sm(0.34,0.40,np.abs(x))[hm]
H2[:,:,0][hm]=H2[:,:,0][hm]*(1-wgt)+sk[0]*wgt
H2[:,:,1][hm]=H2[:,:,1][hm]*(1-wgt)+sk[1]*wgt
out=cv2.cvtColor(np.clip(H2,0,255).astype(np.uint8),cv2.COLOR_HSV2BGR)
cv2.imwrite('../work/atlas_clean.png',out)
np.save('../work/masks.npy',np.stack([bad,sole,hm,facecore]))

# --- global grade: lift the dark TRELLIS albedo (gamma) before matching the face
lut=(255*((np.arange(256)/255.0)**0.78)).astype(np.uint8)
out=cv2.LUT(out,lut)
# --- face projection from the approved front painting
pa=cv2.imread('../inputs/front.png',cv2.IMREAD_UNCHANGED)
k,cx,by,mx=372.0,513.0,930.0,-0.054
px=cx+(pos[:,:,0]-mx)*k; py=by-pos[:,:,1]*k
samp=cv2.remap(pa,px.astype(np.float32),py.astype(np.float32),cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT,borderValue=(0,0,0,0))
fc=pos[:,:,0]+0.01
# soft ellipse around eyes/nose/mouth/cheeks, feathered; only front-facing texels
ell=((fc)/0.30)**2+((pos[:,:,1]-1.64)/0.20)**2
wf=(1-sm(0.55,1.0,ell))*sm(0.35,0.7,nrm[:,:,2])*(samp[:,:,3]/255.0)*valid*(pos[:,:,2]>0.05)*sm(1.49,1.55,pos[:,:,1])
# match painting brightness to model skin so the patch edge disappears
Hs=hsv(samp[:,:,:3]); H3=hsv(out)
ring=valid&(wf>0.05)&(wf<0.4)&(Hs[:,:,0]<30)&(H3[:,:,0]<30)
gain=np.median(H3[:,:,2][ring])/max(np.median(Hs[:,:,2][ring]),1); print('face V gain',gain, 'ring px',ring.sum())
sb=samp[:,:,:3].astype(np.float32)*min(max(gain,0.75),1.0)
out=(out.astype(np.float32)*(1-wf[...,None])+sb*wf[...,None]).clip(0,255).astype(np.uint8)
np.save('../work/facew.npy',wf)
cv2.imwrite('../work/atlas_face.png',out)

# --- pad: bleed valid texels into the unused atlas gutter so bilinear/mip sampling never picks up junk
m=valid.astype(np.float32); acc=out.astype(np.float32)*m[...,None]
for i in range(12):
    bs=cv2.blur(acc,(3,3)); bm=cv2.blur(m,(3,3))
    grow=(m==0)&(bm>0)
    acc[grow]=bs[grow]/bm[grow][:,None]; m[grow]=1
pad=acc.clip(0,255).astype(np.uint8); out=np.where(valid[...,None],out,pad)
cv2.imwrite('../work/atlas_final.png',out)
save('../work/hero2.glb',P,UV,F,out,N=N)
