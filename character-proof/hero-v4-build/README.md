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
7b. `step3c_fix.py [passes]`（iter3，默认全部：`side,hand,shoe,hood,hair`；加 `dbg` 输出候选点调试模型）：读 `geom3/atlas_final3/tpos3`，输出 `work/geom4.npz`、`atlas_final4.png`、`tpos4.npz`。
   - side：正面投影落到侧脸/太阳穴的黑色拖影和“贴纸眼”——按法线朝向（nz<0.5）和皮肤表面深度挑出侧面的暗色/低饱和像素，用 3D 近邻（cKDTree）从好皮肤（y≤1.70）或好头发（y>1.70）取色填平，再做一圈 3D 高斯平滑。眼睛只在正面到约 3/4 侧可见，正脸贴图不动。
   - hand：手的贴图色相/饱和度对齐脸部皮肤中位数（亮度 ×0.93），手的顶点以手腕为中心缩到 85%（靠近袖口处平滑过渡）。
   - shoe：y<0.26 的鞋子顶点按每只脚的鞋底中心在 x/z 缩到 86%、高度 92%，鞋底贴地，0.15–0.24 渐变回原样（裤脚不动）。
   - hood：颈后/肩背 y 1.12–1.62 的毛衣贴图用 3D 中值（48 邻点、半径 0.04）重建低频色 + 一半细纹理，去掉兜帽轮廓画线；后颈小暗点（含一块透出来的反面小三角的取色）用周围毛衣色填掉 → 读作高领毛衣。
   - hair：后脑头发按绕头角度加三组正弦发丝明暗（±16%）、y≈2.02 一条柔和高光带，整体提亮约 10–15%。
8. `step4_rig.py [headTilt headScale UP EB EF]`（当前 `0.2`，其余默认 1.08 / 1.12 / 0.20 / 0.50）：毛衣色相回到原画的青绿色、居中、缩放到 2 个单位高；按规则写蒙皮权重（头发全部跟头，袖子与躯干分开），骨骼名与 `grounded-rig.js` 一致，并把骨骼尾端（`extras.tail`）和步态参数（`GroundedHero.extras.gait`）写进 glTF，输出 `work/hero-v4.glb`（iter3 起读 `geom4/atlas_final4`；步态里新增 `armSwingGain=1.15`、`armSwingMax`=0.30×K，手臂与同侧腿反相摆动幅度约为 v3 的 2 倍；后脑头发的 emissive 额外 +0.10）。UP=1.12 把人物放大到 2.24 单位高（与 v3 在画面里的大小相当）。另写一张 emissive 贴图（glTF `emissiveTexture`：身体 0.20、脸/皮肤/耳/手 0.50 的暖色自发光，让脸在场景里够亮），以及 `GroundedHero.extras.eyes`（两只眼在绑定空间里的椭圆、z 下限和肤色），前端用来做眨眼。

`closeup.py` / `weights_vis.py` 是 Blender 4.5 无界面渲染检查用（`blender -b -P closeup.py -- <glb> <outprefix> "<name:az:el:cx:cy:cz:ortho;...>" 640`）。

依赖：Python 3 + numpy、scipy、opencv-python-headless、pygltflib（生成那一步另需 gradio_client）。
