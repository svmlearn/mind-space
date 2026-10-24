# iter3 fixes on top of step3b: clean the side of the face (front painting smeared onto it),
# smaller shoes and hands, hands recoloured to the face skin, smoother turtleneck back,
# strand shading on the back of the hair. Reads geom3/atlas_final3/tpos3, writes geom4/atlas_final4.
import numpy as np, cv2, sys
from heroio import *
from scipy.ndimage import maximum_filter, gaussian_filter
def sm(a,b,v): t=np.clip((v-a)/(b-a),0,1); return t*t*(3-2*t)
d=np.load('../work/geom3.npz'); P3=d['P']; UV=d['UV']; F=d['F']; olw=d['olw']
out=cv2.imread('../work/atlas_final3.png'); r=out.shape[0]
t=np.load('../work/tmap.npz'); fid=t['fid']; v=fid>=0
pos=np.load('../work/tpos3.npz')['pos']
wf=np.load('../work/facew3.npy')
N3,FN=vnormals(P3,F); nrm=np.zeros_like(pos); nrm[v]=FN[fid[v]]
XC=-0.01
x,y,z=pos[...,0],pos[...,1],pos[...,2]
def hsv(b): return cv2.cvtColor(b,cv2.COLOR_BGR2HSV).astype(np.float32)
def fill_from(img_,known,todo,iters=80,k=5):
    m=known.astype(np.float32); acc=img_.astype(np.float32)*m[...,None]; todo=todo.copy()
    for i in range(iters):
        if not todo.any(): break
        bs=cv2.blur(acc,(k,k)); bm=cv2.blur(m,(k,k))
        g=todo&(bm>0.05); acc[g]=bs[g]/bm[g][:,None]; m[g]=1; todo&=~g
    o=img_.copy(); o[m>0]=acc[m>0].clip(0,255).astype(np.uint8); return o
A=set(sys.argv[1].split(',')) if len(sys.argv)>1 else {'side','hand','shoe','hood','hair','finger'}
H=hsv(out)
skinT=v&(H[:,:,0]<25)&(H[:,:,1]>35)&(H[:,:,2]>90)
# ---------------- A. side of the face
if 'side' in A:
    lx=x-XC
    zone=v&(y>1.50)&(y<1.88)&(np.abs(lx)>0.10)&(np.abs(lx)<0.40)&(z>-0.16)&(z<0.30)
    BIN=0.008
    by_=np.floor((y-1.4)/BIN).astype(int).clip(0,79); bz=np.floor((z+0.3)/BIN).astype(int).clip(0,79)
    cand=np.zeros_like(v)
    for s in (1,-1):
        zs=zone&(s*lx>0)
        sk=zs&skinT&(nrm[...,2]<0.75)
        surf=np.full((80,80),-9.0)
        np.maximum.at(surf,(by_[sk],bz[sk]),(s*lx)[sk])
        surf=maximum_filter(surf,size=5)
        ok=surf[by_,bz]>-1
        # non-skin texel lying on (not above) the skin surface, facing sideways -> painted smear
        c=zs&~skinT&ok&((s*lx)<=surf[by_,bz]+0.014)&(nrm[...,2]<0.5)&((H[:,:,2]<118)|(H[:,:,1]<70))&~((H[:,:,0]>55)&(H[:,:,0]<96)&(H[:,:,1]>60)&(y<1.6))
        cand|=c
    # also stray light/dark blotches on skin facing sideways (S very low = white streak)
    cand|=zone&skinT&(nrm[...,2]<0.45)&((H[:,:,1]<70)|(H[:,:,2]<120))
    cand=cv2.dilate(cand.astype(np.uint8),np.ones((3,3),np.uint8),iterations=1).astype(bool)&zone
    print('side smear texels',cand.sum())
    np.save('../work/sidecand.npy',cand)
    if 'dbg' in A:
        dbg=out.copy(); dbg[cand]=(255,0,255); save('../work/dbg_side.glb',P3,UV,F,dbg,N=N3)
    # colour from the 3D neighbourhood (UV neighbours can be other body parts): smear at the
    # temple (above the ear top) becomes hair like the other side, below it becomes cheek skin
    from scipy.spatial import cKDTree
    hairT=v&(H[:,:,0]>=92)&(H[:,:,0]<112)&(H[:,:,1]>110)&(H[:,:,2]>110)
    goodS=zone&skinT&~cand&(H[:,:,1]>60)&(H[:,:,2]>140)
    goodH=zone&hairT&~cand
    o32=out.astype(np.float32)
    for good,sel in ((goodS,cand&(y<=1.70)),(goodH,cand&(y>1.70))):
        gi=np.argwhere(good); ci=np.argwhere(sel)
        kd=cKDTree(pos[good]); dd,nn=kd.query(pos[sel],k=32)
        w_=1/(dd+0.01); o32[ci[:,0],ci[:,1]]=(o32[gi[:,0],gi[:,1]][nn]*w_[...,None]).sum(1)/w_.sum(1)[:,None]
    # smooth the new borders in 3D (texel-space staircase otherwise)
    band=cv2.dilate(cand.astype(np.uint8),np.ones((3,3),np.uint8),iterations=4).astype(bool)&zone
    zi=np.argwhere(zone); bi=np.argwhere(band)
    kd=cKDTree(pos[zone]); dd,nn=kd.query(pos[band],k=40,distance_upper_bound=0.012)
    okn=np.isfinite(dd); nn=np.where(okn,nn,0); w_=okn*np.exp(-(np.where(okn,dd,1)/0.006)**2)
    src=o32[zi[:,0],zi[:,1]]
    o32[bi[:,0],bi[:,1]]=(src[nn]*w_[...,None]).sum(1)/np.maximum(w_.sum(1),1e-6)[:,None]
    out=o32.clip(0,255).astype(np.uint8)
from scipy.spatial import cKDTree
H=hsv(out)
# ---------------- B. hands: recolour to the face skin (hue/sat of the face, a little darker)
cv_=out[np.clip((UV[:,1]*r).astype(int),0,r-1),np.clip((UV[:,0]*r).astype(int),0,r-1)]
Hv=cv2.cvtColor(cv_[None],cv2.COLOR_BGR2HSV)[0].astype(int)
handv=(Hv[:,0]<25)&(Hv[:,1]>35)&(Hv[:,2]>90)&(P3[:,1]<1.05)&(P3[:,1]>0.6)&(np.abs(P3[:,0]+0.03)>0.30)
hz=v&(y<1.06)&(y>0.6)&(np.abs(x+0.03)>0.30)
handT=hz&(H[:,:,0]<25)&(H[:,:,1]>30)&(H[:,:,2]>80)
if 'hand' in A:
    facesk=v&(wf>0.8)&(y>1.55)&(y<1.64)&(H[:,:,0]<22)
    fh,fs_,fv=[np.median(H[:,:,i][facesk]) for i in range(3)]
    hh,hs_,hv=[np.median(H[:,:,i][handT]) for i in range(3)]
    print('face HSV',fh,fs_,fv,'hand HSV',hh,hs_,hv)
    Hn=H.copy()
    wH=cv2.GaussianBlur(handT.astype(np.float32),(0,0),1.2)*hz
    Hn[:,:,0]=H[:,:,0]+(fh-hh); Hn[:,:,1]=H[:,:,1]*(fs_/hs_); Hn[:,:,2]=H[:,:,2]*(0.93*fv/hv)
    rec=cv2.cvtColor(np.clip(Hn,0,255).astype(np.uint8),cv2.COLOR_HSV2BGR).astype(np.float32)
    out=(out.astype(np.float32)*(1-wH[...,None])+rec*wH[...,None]).clip(0,255).astype(np.uint8)
# ---------------- B2. (iter4) hands: clean dark specks, paint 3 soft finger separations on the
# back of each hand so it reads as four fingers instead of a mitten
H=hsv(out)
if 'finger' in A:
    o32=out.astype(np.float32)
    for sgn in (-1,1):
        hv_=handv&(np.sign(P3[:,0]+0.03)==sgn)
        kd=cKDTree(P3[hv_]); dd,_=kd.query(pos[v],k=1)
        near=np.zeros(v.shape,bool); near[v]=dd<0.012
        near&=(y<1.0)&(y>0.62)
        sk=near&(H[:,:,0]<25)&(H[:,:,1]>30)&(H[:,:,2]>110)
        hp=P3[hv_]; top=hp[:,1].max(); bot=hp[:,1].min()
        bad=near&~sk&(y<top-0.05)&(H[:,:,2]<120)
        if bad.any():
            gi=np.argwhere(sk); bi=np.argwhere(bad); kd2=cKDTree(pos[sk]); _,nn=kd2.query(pos[bad],k=10)
            o32[bi[:,0],bi[:,1]]=o32[gi[:,0],gi[:,1]][nn].mean(1)
        hp=P3[hv_]; top=hp[:,1].max(); bot=hp[:,1].min()
        knuck=bot+0.55*(top-bot)
        outer=near&(nrm[...,0]*sgn>0.25)&(y<knuck)
        # finger lanes across z, per height band (hand narrows towards the tips)
        lines=np.zeros(v.shape,np.float32)
        yb=np.round((y-bot)/0.01).astype(int)
        for b_ in np.unique(yb[outer]):
            m=outer&(yb==b_)
            z0,z1=np.percentile(z[m],[4,96])
            for i in (1,2,3):
                zc=z0+(z1-z0)*i/4
                lines[m]=np.maximum(lines[m],np.exp(-((z[m]-zc)/0.0055)**2))
        fade=np.clip((knuck-y)/0.02,0,1)*np.clip((y-bot)/0.012,0,1)
        lf=cv2.GaussianBlur((lines*fade*outer).astype(np.float32),(0,0),1.0)
        k_=1-0.22*lf
        o32*= np.where(near[...,None],k_[...,None],1)
        print('finger lanes side',sgn,'texels',int((lines*fade>0.3).sum()),'bad',int(bad.sum()))
    out=o32.clip(0,255).astype(np.uint8)
# ---------------- C. turtleneck back/sides: remove the painted hood outline (thin dark arcs,
# dots) but keep the broad shading and the knit grain
H=hsv(out)
if 'hood' in A:
    hairish=(H[:,:,0]>=88)&(H[:,:,0]<125)&(H[:,:,1]>110)&(y>1.45)
    skinish=(H[:,:,0]<25)&(H[:,:,1]>30)&(H[:,:,2]>110)
    swe=v&(y>1.08)&(y<1.62)&(z<0.06)&~hairish&~skinish&~((H[:,:,0]<35)&(H[:,:,1]>120))
    reg=swe&(y>1.12)&(np.abs(x+0.02)<0.46)&~((z>-0.02)&(np.abs(x+0.02)<0.16))
    si=np.argwhere(swe); ri=np.argwhere(reg)
    kd=cKDTree(pos[swe]); dd,nn=kd.query(pos[reg],k=48,distance_upper_bound=0.04)
    okn=np.isfinite(dd); nn=np.where(okn,nn,0)
    src=out[si[:,0],si[:,1]].astype(np.float32)
    vals=np.where(okn[...,None],src[nn],np.nan)
    med=np.nanmedian(vals,1)
    o32=out.astype(np.float32)
    lowf=o32.copy(); lowf[ri[:,0],ri[:,1]]=med
    grain=o32-cv2.GaussianBlur(o32,(0,0),1.5)
    wr=reg*sm(1.12,1.2,y)
    # dark specks anywhere on the collar band -> fully replaced
    o32=np.where(wr[...,None]>0,lowf+grain*0.5,o32)
    out=o32.clip(0,255).astype(np.uint8)
    # collar/hair border: dark dots
    H=hsv(out)
    dk=((v&(y>1.40)&(y<1.60)&(z<0.0)&(H[:,:,2]<62))|(v&(y>1.44)&(y<1.56)&(z<-0.08)&(np.abs(x)<0.14)&(H[:,:,2]<80))).astype(np.uint8)
    nl,lab,st,_=cv2.connectedComponentsWithStats(dk,connectivity=8)
    small=np.zeros(nl,bool); small[1:]=st[1:,cv2.CC_STAT_AREA]<200
    dots=small[lab]&(dk>0)
    dots=cv2.dilate(dots.astype(np.uint8),np.ones((3,3),np.uint8)).astype(bool)&v
    print('collar dots',dots.sum())
    if dots.any():
        gd=v&(y>1.38)&(y<1.64)&(z<0.02)&~dots&(H[:,:,2]>70)
        gi=np.argwhere(gd); ci=np.argwhere(dots); kd=cKDTree(pos[gd]); dd,nn=kd.query(pos[dots],k=12)
        o32=out.astype(np.float32); o32[ci[:,0],ci[:,1]]=o32[gi[:,0],gi[:,1]][nn].mean(1); out=o32.astype(np.uint8)
# ---------------- D. back of the hair: strand light/dark and a soft highlight band
H=hsv(out)
if 'hair' in A:
    hairT=v&(H[:,:,0]>=88)&(H[:,:,0]<116)&(H[:,:,1]>90)&(y>1.5)
    back=sm(0.05,-0.12,z)*hairT
    phi=np.arctan2(x-XC,-(z+0.02))           # angle around the head, 0 = straight back
    rng=np.random.default_rng(3)
    ks=[(23,0.55),(37,0.35),(61,0.22)]
    pat=np.zeros_like(x)
    for k_,amp in ks:
        ph=rng.uniform(0,6.28); wob=0.6*np.sin(y*9+rng.uniform(0,6.28))
        pat+=amp*np.sin(phi*k_+ph+wob)
    pat/=sum(a_ for _,a_ in ks)
    # strands darker in the grooves near the nape, lighter on the crown
    tone=1+0.16*pat*sm(1.55,1.75,y)
    ring=np.exp(-((y-2.02)/0.05)**2)*(0.6+0.4*np.clip(pat+0.3,0,1))
    lift=1.10+0.05*sm(1.7,2.1,y)
    Hn=H.copy(); Hn[:,:,2]=H[:,:,2]*(1+(tone*lift-1)*back)+70*ring*back*0.6
    Hn[:,:,1]=H[:,:,1]*(1-0.18*ring*back)
    out=cv2.cvtColor(np.clip(Hn,0,255).astype(np.uint8),cv2.COLOR_HSV2BGR)
# ---------------- geometry: smaller shoes and hands
P=P3.copy()
if 'shoe' in A:
    ws=1-sm(0.15,0.24,P[:,1])
    for sgn in (-1,1):
        m=(np.sign(P[:,0]+0.03)==sgn)&(P[:,1]<0.26)
        sole=m&(P[:,1]<0.06)
        cx_=0.5*(P[sole,0].min()+P[sole,0].max()); cz_=-0.04
        S=0.86
        P[m,0]=cx_+(P[m,0]-cx_)*(1-(1-S)*ws[m]); P[m,2]=cz_+(P[m,2]-cz_)*(1-(1-S)*ws[m])
        P[m,1]=P[m,1]*(1-(1-0.92)*ws[m])
if 'hand' in A:
    for sgn in (-1,1):
        hv_=handv&(np.sign(P3[:,0]+0.03)==sgn)
        top=P3[hv_,1].max(); wr_=P3[hv_&(P3[:,1]>top-0.03)].mean(0)
        kd=cKDTree(P3[hv_]); dd,_=kd.query(P3,k=1)
        wv=(1-sm(0.006,0.02,dd))*(np.sign(P3[:,0]+0.03)==sgn)*sm(0.0,0.06,wr_[1]-P3[:,1])
        S=0.85
        P+= (wr_+(P3-wr_)*S - P3)*wv[:,None]
        print('hand',sgn,'wrist',wr_.round(3),'verts',(wv>0.5).sum())
cv2.imwrite('../work/atlas_final4.png',out)
np.savez('../work/geom4.npz',P=P,UV=UV,F=F,olw=olw)
np.savez('../work/tpos4.npz',pos=pos)
N,_=vnormals(P,F)
save('../work/hero3c.glb',P,UV,F,out,N=N)
