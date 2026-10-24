# blender -b -P b1_prep.py -- raw.glb work/ [targetTris]   (targetTris >= source: no decimation, full 500k)
# Hunyuan3D 3.1 raw (500k tris, Z-up node rotation, UV-split vertices) -> welded, scaled to 2.24 units,
# feet at origin, decimated (face + hands protected), dumped as numpy (glTF axes: +Y up, +Z forward).
import bpy, bmesh, sys, numpy as np
argv=sys.argv[sys.argv.index('--')+1:]; glb,out=argv[0],argv[1]; TARGET=int(argv[2]) if len(argv)>2 else 50000
HEIGHT=2.24   # same on-screen height as hero-v4 (2.0/2.3*1.12*2.3)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
o=[o for o in bpy.context.scene.objects if o.type=='MESH'][0]
bpy.context.view_layer.objects.active=o; o.select_set(True)
me=o.data
co=np.zeros(len(me.vertices)*3); me.vertices.foreach_get('co',co); co=co.reshape(-1,3)
M=np.array(o.matrix_world); co=co@M[:3,:3].T+M[:3,3]   # bake the node rotation (Z-up raw -> Blender world)
o.matrix_world.identity(); o.parent=None
h=co[:,2].max()-co[:,2].min(); s=HEIGHT/h
# feet: centre between the two shoe soles (lowest 4% of the height)
low=co[co[:,2]<co[:,2].min()+0.04*h]
cx,cy=(low[:,0].min()+low[:,0].max())/2,(low[:,1].min()+low[:,1].max())/2
co=(co-[cx,cy,co[:,2].min()])*s
me.vertices.foreach_set('co',co.ravel()); me.update(); print('SCALED',co.min(0),co.max(0))
bm=bmesh.new(); bm.from_mesh(me)
bmesh.ops.remove_doubles(bm,verts=bm.verts,dist=1e-5*HEIGHT); bm.to_mesh(me); bm.free()
print('welded verts',len(me.vertices)); _c=np.zeros(len(me.vertices)*3); me.vertices.foreach_get('co',_c); print('W',_c.reshape(-1,3).min(0),_c.reshape(-1,3).max(0))
# protect face (front of the head) and hands from decimation
co=np.zeros(len(me.vertices)*3); me.vertices.foreach_get('co',co); co=co.reshape(-1,3)
x,y,z=co[:,0],-co[:,1],co[:,2]       # y: forward (+) in blender is -Y
face=(z>1.30)&(z<1.75)&(y>0.02)&(np.abs(x)<0.28)
hand=(z>0.55)&(z<0.95)&(np.abs(x)>0.30)
w=np.where(face|hand,1.0,0.0)
vg=o.vertex_groups.new(name='keep')
for i in np.nonzero(w)[0]: vg.add([int(i)],1.0,'REPLACE')
me.calc_loop_triangles(); n0=len(me.loop_triangles)
if TARGET<n0:
  m=o.modifiers.new('dec','DECIMATE'); m.decimate_type='COLLAPSE'; m.ratio=TARGET/n0
  VGF=float(argv[3]) if len(argv)>3 else 0.0
  if VGF>0: m.vertex_group='keep'; m.invert_vertex_group=False; m.vertex_group_factor=VGF
  m.use_collapse_triangulate=True
  bpy.ops.object.modifier_apply(modifier='dec')
me=o.data; me.calc_loop_triangles(); print('tris',n0,'->',len(me.loop_triangles))
# dump: split vertices by UV (glTF style)
nl=len(me.loops); lv=np.zeros(nl,np.int64); me.loops.foreach_get('vertex_index',lv)
uv=np.zeros(nl*2); me.uv_layers[0].data.foreach_get('uv',uv); uv=uv.reshape(-1,2)
co=np.zeros(len(me.vertices)*3); me.vertices.foreach_get('co',co); co=co.reshape(-1,3)
tri=np.zeros(len(me.loop_triangles)*3,np.int64); me.loop_triangles.foreach_get('loops',tri); tri=tri.reshape(-1,3)
key=np.c_[lv,np.round(uv*1e6).astype(np.int64)]
uk,inv=np.unique(key,axis=0,return_inverse=True); inv=inv.ravel()
first=np.zeros(len(uk),np.int64); first[inv]=np.arange(nl)
V=co[lv[first]]; P=np.c_[V[:,0],V[:,2],-V[:,1]].astype(np.float32)
UV=uv[first].copy(); UV[:,1]=1-UV[:,1]           # glTF uv origin top-left
F=inv[tri].astype(np.uint32)
weld=lv[first]                                      # geometric vertex id (for normal welding)
np.savez(out+'/dec.npz',P=P,UV=UV.astype(np.float32),F=F,weld=weld)
img=[i for i in bpy.data.images if 'metallic' not in i.name and 'normal' not in i.name and i.size[0]>0][0]
img.filepath_raw=out+'/basecolor_4k.png'; img.file_format='PNG'; img.save()
print('DONE',P.shape,F.shape,P.min(0),P.max(0))
