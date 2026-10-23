import numpy as np, cv2, json
from heroio import *
d=np.load('../work/geom2.npz'); P=d['P'].copy(); UV=d['UV']; F=d['F']
import sys
HT=float(sys.argv[1]) if len(sys.argv)>1 else 0.3
P[:,0]+=0.055; P[:,2]+=0.04              # centre hips/feet on the origin; origin = floor between the feet
P[:,1]-=P[:,1].min()
img=cv2.imread('../work/atlas_final2.png')
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
rest={'body':([0,0.80,0],[0,1.50,0]),'head':([0,1.50,0],[0,2.30,0])}
for s,k in (('L',-1),('R',1)):
    rest['thigh'+s]=([k*HIPX,0.82,0],[k*KNEE[0],KNEE[1],KNEE[2]])
    rest['shin'+s]=([k*KNEE[0],KNEE[1],KNEE[2]],[k*ANK[0],ANK[1],ANK[2]])
    rest['foot'+s]=([k*ANK[0],ANK[1],ANK[2]],[k*ANK[0],ANK[1],0.30])
    rest['arm'+s]=([k*SH[0],SH[1],SH[2]],[k*HAND[0],HAND[1],HAND[2]])
order=['body','head','thighL','shinL','footL','armL','thighR','shinR','footR','armR']
J={n:i+1 for i,n in enumerate(order)}
n=len(P); Wd=np.zeros((n,11),np.float32)
# ---- arms: distance to the sleeve axis vs. the inner sleeve line
S=np.array(SH[:2]); Hh=np.array(HAND[:2]); dvec=Hh-S; L2=(dvec**2).sum()
t=((np.c_[ax,y]-S)@dvec)/L2                       # 0 at shoulder, 1 at wrist/hand
axis_x=SH[0]+np.clip(t,0,1.2)*dvec[0]
inner=axis_x-0.085
armf=sm(-0.012,0.012,ax-inner)*(1-sm(1.34,1.40,y))*(y>0.62)
armf*=sm(-0.02,0.12,t)*0.75+0.25*(t>0.12)          # blend into the torso near the shoulder
armf=np.clip(armf,0,1)
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
    Wd[:,J['arm'+s]]+=armf*(1 if s=='R' else 0)*(x>0) + armf*(1 if s=='L' else 0)*(x<=0)
Wd[:,J['head']]+=headf
Wd[:,J['body']]+=np.clip(1-Wd.sum(1),0,1)
# top 4
idx=np.argsort(-Wd,1)[:,:4]; W=np.take_along_axis(Wd,idx,1); W/=W.sum(1,keepdims=True)
J4=idx.astype(np.uint8)
dom=idx[:,0]
for nm,i in J.items(): print(nm,(dom==i).sum())
K=2.0/2.3   # same overall height as the v3 walker (~2 units) so screen size and gait speed stay calibrated
P=P*K
rest={k_:([c*K for c in a_],[c*K for c in b_]) for k_,(a_,b_) in rest.items()}
gait=dict(hip=0.80,hipX=HIPX,ankle=0.14,seg=0.35,side=0.20,neck=0.70,headLen=0.80,headScale=1.0,
          shoulder=[SH[0],SH[1]-0.80],arm=[HAND[0]-SH[0]-0.03,HAND[1]-SH[1]],toe=0.33,height=2.3,headTilt=HT)
gait={k_:([round(c*K,4) for c in v_] if isinstance(v_,list) else (v_ if k_ in ('headScale','headTilt') else round(v_*K,4))) for k_,v_ in gait.items()}
N,_=vnormals(P,F)
np.savez('../work/hero_final.npz',P=P,UV=UV,F=F,J=J4,W=W,dom=dom)
save('../work/hero-v4.glb',P,UV,F,img,N=N,skin=dict(joints=[(nm,rest[nm][0]) for nm in order],J=J4,W=W,
     tails={nm:rest[nm][1] for nm in order},gait=gait),jpeg=90)
print(json.dumps(gait))
