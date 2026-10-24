# hero-v5 构建脚本（站立/行走人物，默认主角）

`assets/meadow/hero-v5.glb` 由这些脚本生成。来源与许可见根目录 `THIRD_PARTY_NOTICES.md`。

目录约定（脚本都用相对路径）：在一个工作目录里放 `build/`（本目录的脚本）、`inputs/`、`work_hr/`，以及原始模型 `hunyuan31-raw.glb`，在 `build/` 里运行。

- `inputs/front-white.png`：从 `character-proof/assets/painted-turnaround.png` 裁出的正面图（白底），第 3 步用它把原画的脸投影到模型上；也可以用环境变量 `PAINT=...` 指定。
- `hunyuan31-raw.glb`：腾讯混元3D 3.1 官网用原画切出的正/背/左/右 4 张图生成并导出的 GLB（约 50 万三角面、4096² 贴图、44 MB、无骨骼、自然站姿）。它太大，没有放进仓库。

高精度版（当前仓库里的版本，不减面）：

```
PY=python3   # 需要 numpy、scipy、opencv-python-headless、pygltflib
blender -b -P b1_prep.py -- ../hunyuan31-raw.glb ../work_hr 600000
WORK=../work_hr TEX=basecolor_4k.png $PY s2_shape.py 0.14
WORK=../work_hr TEX=basecolor_4k.png $PY s3_face.py
WORK=../work_hr TEX=basecolor_4k.png JPEG=95 $PY s4_rig.py 20 9 0.15 1.0 ../hero-v5.glb
```

1. `b1_prep.py -- raw.glb outdir [目标三角面]`（Blender 4.5 无界面）：把混元的 Z 轴向上节点旋转烘进顶点（glTF：+Y 向上、+Z 向前），高 2.24 单位、脚底为原点，焊接 UV 拆开的顶点（`weld`），输出 `dec.npz` 和 `basecolor_4k.png`。目标面数 ≥ 原始面数时**不减面**（高精度版用 600000 → 保留全部 50 万面）；给 55000 时就是早先的 5.5 万面轻量版（另把贴图缩到 2048，存成 `base2k.png`，不设 `TEX`）。
2. `s2_shape.py [0.14]`：头发向头骨收小 14%（两侧/后面/头顶多，刘海少）；正脸用稀疏矩阵做 Taubin 平滑（迭代次数随面数增加）；鼻子和嘴的立体凸起用双调和（biharmonic）方程从周围脸面重新填平，嘴缝里朝后的小三角删掉——脸由原画投影来画，不需要几何上的鼻嘴。输出 `shape.npz`。
3. `s3_face.py [dbg]`：把原画的正脸（眼睛、眉毛、鼻点、微笑、腮红）按两眼位置对齐投影到模型的正脸贴图上，只改正面可见的像素，往侧脸渐隐；原画是皮肤而模型是头发的额头像素填原画肤色。输出 `atlas_face.png`、`facew.npy`、`face.json`、`tmap_shape.npz`。
4. `s4_rig.py AU AF headTilt headScale out`（当前 `20 9 0.15 1.0`）：按规则写蒙皮权重和骨骼（名字与 `grounded-rig.js` 一致：body、head、thighL/R、shinL/R、footL/R、armL/R，外加两节手臂的 `forearmL/R`），骨骼尾端写进 `extras.tail`，步态尺寸和 iter5 步态参数写进 `GroundedHero.extras.gait`，眼睛椭圆写进 `extras.eyes`（眨眼）。另写：
   - emissive 贴图（身体 0.20、脸/皮肤 0.50 的暖色自发光）。模糊只在每个 UV 分块内部做：混元的贴图有约 2400 个挤在一起的小分块，普通的整图模糊会把旁边深色分块“渗”进皮肤，在脸上画出接缝线。
   - 顶点属性 `_OUTLINE`（描边宽度系数）：额头刘海处为 0；高精度网格上，凹处、以及“沿法线外推描边宽度后离别的表面太近”（耳朵贴脸颊、领口贴下巴、刘海贴额头）的地方自动变细，避免反向壳从小缝里穿出黑点。
   - 贴图：4096² 基础色 JPEG 质量 95（4:4:4 色度，肉眼无损），emissive 2048²。没有法线贴图：50 万面几何本身已有细节，法线贴图会把压平的鼻嘴立体感带回来，而卡通渐变也会把它量化掉。
   - 环境变量：`WORK`（工作目录，默认 `../work`）、`TEX`、`JPEG`（默认 88）、`EMIS`（emissive 尺寸，默认贴图一半）、`CONC_K`（凹度检测的邻域圈数）。

检查工具：`b0_inspect.py -- raw.glb outdir`（原始模型统计与渲染）、`closeup.py`（Blender 特写渲染，用法同 hero-v4-build）、`swr.py`（numpy 软件光栅器，前几步用来找眼睛位置和做 QA）、`heroio.py`（贴图像素→3D 位置映射、法线、GLB 写出）。

结果：499,014 三角面、300,837 顶点、约 26.3 MB（没有 Draco/meshopt 压缩，three.js 原生 GLTFLoader 直接读）。
