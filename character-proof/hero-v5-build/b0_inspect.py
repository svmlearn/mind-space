# blender -b -P b0_inspect.py -- raw.glb outdir : stats + unlit/lit views of the raw Hunyuan3D model
import bpy, sys, math, mathutils, numpy as np
argv=sys.argv[sys.argv.index('--')+1:]; glb,out=argv[0],argv[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
objs=[o for o in bpy.context.scene.objects if o.type=='MESH']
for o in objs:
  me=o.data; me.calc_loop_triangles()
  co=np.array([o.matrix_world@v.co for v in me.vertices])
  print('OBJ',o.name,'verts',len(me.vertices),'tris',len(me.loop_triangles),'bbox',co.min(0).round(3),co.max(0).round(3))
  # islands (loose parts)
  import bmesh
  bm=bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
  seen=np.zeros(len(bm.verts),bool); sizes=[]
  for v in bm.verts:
    if seen[v.index]: continue
    st=[v]; seen[v.index]=True; c=0
    while st:
      x=st.pop(); c+=1
      for e in x.link_edges:
        y=e.other_vert(x)
        if not seen[y.index]: seen[y.index]=True; st.append(y)
    sizes.append(c)
  sizes.sort(reverse=True); print('ISLANDS',len(sizes),sizes[:10])
  print('UVlayers',[l.name for l in me.uv_layers])
for im in bpy.data.images:
  px=np.array(im.pixels[:]).reshape(-1,4) if im.size[0] else None
  print('IMG',im.name,im.size[:],im.colorspace_settings.name, 'mean',px.mean(0).round(3) if px is not None else None,'min',px.min(0).round(3),'max',px.max(0).round(3))
