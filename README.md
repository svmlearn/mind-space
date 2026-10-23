# 心灵空间

一个以草坪、人物与个人叙事为中心的桌面 Web 交互原型。本仓库交接给设计/编程 AI，重点是改善人物站立、转身和走路后的表现，而不是重做整个产品。

请先阅读 [AI_HANDOFF.md](AI_HANDOFF.md)。

## 本地运行

这是原生 HTML、CSS、JavaScript 与 Three.js 的静态项目，没有 npm 安装或构建步骤。需要 Python 3 和支持 WebGL 的现代浏览器。

在仓库根目录运行：

```sh
python3 -m http.server 8000 --bind 127.0.0.1
```

Windows 也可以使用 `py -m http.server 8000 --bind 127.0.0.1`。

打开 <http://127.0.0.1:8000/>。请不要直接双击 HTML 使用 `file://`，因为 ES modules 与 GLB 加载需要 HTTP。

## 主要入口

- `/`：当前主页。默认坐在草坪中，可点击脸和手互动，再选择“去走走”。
- `/character-proof/`：较新的手绘风格 3D 人物造型对照。它是独立静态展示，尚未接入主页行走系统。
- `/motion-lab.html`：已有动作小样，含三维播放与视频回退。
- 其他 HTML 页面是保留的早期探索或交互原型，不是本轮要求重新设计的页面。

## 文件地图

| 文件/目录 | 作用 |
| --- | --- |
| `index.html`, `meadow.css` | 主页草坪、坐姿、站立视图与界面布局 |
| `meadow.js`, `meadow-navigation.js` | 模式切换、点击/键盘移动、树洞交互、路径约束 |
| `grounded-walker.js` | 主页 Three.js 场景、灯光、相机及角色加载 |
| `grounded-rig.js` | 现有骨骼、转向、脚步接地与摆臂逻辑 |
| `seated-rig.js`, `meadow-seated.js` | 坐姿人物的脸部与挥手互动 |
| `inner-home.js`, `inner-home.css` | 自传、来时路、路书及本地记录逻辑 |
| `assets/meadow/character-v3.glb` | 主页目前实际加载的可动角色 |
| `character-proof/meadow-hero.glb` | 较新的静态角色，不可直接视作已绑定的替代品 |
| `character-proof/assets/` | 概念图、四面制作参考及渲染图 |
| `vendor/three/` | 随项目提供的 Three.js 与 MIT 许可文本 |

## 数据和边界

- 没有后端、真实 AI 服务、真实支付或云同步；计费、余额等为原型演示。
- 页面状态保存在当前浏览器的 `localStorage`。仓库不包含用户浏览器中的个人记录。
- 自带文本是原型示例，不能当作真实用户经历或心理结论。
- 不需要 API key、部署 token 或 `.env`。托管平台配置和旧 Git 历史未放入交接副本。
- 这里只交接网站运行所需的资源，不包含完整 Blender 制作工程、历史备份或工作日志。
- 修改在本地或新分支验证，不要自动覆盖任何既有线上站点。

## 公开交接说明

本副本移除了 5 张未被当前页面引用的历史电影剧照，当前窗景仍使用原有生成风景，因此不影响现有功能。两张 PNG 的制作工具文字元数据已无损移除，逐像素验证与原图一致。其他项目素材与代码保持原样，交接文档为新增。

公开仓库不等同于为项目授予开源许可。本次未添加项目级开源许可证。第三方组件遵守各自许可证，见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

验证范围与已知限制见 [VALIDATION.md](VALIDATION.md)。
