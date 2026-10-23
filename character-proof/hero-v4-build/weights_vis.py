import bpy, sys, math, mathutils
argv=sys.argv[sys.argv.index('--')+1:]; glb,out=argv[0],argv[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
sc=bpy.context.scene; sc.render.engine='BLENDER_EEVEE_NEXT'; sc.render.resolution_x=sc.render.resolution_y=640; sc.view_settings.view_transform='Standard'
w=bpy.data.worlds.new('w'); sc.world=w; w.use_nodes=True; wn=w.node_tree; [wn.nodes.remove(n) for n in list(wn.nodes)]; bg=wn.nodes.new('ShaderNodeBackground'); wo=wn.nodes.new('ShaderNodeOutputWorld'); wn.links.new(bg.outputs[0],wo.inputs[0]); bg.inputs[0].default_value=(0.8,0.8,0.8,1)
me=[o for o in bpy.data.objects if o.type=='MESH'][0]; arm=[o for o in bpy.data.objects if o.type=='ARMATURE'][0]
pal={'body':(0.9,0.9,0.9),'head':(0.2,0.4,1),'thighL':(1,0.2,0.2),'shinL':(1,0.6,0.1),'footL':(0.5,0.1,0.1),'armL':(0.1,0.9,0.2),'thighR':(0.9,0.2,0.9),'shinR':(1,1,0.2),'footR':(0.4,0.1,0.5),'armR':(0.1,0.8,0.8),'root':(0,0,0)}
mesh=me.data; ca=mesh.color_attributes.new('wcol','FLOAT_COLOR','POINT')
gn={g.index:g.name for g in me.vertex_groups}
for v in mesh.vertices:
    c=[0,0,0]
    for g in v.groups:
        p=pal.get(gn[g.group],(0,0,0)); c=[c[i]+p[i]*g.weight for i in range(3)]
    ca.data[v.index].color=(*c,1)
mat=bpy.data.materials.new('wm'); mat.use_nodes=True; nt=mat.node_tree; [nt.nodes.remove(n) for n in list(nt.nodes)]
at=nt.nodes.new('ShaderNodeVertexColor'); at.layer_name='wcol'; em=nt.nodes.new('ShaderNodeEmission'); o=nt.nodes.new('ShaderNodeOutputMaterial'); nt.links.new(at.outputs[0],em.inputs[0]); nt.links.new(em.outputs[0],o.inputs[0])
tex_mats=list(me.data.materials)
cam=bpy.data.objects.new('cam',bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera=cam; cam.data.type='ORTHO'; cam.data.ortho_scale=2.3
def shot(name,az,el=0):
    az,el=math.radians(az),math.radians(el); c=mathutils.Vector((0,0,1.0))
    d=mathutils.Vector((-math.sin(az)*math.cos(el),-math.cos(az)*math.cos(el),math.sin(el)))
    cam.location=c+d*10; cam.rotation_euler=d.to_track_quat('Z','Y').to_euler()
    sc.render.filepath=f'{out}-{name}.png'; bpy.ops.render.render(write_still=True)
me.data.materials[0]=mat
shot('wf',0); shot('wb',180); shot('ws',90)
# pose test: arms swing forward/back, legs stride, head turn
me.data.materials[0]=tex_mats[0]
# emission for texture
tm=tex_mats[0]; t=tm.node_tree; b=[n for n in t.nodes if n.type=='BSDF_PRINCIPLED'][0]; e=t.nodes.new('ShaderNodeEmission'); oo=[n for n in t.nodes if n.type=='OUTPUT_MATERIAL'][0]; t.links.new(b.inputs['Base Color'].links[0].from_socket,e.inputs[0]); t.links.new(e.outputs[0],oo.inputs[0])
pb=arm.pose.bones
for n,ax_,ang in [('armL','X',35),('armR','X',-35),('thighL','X',30),('shinL','X',-35),('thighR','X',-25),('head','Y',25)]:
    if n in pb: pb[n].rotation_mode='XYZ'; setattr(pb[n].rotation_euler,'xyz'[ 'XYZ'.index(ax_)] ,math.radians(ang)) if False else None; r=[0,0,0]; r['XYZ'.index(ax_)]=math.radians(ang); pb[n].rotation_euler=r
bpy.context.view_layer.update()
shot('pf',0); shot('ps',90); shot('p34',35,10)
