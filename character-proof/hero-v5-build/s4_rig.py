# s4_rig.py [AU AF HT HS] : skin weights + skeleton for grounded-rig.js (same bone names/order as
# hero-v4 iter4: body, head, thighL/R, shinL/R, footL/R, armL/R (upper arm) + forearmL/R), glTF
# extras (bone tails, gait, eyes), emissive map, welded normals -> ../hero-v5.glb
# in: work/shape.npz atlas_face.png facew.npy face.json tmap_shape.npz
import os
WK=os.environ.get('WORK','../work'); TEX=os.environ.get('TEX','base2k.png')   # high-res build: WORK=../work_hr TEX=basecolor_4k.png
import numpy as np, cv2, json, sys, math
from heroio import save, vnormals
AU=float(sys.argv[1]) if len(sys.argv)>1 else 20.0   # hanging upper-arm abduction (deg); rest pose ~25
AF=float(sys.argv[2]) if len(sys.argv)>2 else 9.0    # forearm abduction (deg); rest ~12
HT=float(sys.argv[3]) if len(sys.argv)>3 else 0.15   # head tilt (chin up) for the high game camera
HS=float(sys.argv[4]) if len(sys.argv)>4 else 1.0
OUT=sys.argv[5] if len(sys.argv)>5 else '../hero-v5.glb'
d=np.load(WK+'/shape.npz'); P=d['P'].astype(np.float64); UV=d['UV']; F=d['F']; weld=d['weld']; hair=d['hair']
img=cv2.imread(WK+'/atlas_face.png'); R=img.shape[0]; SC=R/2048   # texel-space blur radii scale with the atlas
JPQ=int(os.environ.get('JPEG','88')); ER=int(os.environ.get('EMIS',str(R//2)))
def sm(a,b,v): t=np.clip((v-a)/(b-a),0,1); return t*t*(3-2*t)
x,y,z=P[:,0],P[:,1],P[:,2]; ax=np.abs(x)
# ---- soften the front-face relief (Hunyuan sculpted a nose ridge, mouth groove and eye pits; with the
# painted face on top they read as stiff and the ink hull pokes through them). Taubin smoothing on
# welded vertices, weighted by the painted-face weight, keeps the volume and the silhouette.
wfT=np.load(WK+'/facew.npy').astype(np.float32); RT=wfT.shape[0]
fv=wfT[np.clip((UV[:,1]*RT).astype(int),0,RT-1),np.clip((UV[:,0]*RT).astype(int),0,RT-1)]
fv=fv*sm(0.22,0.14,ax)*sm(1.41,1.45,y)*sm(1.88,1.80,y)*sm(0.10,0.18,z)*(~hair)
_,wi=np.unique(weld,return_inverse=True); wi=wi.ravel(); nW=wi.max()+1
Pw=np.zeros((nW,3)); np.add.at(Pw,wi,P); cw=np.bincount(wi,minlength=nW); Pw/=cw[:,None]
fw=np.zeros(nW); np.maximum.at(fw,wi,fv)
E=np.vstack([wi[F[:,[0,1]]],wi[F[:,[1,2]]],wi[F[:,[2,0]]]]); E=np.vstack([E,E[:,::-1]])
deg=np.bincount(E[:,0],minlength=nW).astype(float)
FS=int(sys.argv[6]) if len(sys.argv)>6 else 0
for it in range(FS):
    for lam in (0.55,-0.58):
        L=np.zeros((nW,3)); np.add.at(L,E[:,0],Pw[E[:,1]]); L=L/np.maximum(deg,1)[:,None]-Pw
        Pw+=lam*fw[:,None]*L
P=np.where((fw[wi]>0)[:,None],Pw[wi],P)
print('face smooth verts',int((fw>0.05).sum()),'max move',float(np.abs(Pw[wi]-d['P']).max()))
x,y,z=P[:,0],P[:,1],P[:,2]; ax=np.abs(x)
col=img[np.clip((UV[:,1]*R).astype(int),0,R-1),np.clip((UV[:,0]*R).astype(int),0,R-1)]
Hv=cv2.cvtColor(col[None],cv2.COLOR_BGR2HSV)[0].astype(int)
sweater=(Hv[:,0]>=78)&(Hv[:,0]<=93)&(Hv[:,2]>100)
# ---- rest skeleton (measured on the mesh: cross-sections + front/side renders; +Z forward, L = -x)
HIP=(0.12,0.76,-0.03); KNEE=(0.165,0.44,-0.05); ANK=(0.215,0.14,-0.075)
SH=(0.25,1.32,-0.03); ELB=(0.40,1.00,-0.03); HAND=(0.46,0.72,0.03)
rest={'body':([0,0.76,0],[0,1.45,0]),'head':([0,1.45,0],[0,2.24,0])}
for s,k in (('L',-1),('R',1)):
    rest['thigh'+s]=([k*HIP[0],HIP[1],HIP[2]],[k*KNEE[0],KNEE[1],KNEE[2]])
    rest['shin'+s]=([k*KNEE[0],KNEE[1],KNEE[2]],[k*ANK[0],ANK[1],ANK[2]])
    rest['foot'+s]=([k*ANK[0],ANK[1],ANK[2]],[k*ANK[0],ANK[1],0.22])
    rest['arm'+s]=([k*SH[0],SH[1],SH[2]],[k*ELB[0],ELB[1],ELB[2]])
    rest['forearm'+s]=([k*ELB[0],ELB[1],ELB[2]],[k*HAND[0],HAND[1],HAND[2]])
order=['body','head','thighL','shinL','footL','armL','thighR','shinR','footR','armR','forearmL','forearmR']
J={n:i+1 for i,n in enumerate(order)}
Wd=np.zeros((len(P),len(order)+1))
# ---- arms: the sleeve is a separate tube below y~1.06 (gap at |x|~0.30-0.31), fused with the
# torso above; the boundary then runs up to the shoulder seam
inner=np.where(y<=1.08,0.304,0.304-(y-1.08)*(0.064/0.26))
armf=sm(-0.005,0.005,ax-inner)*(y>0.58)*(1-sm(1.30,1.40,y))
armf*=1-0.45*sm(1.16,1.34,y)                    # share the shoulder with the torso
fo=sm(1.05,0.95,y)                              # elbow blend (the arm hangs almost vertically)
# ---- head: skin + hair above the collar (the turtleneck stays on the body)
headf=sm(1.42,1.49,y)*(1-sweater*(1-sm(1.52,1.58,y)))*(1-armf)
# ---- legs (pants + shoes) below the sweater hem
legf=(1-sm(0.64,0.74,y))*(1-armf)*(1-headf)
right=np.where(y<0.6,(x>0).astype(float),sm(-0.03,0.03,x))
shinf=1-sm(0.40,0.50,y); footf=1-sm(0.13,0.21,y)
for s,side in (('L',1-right),('R',right)):
    lf=legf*side
    Wd[:,J['foot'+s]]+=lf*footf
    Wd[:,J['shin'+s]]+=lf*(1-footf)*shinf
    Wd[:,J['thigh'+s]]+=lf*(1-footf)*(1-shinf)
    am=armf*((x>0) if s=='R' else (x<=0))
    Wd[:,J['arm'+s]]+=am*(1-fo); Wd[:,J['forearm'+s]]+=am*fo
Wd[:,J['head']]+=headf
Wd[:,J['body']]+=np.clip(1-Wd.sum(1),0,1)
# same weights for all UV-split copies of a vertex (no cracks at seams)
_,winv=np.unique(weld,return_inverse=True); winv=winv.ravel()
WA=np.zeros((winv.max()+1,Wd.shape[1])); np.add.at(WA,winv,Wd); cnt=np.bincount(winv); Wd=WA[winv]/cnt[winv,None]
idx=np.argsort(-Wd,1)[:,:4]; W=np.take_along_axis(Wd,idx,1); W/=W.sum(1,keepdims=True)
J4=idx.astype(np.uint8); dom=idx[:,0]
print({nm:int((dom==i).sum()) for nm,i in J.items()})
# ---- gait (character units, final scale; see grounded-rig.js DEFAULTS)
Lu=math.dist(SH[:2],ELB[:2]); Lf=math.dist(ELB[:2],HAND[:2])
UA=[round(Lu*math.sin(math.radians(AU)),4),round(-Lu*math.cos(math.radians(AU)),4)]
FA=[round(Lf*math.sin(math.radians(AF)),4),round(-Lf*math.cos(math.radians(AF)),4)]
gait=dict(hip=0.76,hipX=HIP[0],ankle=ANK[1],seg=0.315,side=0.20,neck=0.69,headLen=0.79,headScale=HS,
          shoulder=[SH[0],round(SH[1]-0.76,4)],arm=[round(HAND[0]-SH[0]-0.03,4),round(HAND[1]-SH[1],4)],
          toe=0.29,height=2.24,headTilt=HT,armSwingGain=1.15,armSwingMax=0.24,
          upperArm=UA,foreArm=FA,elbowRest=0.14,elbowSwing=0.40,
          # iter5 gait shape (grounded-rig.js): readable knees and narrower steps from the front
          narrow=0.32,swingIn=0.02,kneeOut=0.4,toeOut=0.07,flex=0.055,bob=0.03,lift=0.13,sway=0.04,
          pelvisTilt=0.02,pelvisYaw=0.12,twist=0.07,heelOff=0.35,heelStrike=0.2,jitter=0.07)
# ---- emissive (self-light): body 0.20, face/skin 0.50, warm tint (same recipe as hero-v4)
tm=np.load(WK+'/tmap_shape.npz'); tpos,tv=tm['pos'],tm['fid']>=0
wf=np.load(WK+'/facew.npy').astype(np.float32)
Hh=cv2.cvtColor(img,cv2.COLOR_BGR2HSV).astype(np.float32)
skinT=((Hh[...,0]<25)&(Hh[...,1]>35)&(Hh[...,2]>90)&tv).astype(np.float32)
# blur inside each UV chart only: a plain texel-space blur pulls dark neighbouring charts into a skin
# chart's border and draws seam lines across the face (the 500k atlas has ~2400 tightly packed charts)
import scipy.sparse as sp
from scipy.sparse.csgraph import connected_components
_r=np.repeat(np.arange(len(F)),3); _A=sp.csr_matrix((np.ones(len(_r)),(_r,F.ravel().astype(np.int64))),shape=(len(F),len(P)))
_nc,_lab=connected_components(_A@_A.T,directed=False)
chart=np.where(tm['fid']>=0,_lab[np.maximum(tm['fid'],0)],-1)
_ys,_xs=np.nonzero(chart>=0); _cl=chart[_ys,_xs]; _o=np.argsort(_cl,kind='stable'); _cl,_ys,_xs=_cl[_o],_ys[_o],_xs[_o]
_cut=np.flatnonzero(np.diff(_cl))+1; _st=np.r_[0,_cut]; _en=np.r_[_cut,len(_cl)]
def cblur(m,sig):
    out=cv2.GaussianBlur(m,(0,0),sig); pad=int(3*sig)+1
    for s0,e0 in zip(_st,_en):
        c=_cl[s0]; ys,xs=_ys[s0:e0],_xs[s0:e0]
        y0,y1,x0,x1=max(ys.min()-pad,0),min(ys.max()+pad+1,R),max(xs.min()-pad,0),min(xs.max()+pad+1,R)
        mc=(chart[y0:y1,x0:x1]==c).astype(np.float32)
        num=cv2.GaussianBlur(m[y0:y1,x0:x1]*mc,(0,0),sig); den=cv2.GaussianBlur(mc,(0,0),sig)
        out[ys,xs]=num[ys-y0,xs-x0]/np.maximum(den[ys-y0,xs-x0],1e-6)
    return out
facem=np.clip(np.maximum(cblur(wf,6*SC)*1.4,cblur(skinT,3*SC)*0.7),0,1)
strength=0.20+0.30*facem
hairB=((Hh[...,0]>=93)&(Hh[...,0]<115)&tv&(tpos[...,1]>1.5)).astype(np.float32)*np.clip((0.0-tpos[...,2])/0.25,0,1)
strength+=0.10*cblur(hairB,3*SC)
emis=(img.astype(np.float32)*np.array([0.76,0.88,1.0],np.float32)*strength[...,None]).clip(0,255).astype(np.uint8)
emis=cv2.resize(emis,(ER,ER),interpolation=cv2.INTER_AREA)
eyes=json.load(open(WK+'/face.json'))['eyes']
# ---- normals, welded across UV seams
N,_=vnormals(P,F)
NA=np.zeros((winv.max()+1,3)); np.add.at(NA,winv,N); NA/=np.maximum(np.linalg.norm(NA,axis=1,keepdims=True),1e-9); N=NA[winv]
# ---- outline width: thin on the hair lying on the forehead (no ink line across the eyes)
from scipy.spatial import cKDTree
olw=np.ones(len(P),np.float32)
fr=hair&(z>0.12)&(y>1.58)&(y<1.82)&(ax<0.30)
olw[fr]=np.clip(d['dsk'][fr]/0.03,0.25,1)
olw[hair&(z>0.10)&(y<1.86)&(ax<0.26)]*=0.4
olw*=1-np.clip(fv*3,0,1)   # no ink inside the face, the silhouette keeps it
olw[(~hair)&(z>0.10)&(y>1.58)&(ax<0.22)]=0
# the inverted hull pokes through small creases (more of them on the 500k mesh): scale the ink width
# down where the surface is locally concave, measured against a ~1.5 cm neighbourhood average
import scipy.sparse as sp
Ew=np.vstack([wi[F[:,[0,1]]],wi[F[:,[1,2]]],wi[F[:,[2,0]]]]); Ew=np.vstack([Ew,Ew[:,::-1]])
Aw=sp.csr_matrix((np.ones(len(Ew)),(Ew[:,0],Ew[:,1])),shape=(nW,nW)); Aw=sp.diags(1/np.maximum(np.asarray(Aw.sum(1)).ravel(),1))@Aw
Pw2=np.zeros((nW,3)); np.add.at(Pw2,wi,P); Pw2/=np.bincount(wi,minlength=nW)[:,None]
Nw=np.zeros((nW,3)); np.add.at(Nw,wi,N); Nw/=np.maximum(np.linalg.norm(Nw,axis=1,keepdims=True),1e-9)
Q=Pw2.copy(); KR=int(os.environ.get('CONC_K',str(max(3,int(3*np.sqrt(len(F)/55000))))))
for _ in range(KR): Q=Aw@Q
conc=((Q-Pw2)*Nw).sum(1)[wi]          # >0: vertex sits in a dip
olw*=sm(0.0035,0.001,conc).astype(np.float32)
# hull clearance: push each vertex out by its ink width; if that point lands close to some other
# surface (ear against cheek, collar under chin, fringe over the brow) the hull would poke through it
from scipy.spatial import cKDTree
OFF=0.011; kd=cKDTree(Pw2)
for _ in range(2):
    ow=np.zeros(nW); np.maximum.at(ow,wi,olw); q=Pw2+Nw*(OFF*ow)[:,None]
    dq,_i=kd.query(q); clr=np.where(ow>0.05,dq/np.maximum(OFF*ow,1e-9),1.0)
    olw*=np.clip((clr[wi]-0.55)/0.35,0,1).astype(np.float32)
print('outline: hull-clearance attenuated',int((clr<0.9).sum()))
print('outline: concave-attenuated verts',int((conc>0.001).sum()),'K',KR)
np.savez(WK+'/hero_final.npz',P=P,UV=UV,F=F,J=J4,W=W,dom=dom)
save(OUT,P.astype(np.float32),UV,F,img,N=N,skin=dict(joints=[(nm,rest[nm][0]) for nm in order],J=J4,W=W,
     tails={nm:rest[nm][1] for nm in order},gait=gait,eyes=eyes),jpeg=JPQ,emis=emis,extra_attr={'_OUTLINE':olw},name='MeadowCharacter')
import os; print(json.dumps(gait)); print('size MB',os.path.getsize(OUT)/1e6,'tris',len(F),'verts',len(P))
