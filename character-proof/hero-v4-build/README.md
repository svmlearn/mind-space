# hero-v4 构建脚本（站立/行走人物）

`assets/meadow/hero-v4.glb` 是由这些脚本生成的。来源与许可见根目录 `THIRD_PARTY_NOTICES.md`。

目录约定（脚本用相对路径）：在一个工作目录里放 `tools/`（本目录的脚本）、`inputs/`、`gen/`、`work/`，从 `tools/` 里运行。

1. `inputs/`：从 `character-proof/assets/painted-turnaround.png` 裁出的正面/侧面/背面/另一侧 4 张图（1024²，泛洪去背景，RGBA）。
2. `generate_trellis.py <tag> <seed> multi`：调用 Hugging Face Space `trellis-community/TRELLIS`（MIT）做多视图 image-to-3D。需要环境变量 `HF_TOKEN`（只从环境读取，不要写进文件）。选用的是 `trellis-multi-s1`（seed 1，stochastic）。
3. `step1_geom.py`：统一尺度（高 2.3）、脚底为原点、去掉鞋底外沿的薄片。
4. `tmap.py`：把每个贴图像素映射回 3D 位置（后续按身体部位修贴图）。
5. `step2_tex.py`：修贴图：裤子/毛衣/袖子上的灰白条纹、鞋底、偏黄的手、提亮；把正面原画投影到脸上（眼睛、微笑），边缘羽化。
6. `step3_hood.py`：把背后的兜帽压平成高领毛衣的背面，并抹掉背后兜帽的画线。
7. `step3b_face.py BANG EAR GAIN KA KB EYS`（当前 `0.05 0.8 0.9 1.98 2.32 1.18`）：让脸在游戏的俯视镜头下看得见。把额前刘海的前伸部分压回脸面（只压眼睛上方那一带，头顶蓬松轮廓保留），耳朵缩到 80%，背后兜帽边缘硬压平；用正面深度图找出仍盖在眼睛上的刘海贴图，用原画正脸重新投影并把眼睛在竖直方向拉长 1.18（抵消俯视压扁）；清理后颈暗点、袖口肤色点和极小 UV 面的取色错误。输出 `work/geom3.npz`、`atlas_final3.png`、`facew3.npy`（脸部权重）。刘海贴在额头的顶点写入顶点属性 `_OUTLINE`=0（描边在那里变细，免得眼睛上方一道黑线）。
8. `step4_rig.py [headTilt headScale UP EB EF]`（当前 `0.2`，其余默认 1.08 / 1.12 / 0.20 / 0.50）：毛衣色相回到原画的青绿色、居中、缩放到 2 个单位高；按规则写蒙皮权重（头发全部跟头，袖子与躯干分开），骨骼名与 `grounded-rig.js` 一致，并把骨骼尾端（`extras.tail`）和步态参数（`GroundedHero.extras.gait`）写进 glTF，输出 `work/hero-v4.glb`。UP=1.12 把人物放大到 2.24 单位高（与 v3 在画面里的大小相当）。另写一张 emissive 贴图（glTF `emissiveTexture`：身体 0.20、脸/皮肤/耳/手 0.50 的暖色自发光，让脸在场景里够亮），以及 `GroundedHero.extras.eyes`（两只眼在绑定空间里的椭圆、z 下限和肤色），前端用来做眨眼。

`closeup.py` / `weights_vis.py` 是 Blender 4.5 无界面渲染检查用（`blender -b -P closeup.py -- <glb> <outprefix> "<name:az:el:cx:cy:cz:ortho;...>" 640`）。

依赖：Python 3 + numpy、scipy、opencv-python-headless、pygltflib（生成那一步另需 gradio_client）。
