X v1 · 角色头部 / 躯干三视图（2026-11-08）

正式安装完成：头部位于 C:\Users\29232\Desktop\Lannuosprojects\MIS_Lannuosproject\MIS_Reverse1999\Textures\Things\Hair\R99；躯干和物品图位于 C:\Users\29232\Desktop\Lannuosprojects\MIS_Lannuosproject\MIS_Reverse1999\Textures\Things\R99_Agents\Arcanist。全部使用 X 前缀，与 Vertin 同级。共 7 张 256×256 RGBA 透明 PNG；物品图 X.png 与 X_Thin_south.png 字节一致。

原画：本地 X.png 为主，网络为辅助。保留灰紫短发、金蓝异色瞳、轻松笑容及服装标志配件。男性、宽松长外套按衣物垂坠处理，不套用女性收腰或 Vertin 条件尺寸基准。头部直立，无完整手臂与手。

生成方式：内置 image_gen 分别绘制六个部件；侧躯干局部修订口袋侧别及鞋尖。format_assets.py 仅处理透明边缘、4 倍采样缩放定位和轮廓补强。imagegen_prompts.json 保存完整 7 次提示词及对应来源，source_art 保存最终六份原稿，source_art_initial 保存被替换的侧躯干。

复现命令（在本目录）：
python format_assets.py --recipe recipe.json --out 新输出目录
依赖：Python、Pillow、numpy。输出目录须为空；不会重新调用生图。

预览：three_views_final.png 为完整三视图；heads_three_views.png / bodies_three_views.png 为分件；character_comparison.png 与 head_style_comparison.png 为同尺度比较；native_and_reduced.png 为原尺寸和 50% 预览；expression_and_identity_check.png 对照立绘神情；side_before_after.png 记录侧面修订。棋盘格仅用于预览，不存在于正式贴图。

recipe.json 保存逐图尺寸、定位和描边；预览头部相对躯干为 (0,-72)，不是游戏配置。后发、后肩披、外套中缝和开衩等不可见结构为合理推断，详见 character_brief.json。

静态检查通过：格式、透明边缘、朝向独立、物品副本、导出复现、安装哈希一致。安装前已有 16 张纹理（包括 Vertin、并行任务新增的 Regulus 及 UI）全部保持字节一致；原角色记录与通用规范未修改。当前资源为初次交付，用户视觉确认及游戏内显示尚未验证；本次未创建角色 Def。

记录：characters/X.json；installation_receipt.json；validation.json。
备份：C:\Users\29232\Desktop\Lannuosprojects\MIS_Lannuosproject\MIS_Reverse1999\Tools\TextureBackups\X_before_add_20261108_912d31e7.zip
