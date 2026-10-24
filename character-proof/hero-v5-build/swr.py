# tiny numpy software rasterizer: orthographic views of the textured mesh (z-buffer) for landmarks/QA
import numpy as np, cv2
def rot_y(P,deg):
    a=np.radians(deg); c,s=np.cos(a),np.sin(a)
    return np.c_[c*P[:,0]+s*P[:,2],P[:,1],-s*P[:,0]+c*P[:,2]]
def render(P,UV,F,img,cx,cy,scale,res,yaw=0,bg=(230,226,220)):
    """ortho view from +Z (front) after yawing the model by `yaw` deg; pixel = (x-cx)*scale+res/2.
    returns color image, depth (z, -inf empty), face id, and per-pixel barycentric uv"""
    Q=rot_y(P,yaw) if yaw else P
    X=(Q[:,0]-cx)*scale+res/2; Y=res/2-(Q[:,1]-cy)*scale; Z=Q[:,2]
    zb=np.full((res,res),-np.inf,np.float32); fb=-np.ones((res,res),np.int32); uvb=np.zeros((res,res,2),np.float32)
    T=np.stack([X[F],Y[F]],-1); Zt=Z[F]
    keep=(T[:,:,0].max(1)>=0)&(T[:,:,0].min(1)<res)&(T[:,:,1].max(1)>=0)&(T[:,:,1].min(1)<res)
    for f in np.nonzero(keep)[0]:
        t=T[f]; x0,y0=np.floor(t.min(0)).astype(int); x1,y1=np.ceil(t.max(0)).astype(int)
        x0=max(x0,0);y0=max(y0,0);x1=min(x1,res-1);y1=min(y1,res-1)
        if x1<x0 or y1<y0: continue
        xs,ys=np.meshgrid(np.arange(x0,x1+1)+.5,np.arange(y0,y1+1)+.5)
        a,b,c=t; d=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(d)<1e-12: continue
        l1=((b[1]-c[1])*(xs-c[0])+(c[0]-b[0])*(ys-c[1]))/d; l2=((c[1]-a[1])*(xs-c[0])+(a[0]-c[0])*(ys-c[1]))/d; l3=1-l1-l2
        m=(l1>=0)&(l2>=0)&(l3>=0)
        if not m.any(): continue
        z=l1*Zt[f,0]+l2*Zt[f,1]+l3*Zt[f,2]
        yy=(ys[m]-.5).astype(int); xx=(xs[m]-.5).astype(int); zz=z[m]
        upd=zz>zb[yy,xx]
        if not upd.any(): continue
        yy,xx,zz=yy[upd],xx[upd],zz[upd]
        zb[yy,xx]=zz; fb[yy,xx]=f
        u=UV[F[f]]; L=np.stack([l1[m][upd],l2[m][upd],l3[m][upd]],-1)
        uvb[yy,xx]=L@u
    h,w=img.shape[:2]
    col=np.full((res,res,3),bg,np.uint8); v=fb>=0
    px=np.clip((uvb[...,0]*w).astype(int),0,w-1); py=np.clip((uvb[...,1]*h).astype(int),0,h-1)
    col[v]=img[py[v],px[v]]
    return col,zb,fb,uvb
