import numpy as np, cv2, json
from heroio import *
d=np.load('../work/geom4.npz'); P=d['P'].copy(); UV=d['UV']; F=d['F']
import sys
HT=float(sys.argv[1]) if len(sys.argv)>1 else 0.12
HS=float(sys.argv[2]) if len(sys.argv)>2 else 1.08   # head scale (bigger face, closer to the turnaround)
UP=float(sys.argv[3]) if len(sys.argv)>3 else 1.12   # overall size vs. v3 on screen
P[:,0]+=0.055; P[:,2]+=0.04              # centre hips/feet on the origin; origin = floor between the feet
P[:,1]-=P[:,1].min()
img=cv2.imread('../work/atlas_final4.png')
# sweater: the TRELLIS bake drifted to a darker leaf green; pull it back to the painted teal
tm=np.load('../work/tmap.npz'); tpos,tv=tm['pos'],tm['fid']>=0
Hs=cv2.cvtColor(img,cv2.COLOR_BGR2HSV).astype(np.float32)
sel=(Hs[:,:,0]>=62)&(Hs[:,:,0]<=91)&(Hs[:,:,1]>70)&(~tv|(tpos[:,:,1]<1.52))
wgt=np.clip((91-Hs[:,:,0])/6,0,1)*sel     # fade out towards the hair hue
Hs[:,:,0]+=9*wgt; Hs[:,:,2]=np.minimum(255,Hs[:,:,2]*(1+0.18*wgt))
img=cv2.cvtColor(np.clip(Hs,0,255).astype(np.uint8),cv2.COLOR_HSV2BGR)
cv2.imwrite('../work/atlas_v4.png',img)
def sm(a,b,v): t=np.clip((v-a)/(b-a),0,1); return t*t*(3-2*t)
x,y,z=P[:,0],P[:,1],P[:,2]; ax=np.abs(x); sgn=np.where(x<0,0,1)  # 0=L(-x) 1=R
# ---- rest skeleton (glTF units, +Z forward, L = -x)
HIPX,KNEE,ANK=0.14,(0.19,0.47,0.0),(0.245,0.14,-0.035)
SH=(0.27,1.33,0.0); HAND=(0.515,0.76,0.07)
TE=float(sys.argv[6]) if len(sys.argv)>6 else 0.47         # elbow position along shoulder->hand
ELB=tuple(SH[i]+TE*(HAND[i]-SH[i]) for i in range(3))
rest={'body':([0,0.80,0],[0,1.50,0]),'head':([0,1.50,0],[0,2.30,0])}
for s,k in (('L',-1),('R',1)):
    rest['thigh'+s]=([k*HIPX,0.82,0],[k*KNEE[0],KNEE[1],KNEE[2]])
    rest['shin'+s]=([k*KNEE[0],KNEE[1],KNEE[2]],[k*ANK[0],ANK[1],ANK[2]])
    rest['foot'+s]=([k*ANK[0],ANK[1],ANK[2]],[k*ANK[0],ANK[1],0.30])
    # iter4: two-bone arm (upper arm + forearm, elbow at TE along shoulder->hand)
    rest['arm'+s]=([k*SH[0],SH[1],SH[2]],[k*ELB[0],ELB[1],ELB[2]])
    rest['forearm'+s]=([k*ELB[0],ELB[1],ELB[2]],[k*HAND[0],HAND[1],HAND[2]])
order=['body','head','thighL','shinL','footL','armL','thighR','shinR','footR','armR','forearmL','forearmR']
J={n:i+1 for i,n in enumerate(order)}
n=len(P); Wd=np.zeros((n,len(order)+1),np.float32)
# ---- arms: distance to the sleeve axis vs. the inner sleeve line
S=np.array(SH[:2]); Hh=np.array(HAND[:2]); dvec=Hh-S; L2=(dvec**2).sum()
t=((np.c_[ax,y]-S)@dvec)/L2                       # 0 at shoulder, 1 at wrist/hand
axis_x=SH[0]+np.clip(t,0,1.2)*dvec[0]
inner=axis_x-0.085
armf=sm(-0.012,0.012,ax-inner)*(1-sm(1.34,1.40,y))*(y>0.62)
armf*=sm(-0.02,0.12,t)*0.75+0.25*(t>0.12)          # blend into the torso near the shoulder
armf=np.clip(armf,0,1)
# iter4: the sweater hem flares out right where the relaxed arm hangs -> pull the hem sides in
# (torso only, the sleeves are separate further out) so the arms can hang close to the body
xc_=-0.0; hx=np.abs(P[:,0]-xc_); ys=P[:,1]
side_=(hx>0.25)&(ys>0.80)&(ys<1.06)&(armf<0.02)
hemw=np.clip(np.minimum((ys-0.80)/0.05,(1.06-ys)/0.08),0,1)**1
hemw=hemw*hemw*(3-2*hemw)
newx=0.25+(hx-0.25)*0.45
P[:,0]=np.where(side_,np.sign(P[:,0]-xc_)*(hx+(newx-hx)*hemw)+xc_,P[:,0])
# ---- head: everything above the collar (all hair) goes to the head, nothing else
headf=sm(1.44,1.54,y)*(1-armf)
# ---- legs
legf=(1-sm(0.78,0.90,y))*(1-armf)*(1-headf)
right=sm(-0.03,0.03,x); right=np.where(y<0.6,(x>0).astype(np.float32),right)
shinf=1-sm(0.41,0.53,y); footf=1-sm(0.15,0.22,y)
for s,side in (('L',1-right),('R',right)):
    lf=legf*side
    Wd[:,J['foot'+s]]+=lf*footf
    Wd[:,J['shin'+s]]+=lf*(1-footf)*shinf
    Wd[:,J['thigh'+s]]+=lf*(1-footf)*(1-shinf)
    am=armf*((x>0) if s=='R' else (x<=0))
    fo=sm(TE-0.06,TE+0.06,t)                       # smooth elbow: blend over ~0.07 units of sleeve
    Wd[:,J['arm'+s]]+=am*(1-fo)
    Wd[:,J['forearm'+s]]+=am*fo
Wd[:,J['head']]+=headf
Wd[:,J['body']]+=np.clip(1-Wd.sum(1),0,1)
# top 4
idx=np.argsort(-Wd,1)[:,:4]; W=np.take_along_axis(Wd,idx,1); W/=W.sum(1,keepdims=True)
J4=idx.astype(np.uint8)
dom=idx[:,0]
for nm,i in J.items(): print(nm,(dom==i).sum())
K=2.0/2.3*UP   # v3 is ~2 units tall; v4 reads smaller (big hair, thin body), so it is scaled up a bit
P=P*K
rest={k_:([c*K for c in a_],[c*K for c in b_]) for k_,(a_,b_) in rest.items()}
import math
AU=float(sys.argv[7]) if len(sys.argv)>7 else 9.0; AF=float(sys.argv[8]) if len(sys.argv)>8 else 3.0  # abduction (deg)
Lu=math.dist(SH[:2],ELB[:2]); Lf=math.dist(ELB[:2],HAND[:2])
UA=(Lu*math.sin(math.radians(AU)),-Lu*math.cos(math.radians(AU))); FA=(Lf*math.sin(math.radians(AF)),-Lf*math.cos(math.radians(AF)))
gait=dict(hip=0.80,hipX=HIPX,ankle=0.14,seg=0.35,side=0.20,neck=0.70,headLen=0.80,headScale=HS,
          shoulder=[SH[0],SH[1]-0.80],arm=[HAND[0]-SH[0]-0.03,HAND[1]-SH[1]],toe=0.33,height=2.3,headTilt=HT,
          armSwingGain=1.15,armSwingMax=0.24,   # iter3: livelier anti-phase arm swing
          upperArm=list(UA),foreArm=list(FA),elbowRest=0.14,elbowSwing=0.40)  # iter4: hanging two-bone arm
gait={k_:([round(c*K,4) for c in v_] if isinstance(v_,list) else (v_ if k_ in ('headScale','headTilt','armSwingGain','elbowRest','elbowSwing') else round(v_*K,4))) for k_,v_ in gait.items()}
# ---- emissive (self-light) map: albedo x warm tint x strength; face/ears/hands get more
wf=np.load('../work/facew3.npy').astype(np.float32)
Hh=cv2.cvtColor(img,cv2.COLOR_BGR2HSV).astype(np.float32)
skinT=((Hh[:,:,0]<25)&(Hh[:,:,1]>35)&(Hh[:,:,2]>90)&tv).astype(np.float32)
facem=np.clip(np.maximum(cv2.GaussianBlur(wf,(0,0),6)*1.4,cv2.GaussianBlur(skinT,(0,0),3)*0.7),0,1)
EB=float(sys.argv[4]) if len(sys.argv)>4 else 0.20; EF=float(sys.argv[5]) if len(sys.argv)>5 else 0.50
strength=EB+(EF-EB)*facem
# iter3: the back of the hair sits in the key light's shadow -> a little more self-light there
hairB=((Hh[:,:,0]>=88)&(Hh[:,:,0]<125)&(Hh[:,:,1]>90)&tv&(tpos[:,:,1]>1.5)).astype(np.float32)
hairB*=np.clip((0.02-tpos[:,:,2])/0.20,0,1)
strength=strength+0.10*cv2.GaussianBlur(hairB,(0,0),3)
tint=np.array([0.76,0.88,1.0],np.float32)   # BGR: warm
emis=(img.astype(np.float32)*tint*strength[...,None]).clip(0,255).astype(np.uint8)
emis=cv2.resize(emis,(1024,1024),interpolation=cv2.INTER_AREA)
# ---- eyes for the shader blink (painting eye boxes -> model space, incl. the vertical eye stretch)
def p2m(px_,py_): return (px_-513)/372-0.054, 1.695+((930-py_)/372-1.695)*1.18
eyes={}
for nm,(ex,ey) in (('L',(460,293)),('R',(575,293))):
    mx_,my_=p2m(ex,ey); eyes[nm]=[round((mx_+0.055)*K,4),round((my_-0.028)*K,4)]
eyes['r']=[round(30/372*1.25*K,4),round(28/372*1.18*1.65*K,4)]
eyes['zmin']=round((0.17+0.04)*K,4)
fm=(wf>0.8)&tv&(tpos[:,:,1]>1.55)&(tpos[:,:,1]<1.64)
sk=np.median(img[fm&(Hh[:,:,0]<22)],0)[::-1]/255.0
eyes['skin']=[round(0.94*float(((c+0.055)/1.055)**2.4),4) for c in sk]
print('eyes',eyes)
N,_=vnormals(P,F)
# iter4: weld normals across UV seams (TRELLIS charts split ~54% of the vertices) -> no hard
# shading lines / outline cracks along the seams
_,winv=np.unique(np.round(P*2e4).astype(np.int64),axis=0,return_inverse=True); winv=winv.ravel()
NA=np.zeros((winv.max()+1,3)); np.add.at(NA,winv,N); NA/=np.maximum(np.linalg.norm(NA,axis=1,keepdims=True),1e-9)
N=NA[winv].astype(np.float32)
np.savez('../work/hero_final.npz',P=P,UV=UV,F=F,J=J4,W=W,dom=dom)
save('../work/hero-v4.glb',P,UV,F,img,N=N,skin=dict(joints=[(nm,rest[nm][0]) for nm in order],J=J4,W=W,
     tails={nm:rest[nm][1] for nm in order},gait=gait,eyes=eyes),jpeg=90,emis=emis,extra_attr={'_OUTLINE':d['olw']})
print(json.dumps(gait))
