import bpy, sys, math, mathutils
argv=sys.argv[sys.argv.index('--')+1:]; glb,out=argv[0],argv[1]
# views: list of "name:az:el:cx:cy:cz:ortho"
bpy.ops.wm.read_factory_settings(use_empty=True)
if glb.endswith('.blend'): bpy.ops.wm.open_mainfile(filepath=glb)
else: bpy.ops.import_scene.gltf(filepath=glb)
sc=bpy.context.scene; sc.render.engine='BLENDER_EEVEE_NEXT'; sc.render.resolution_x=int(argv[3]) if len(argv)>3 else 512; sc.render.resolution_y=sc.render.resolution_x; sc.view_settings.view_transform='Standard'
w=bpy.data.worlds.new('w'); sc.world=w; w.use_nodes=True; wn=w.node_tree; [wn.nodes.remove(n) for n in list(wn.nodes)]; bg=wn.nodes.new('ShaderNodeBackground'); wo=wn.nodes.new('ShaderNodeOutputWorld'); wn.links.new(bg.outputs[0],wo.inputs[0]); bg.inputs[0].default_value=(0.75,0.8,0.85,1); bg.inputs[1].default_value=1.0
for m in bpy.data.materials:
  if not m.use_nodes: continue
  nt=m.node_tree; b=[n for n in nt.nodes if n.type=='BSDF_PRINCIPLED']
  if not b or not b[0].inputs['Base Color'].links: continue
  em=nt.nodes.new('ShaderNodeEmission'); o=[n for n in nt.nodes if n.type=='OUTPUT_MATERIAL'][0]
  nt.links.new(b[0].inputs['Base Color'].links[0].from_socket,em.inputs[0]); nt.links.new(em.outputs[0],o.inputs[0])
cam=bpy.data.objects.new('cam',bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera=cam; cam.data.type='ORTHO'
for spec in argv[2].split(';'):
  n,az,el,cx,cy,cz,os_=spec.split(':'); az,el=math.radians(float(az)),math.radians(float(el)); c=mathutils.Vector((float(cx),float(cy),float(cz)))
  d=mathutils.Vector((-math.sin(az)*math.cos(el),-math.cos(az)*math.cos(el),math.sin(el)))
  cam.location=c+d*10; cam.rotation_euler=d.to_track_quat('Z','Y').to_euler(); cam.data.ortho_scale=float(os_); cam.data.clip_end=100
  sc.render.filepath=f'{out}-{n}.png'; bpy.ops.render.render(write_still=True)
