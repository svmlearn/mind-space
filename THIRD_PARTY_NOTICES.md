# 第三方组件与素材边界

## Three.js

`vendor/three/` 包含 Three.js 运行时代码及 GLTFLoader、BufferGeometryUtils。保留了原始许可文本：

- [vendor/three/LICENSE.txt](vendor/three/LICENSE.txt)
- 上游：<https://github.com/mrdoob/three.js>

该目录中的第三方代码依 MIT License 分发。MIT License 不自动覆盖本项目的图像、模型或其他原创文件。

## 本项目素材

网站包含既有原型的生成图像、人物模型和动作研究素材。当前窗景使用 `train-landscape.webp`、`panorama-lake.webp`、`panorama-valley.webp`，不是旧版电影剧照。

曾用于私有设计研究、但当前代码已不再引用的 5 张 `your-name-*.webp` 电影剧照没有放入这个公开交接副本。不要从历史工作目录重新加入。

本次没有为本项目新增统一的开源许可证，也没有承诺所有素材适用于任何商业用途。新增外部资源时，请核对具体代码、模型、贴图和动画各自的许可，不能因为某个运行库是 MIT 就推断它的示例素材同样可用。

## 站立/行走人物 hero-v4（TRELLIS 生成）

`assets/meadow/hero-v4.glb` 的几何与初始贴图由 TRELLIS（Microsoft，MIT License）根据本项目自己的原画 `character-proof/assets/painted-turnaround.png` 的 4 个视角生成，之后用 `character-proof/hero-v4-build/` 里的脚本做了清理、原画面部投影、绑定与蒙皮。

- 代码：<https://github.com/microsoft/TRELLIS>（MIT License）
- 权重：<https://huggingface.co/microsoft/TRELLIS-image-large>（MIT License）
- 运行方式：Hugging Face Space `trellis-community/TRELLIS`（免费 ZeroGPU 额度，未付费）
- 输入只有本项目自己的原画，没有使用其他第三方图像或模型。

旧人物 `assets/meadow/character-v3.glb` 仍保留，作为加载失败时的后备，也可以用 `?walker=v3` 强制使用。
