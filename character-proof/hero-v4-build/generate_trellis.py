import sys, shutil, time
from gradio_client import Client, handle_file
I='../inputs/'; O='../gen/'
tag=sys.argv[1]; seed=int(sys.argv[2]); multi=sys.argv[3]=='multi'; algo=sys.argv[4] if len(sys.argv)>4 else 'stochastic'
import os; c=Client('trellis-community/TRELLIS',verbose=False,token=os.environ['HF_TOKEN'])
c.predict(api_name='/start_session')
t=time.time()
imgs=[{'image':handle_file(I+k+'.png'),'caption':None} for k in ['front','side','back','side2']] if multi else []
r=c.predict(image=handle_file(I+'front.png'), multiimages=imgs, seed=seed, ss_guidance_strength=7.5, ss_sampling_steps=12, slat_guidance_strength=3.0, slat_sampling_steps=12, multiimage_algo=algo, mesh_simplify=0.9, texture_size=2048, api_name='/generate_and_extract_glb')
print(time.time()-t, r)
v=r[0]['video'] if isinstance(r[0],dict) else r[0]
shutil.copy(v,O+tag+'.mp4'); shutil.copy(r[2] if r[2] else r[1],O+tag+'.glb'); print('saved',tag)
