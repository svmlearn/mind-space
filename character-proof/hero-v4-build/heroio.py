import numpy as np, pygltflib, cv2, struct
DOUBLE=True
def load(path):
    g=pygltflib.GLTF2().load(path); blob=g.binary_blob(); p=g.meshes[0].primitives[0]
    def acc(i,dt,n):
        a=g.accessors[i]; bv=g.bufferViews[a.bufferView]; off=(bv.byteOffset or 0)+(a.byteOffset or 0)
        return np.frombuffer(blob,dtype=dt,count=a.count*n,offset=off).reshape(a.count,n).copy()
    P=acc(p.attributes.POSITION,np.float32,3); UV=acc(p.attributes.TEXCOORD_0,np.float32,2)
    F=acc(p.indices,np.uint32,1).reshape(-1,3)
    bv=g.bufferViews[g.images[0].bufferView]
    img=cv2.imdecode(np.frombuffer(blob[bv.byteOffset:bv.byteOffset+bv.byteLength],np.uint8),cv2.IMREAD_COLOR)
    return P,UV,F,img
def vnormals(P,F):
    fn=np.cross(P[F[:,1]]-P[F[:,0]],P[F[:,2]]-P[F[:,0]]); N=np.zeros_like(P)
    for k in range(3): np.add.at(N,F[:,k],fn)
    return N/np.maximum(np.linalg.norm(N,axis=1,keepdims=True),1e-9), fn/np.maximum(np.linalg.norm(fn,axis=1,keepdims=True),1e-9)
def texel_map(P,UV,F,res):
    """per-texel 3D position + face id by rasterizing triangles in UV space (v flipped: glTF uv origin top-left)."""
    pos=np.zeros((res,res,3),np.float32); fid=-np.ones((res,res),np.int32)
    T=UV[F]*res  # (f,3,2) x=u*res, y=v*res
    for f in range(len(F)):
        t=T[f]; x0,y0=np.floor(t.min(0)).astype(int); x1,y1=np.ceil(t.max(0)).astype(int)
        x0=max(x0,0);y0=max(y0,0);x1=min(x1,res-1);y1=min(y1,res-1)
        if x1<x0 or y1<y0: continue
        xs,ys=np.meshgrid(np.arange(x0,x1+1)+.5,np.arange(y0,y1+1)+.5)
        a,b,c=t; d=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(d)<1e-12: continue
        l1=((b[1]-c[1])*(xs-c[0])+(c[0]-b[0])*(ys-c[1]))/d; l2=((c[1]-a[1])*(xs-c[0])+(a[0]-c[0])*(ys-c[1]))/d; l3=1-l1-l2
        e=-0.6/ max(np.abs(d)**.5,1)
        m=(l1>=e)&(l2>=e)&(l3>=e)
        if not m.any(): continue
        yy=(ys[m]-.5).astype(int); xx=(xs[m]-.5).astype(int)
        q=P[F[f]]; pos[yy,xx]=l1[m,None]*q[0]+l2[m,None]*q[1]+l3[m,None]*q[2]; fid[yy,xx]=f
    return pos,fid
def save(path,P,UV,F,img,N=None,skin=None,name='MeadowCharacter',jpeg=None,emis=None,extra_attr=None):
    """skin: dict(joints=[(name,head_xyz)], J=(n,4) uint8, W=(n,4) float)"""
    g=pygltflib.GLTF2(); blob=bytearray(); g.asset=pygltflib.Asset(version='2.0',generator='mind-space build_hero.py')
    def add(arr,target=None,typ=None,comp=None,minmax=False):
        nonlocal blob
        b=arr.tobytes(); pad=(-len(blob))%4; blob+=b'\0'*pad; off=len(blob); blob+=b
        g.bufferViews.append(pygltflib.BufferView(buffer=0,byteOffset=off,byteLength=len(b),target=target))
        if typ is None: return len(g.bufferViews)-1
        a=pygltflib.Accessor(bufferView=len(g.bufferViews)-1,componentType=comp,count=len(arr),type=typ)
        if minmax: a.min=arr.min(0).tolist(); a.max=arr.max(0).tolist()
        g.accessors.append(a); return len(g.accessors)-1
    attrs=pygltflib.Attributes(POSITION=add(P.astype(np.float32),34962,'VEC3',5126,True),TEXCOORD_0=add(UV.astype(np.float32),34962,'VEC2',5126))
    if N is not None: attrs.NORMAL=add(N.astype(np.float32),34962,'VEC3',5126)
    if skin:
        attrs.JOINTS_0=add(skin['J'].astype(np.uint8),34962,'VEC4',5121); attrs.WEIGHTS_0=add(skin['W'].astype(np.float32),34962,'VEC4',5126)
    if extra_attr:
        for k_,v_ in extra_attr.items(): setattr(attrs,k_,add(v_.astype(np.float32).reshape(-1),34962,'SCALAR',5126))
    idx=add(F.astype(np.uint32).reshape(-1),34963,'SCALAR',5125)
    if jpeg: ok,png=cv2.imencode('.jpg',img,[cv2.IMWRITE_JPEG_QUALITY,jpeg]); mt='image/jpeg'
    else: ok,png=cv2.imencode('.png',img); mt='image/png'
    iv=add(np.frombuffer(png.tobytes(),np.uint8))
    g.images=[pygltflib.Image(bufferView=iv,mimeType=mt)]; g.samplers=[pygltflib.Sampler(magFilter=9729,minFilter=9987,wrapS=33071,wrapT=33071)]
    g.textures=[pygltflib.Texture(source=0,sampler=0)]
    mat=pygltflib.Material(name='hero',pbrMetallicRoughness=pygltflib.PbrMetallicRoughness(baseColorTexture=pygltflib.TextureInfo(index=0),metallicFactor=0.0,roughnessFactor=0.9),doubleSided=DOUBLE)
    if emis is not None:
        # self-light map: lets the face/skin glow a little more than the clothes in the dim scene
        ok,eb=cv2.imencode('.jpg',emis,[cv2.IMWRITE_JPEG_QUALITY,88])
        g.images.append(pygltflib.Image(bufferView=add(np.frombuffer(eb.tobytes(),np.uint8)),mimeType='image/jpeg'))
        g.textures.append(pygltflib.Texture(source=1,sampler=0))
        mat.emissiveTexture=pygltflib.TextureInfo(index=1); mat.emissiveFactor=[1.0,1.0,1.0]
    g.materials=[mat]
    g.meshes=[pygltflib.Mesh(name=name,primitives=[pygltflib.Primitive(attributes=attrs,indices=idx,material=0)])]
    if skin:
        nodes=[]; jl=skin['joints']
        root=pygltflib.Node(name='root',children=list(range(1,len(jl)+1)))
        g.nodes.append(root)
        tails=skin.get('tails',{})
        for n,h in jl:
            nd=pygltflib.Node(name=n,translation=[float(v) for v in h])
            if n in tails: nd.extras={'tail':[round(float(v),4) for v in tails[n]]}
            g.nodes.append(nd)
        ibm=np.zeros((len(jl)+1,16),np.float32)
        ibm[0]=np.eye(4).reshape(-1)
        for i,(n,h) in enumerate(jl):
            m=np.eye(4); m[:3,3]=-np.array(h); ibm[i+1]=m.T.reshape(-1)  # column-major
        ia=add(ibm,None,'MAT4',5126)
        g.skins=[pygltflib.Skin(joints=list(range(0,len(jl)+1)),inverseBindMatrices=ia)]
        g.nodes.append(pygltflib.Node(name=name,mesh=0,skin=0))
        g.nodes.append(pygltflib.Node(name='GroundedHero',children=[len(g.nodes)-1,0]))
        if 'gait' in skin: g.nodes[-1].extras={k_:skin[k_] for k_ in ('gait','eyes') if k_ in skin}
        g.scenes=[pygltflib.Scene(nodes=[len(g.nodes)-1])]
    else:
        g.nodes=[pygltflib.Node(name=name,mesh=0)]; g.nodes.append(pygltflib.Node(name='GroundedHero',children=[0])); g.scenes=[pygltflib.Scene(nodes=[1])]
    g.scene=0; g.buffers=[pygltflib.Buffer(byteLength=len(blob))]; g.set_binary_blob(bytes(blob)); g.save(path)
