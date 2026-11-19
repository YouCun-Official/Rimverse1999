X v2 · 闭口微笑与侧面头部前移（2026-11-08）

本次按用户反馈，只调整 south / east 两张头部：张口笑改成轻松、克制的闭口微笑；east 朝右侧面在 256×256 原生画布中向右平移 4 像素，保持 0° 旋转、原尺寸目标及垂直定位。背面头部、三向躯干、物品图及其他角色不变。

绘制使用内置 image_gen 局部编辑。imagegen_prompts.json 保存本次两条完整提示词；imagegen_prompts_v1.json 保存六部件及既有侧躯干修订的历史提示词。source_art 为当前完整六原稿；source_art_before 保留两张修改前头部。新头部的发型、异色瞳、眼眉、鼻、短下巴及配色作视觉核查，不声称生图保留区逐像素不变。

完整套装位于本目录 Textures，共 7 张 256×256 RGBA 透明 PNG；物品图与正面躯干字节一致。正式目录仅替换 X_south.png 与 X_east.png。当前版本记录：C:\Users\29232\Desktop\Lannuosprojects\MIS_Lannuosproject\MIS_Reverse1999\Tools\PortraitToPawn\characters\X.json

预览：changes_before_after.png（前后对比）、three_views_final.png（完整三视图）、heads_three_views.png / bodies_three_views.png（分件）、native_and_reduced.png（原尺寸与 50%）、character_comparison.png / head_style_comparison.png（同尺度参考）。预览棋盘格不在贴图内。

复现：在本目录运行 python format_assets.py --recipe recipe.json --out 新输出目录
依赖 Python、Pillow、numpy。沿用 4 倍采样、原描边和透明边缘处理。头身预览偏移仍为 (0,-72)；侧头 +4 像素已写入头部图本身，不应再在预览或游戏配置重复叠加。

格式、透明边缘、哈希、归档复现和安装一致性检查通过；35 张未修改正式纹理保持字节一致。游戏内效果尚未验证。本次用户关于表情的修订保存在 X 的角色记录，通用规范未改动。
旧版本：C:\Users\29232\Desktop\Lannuosprojects\MIS_Lannuosproject\MIS_Reverse1999\Tools\PortraitToPawn\exports\X_v1
备份：C:\Users\29232\Desktop\Lannuosprojects\MIS_Lannuosproject\MIS_Reverse1999\Tools\TextureBackups\X_before_v2_20261108_a5568ee4.zip
