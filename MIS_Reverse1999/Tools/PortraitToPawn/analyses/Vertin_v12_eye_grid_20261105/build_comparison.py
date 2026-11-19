"""Read-only texture analysis: integer nearest-neighbor grids and reviewed eye boxes."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import json, csv, hashlib

OUT=Path(__file__).resolve().parent
DATA=json.loads((OUT/'measurements.json').read_text(encoding='utf-8'))
CHARS=DATA['characters']
BG='#f6f8fa'; INK='#233e50'; MUTED='#557183'; BLUE='#0078ad'; PINK='#bf426d'; ORANGE='#ae6500'; GREEN='#25855b'
font=lambda n: ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',n)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def num(v): return str(int(v)) if float(v).is_integer() else f'{v:.1f}'
def size(box): return (box[2]-box[0],box[3]-box[1])
def text(d,xy,s,n=20,fill=INK): d.text(xy,s,font=font(n),fill=fill)
def centered(d,xy,s,n=18,fill=INK):
    f=font(n);w=d.textbbox((0,0),s,font=f)[2]; d.text((xy[0]-w/2,xy[1]),s,font=f,fill=fill)

rows=[]
for c in CHARS:
    a,b=c['south']['left'],c['south']['right'];aw,ah=size(a);bw,bh=size(b)
    f=c['south']['face_span'];fw=f[2]-f[0];gap=b[0]-a[2];cd=(b[0]+b[2]-a[0]-a[2])/2;ew,eh=size(c['east']['eye'])
    row=dict(name=c['name'],left_width=aw,left_height=ah,right_width=bw,right_height=bh,
             mean_eye_width=(aw+bw)/2,mean_eye_height=(ah+bh)/2,inner_gap=gap,box_center_distance=cd,
             visible_face_width=fw,face_y=f[1],eye_width_over_visible_face=round((aw+bw)/2/fw,4),
             gap_over_mean_eye_width=round(gap/((aw+bw)/2),4),gap_over_visible_face=round(gap/fw,4),
             east_eye_width=ew,east_eye_height=eh)
    c['metrics']=row;rows.append(row)
with (OUT/'eye_metrics.csv').open('w',newline='',encoding='utf-8-sig') as f:
    wr=csv.DictWriter(f,fieldnames=list(rows[0]));wr.writeheader();wr.writerows(rows)
(OUT/'eye_metrics.json').write_text(json.dumps({'measurement_spec':{k:v for k,v in DATA.items() if k!='characters'},'characters':CHARS},ensure_ascii=False,indent=2),encoding='utf-8')

def crop_image(name,di,crop,scale):
    im=Image.open(OUT/'inputs'/f'{name}_{di}.png').convert('RGBA')
    bg=Image.new('RGBA',im.size,'#e7edf1');d=ImageDraw.Draw(bg)
    for y in range(0,256,8):
        for x in range(0,256,8):
            if (x//8+y//8)%2==0:d.rectangle((x,y,x+7,y+7),fill='#dfe5eb')
    bg.alpha_composite(im)
    return bg.crop(crop).resize(((crop[2]-crop[0])*scale,(crop[3]-crop[1])*scale),Image.Resampling.NEAREST)

def tile_grid(canvas,origin,crop,scale):
    x,y=origin;w=(crop[2]-crop[0])*scale;h=(crop[3]-crop[1])*scale
    ov=Image.new('RGBA',canvas.size);g=ImageDraw.Draw(ov)
    for xx in range(crop[0],crop[2]+1):
        px=x+(xx-crop[0])*scale
        g.line((px,y,px,y+h),fill=(31,79,111,88 if xx%4==0 else 27),width=1)
    for yy in range(crop[1],crop[3]+1):
        py=y+(yy-crop[1])*scale
        g.line((x,py,x+w,py),fill=(31,79,111,88 if yy%4==0 else 27),width=1)
    canvas.alpha_composite(ov);d=ImageDraw.Draw(canvas)
    label_step=8 if scale<8 else 4
    for xx in range(crop[0],crop[2]+1,label_step):
        centered(d,(x+(xx-crop[0])*scale,y-20),str(xx),12,MUTED)
    for yy in range(crop[1],crop[3]+1,4):
        text(d,(x-29,y+(yy-crop[1])*scale-7),str(yy),11,MUTED)

def bracket(d,p1,p2,color):
    x1,y1=p1;x2,y2=p2;d.line((x1,y1,x2,y2),fill=color,width=2)
    if y1==y2:
        d.line((x1,y1-5,x1,y1+5),fill=color,width=2);d.line((x2,y2-5,x2,y2+5),fill=color,width=2)
    else:
        d.line((x1-5,y1,x1+5,y1),fill=color,width=2);d.line((x2-5,y2,x2+5,y2),fill=color,width=2)

def front_chart(marked=True):
    crop=(100,128,156,160);sc=9;w=56*sc;h=32*sc;cw=w+56;ch=h+194
    out=Image.new('RGBA',(36+3*cw,158+2*ch+112),BG);d=ImageDraw.Draw(out)
    text(d,(28,18),'眼睛尺寸与间距 · 正面原生像素网格',30)
    text(d,(28,64),'全部 256×256 原图，统一 9×最近邻放大；每小格 = 1 px，加深线每 4 px。',19,MUTED)
    text(d,(28,96),'蓝框：可见眼裂　粉线 G：内缘间隔　橙线 C：两眼框中心距（非瞳距）',18,MUTED)
    for i,c in enumerate(CHARS):
        bx=28+(i%3)*cw;by=158+(i//3)*ch;px=bx+30;py=by+51
        out.alpha_composite(crop_image(c['name'],'south',crop,sc),(px,py));tile_grid(out,(px,py),crop,sc);d=ImageDraw.Draw(out)
        text(d,(bx,by),c['label'],25,BLUE if i==0 else INK)
        def pt(x,y):return(px+(x-crop[0])*sc,py+(y-crop[1])*sc)
        a,b=c['south']['left'],c['south']['right'];m=c['metrics']
        if marked:
            for box in [a,b]:
                d.rectangle((*pt(box[0],box[1]),*pt(box[2],box[3])),outline=BLUE,width=2)
            cy=min(a[1],b[1])-5;cx1=(a[0]+a[2])/2;cx2=(b[0]+b[2])/2
            bracket(d,pt(cx1,cy),pt(cx2,cy),ORANGE)
            for cx,box in [(cx1,a),(cx2,b)]:
                for yy in range(int(cy)+1,box[1]):
                    if yy%2==0:d.line((*pt(cx,yy),*pt(cx,yy+1)),fill=ORANGE,width=1)
            centered(d,pt((cx1+cx2)/2,cy-3.2),'C '+num(m['box_center_distance']),15,ORANGE)
            gy=max(a[3],b[3])+3;bracket(d,pt(a[2],gy),pt(b[0],gy),PINK)
            centered(d,pt((a[2]+b[0])/2,gy+.8),'G '+num(m['inner_gap']),15,PINK)
        fy=py+h+14
        text(d,(bx,fy),f"左 {m['left_width']}×{m['left_height']} px    右 {m['right_width']}×{m['right_height']} px",20)
        text(d,(bx,fy+31),f"内缘 G {m['inner_gap']} px    中心 C {num(m['box_center_distance'])} px",19,PINK)
        text(d,(bx,fy+61),f"平均眼宽 {num(m['mean_eye_width'])} px · G/眼宽 {m['gap_over_mean_eye_width']:.2f}",18,MUTED)
    y=158+2*ch
    text(d,(28,y),'眼裂框含眼白、虹膜，排除眉毛、眼线厚度、睫毛尾；人工边界判读约有 1 px 不确定性。',18,MUTED)
    text(d,(28,y+29),'左/右均指画面；框为水平包围框，不推算刘海遮挡处。仅分析，未改动正式贴图。',18,MUTED)
    out.convert('RGB').save(OUT/('eye_grid_front.png' if marked else 'eye_grid_front_clean.png'))

def side_chart():
    crop=(128,128,168,160);sc=10;w=400;h=320;cw=464;ch=480
    out=Image.new('RGBA',(36+3*cw,150+2*ch+80),BG);d=ImageDraw.Draw(out)
    text(d,(28,18),'眼睛尺寸 · 朝右侧面原生像素网格',30)
    text(d,(28,62),'统一 10×最近邻放大；小格 1 px，加深线 4 px；侧面只测可见单眼。',19,MUTED)
    text(d,(28,94),'不同角色眼部坐标保留原样，不单独平移、旋转或缩放；上下位置差异可直接核对。',17,MUTED)
    for i,c in enumerate(CHARS):
        bx=28+(i%3)*cw;by=150+(i//3)*ch;px=bx+31;py=by+51
        out.alpha_composite(crop_image(c['name'],'east',crop,sc),(px,py));tile_grid(out,(px,py),crop,sc);d=ImageDraw.Draw(out)
        text(d,(bx,by),c['label'],25,BLUE if i==0 else INK)
        def pt(x,y):return(px+(x-crop[0])*sc,py+(y-crop[1])*sc)
        b=c['east']['eye'];w0,h0=size(b)
        d.rectangle((*pt(b[0],b[1]),*pt(b[2],b[3])),outline=BLUE,width=2)
        bracket(d,pt(b[0],b[3]+2),pt(b[2],b[3]+2),PINK)
        text(d,(bx,py+h+17),f'可见眼裂 {w0}×{h0} px',22)
        text(d,(bx,py+h+49),f'x [{b[0]},{b[2]})   y [{b[1]},{b[3]})',17,MUTED)
    text(d,(28,150+2*ch),'只计算可见部分；侧面不推算第二只眼及双眼间距。人工边界判读约有 1 px 不确定性。',17,MUTED)
    out.convert('RGB').save(OUT/'eye_grid_side.png')

def face_context():
    crop=(96,120,160,176);sc=5;w=320;h=280;cw=374;ch=410
    out=Image.new('RGBA',(36+3*cw,110+2*ch+100),BG);d=ImageDraw.Draw(out)
    text(d,(26,17),'脸宽辅助截面 · 保留五官与脸型上下文',28)
    text(d,(26,57),'统一 5×；绿线 F 为眼裂下沿所在行的可见面部宽度，不估补被遮挡脸宽。',17,MUTED)
    for i,c in enumerate(CHARS):
        bx=26+(i%3)*cw;by=110+(i//3)*ch;px=bx+29;py=by+45
        out.alpha_composite(crop_image(c['name'],'south',crop,sc),(px,py));tile_grid(out,(px,py),crop,sc);d=ImageDraw.Draw(out)
        text(d,(bx,by),c['label'],23,BLUE if i==0 else INK)
        def pt(x,y):return(px+(x-crop[0])*sc,py+(y-crop[1])*sc)
        f=c['south']['face_span'];m=c['metrics'];bracket(d,pt(f[0],f[1]+.5),pt(f[2],f[1]+.5),GREEN)
        text(d,(bx,py+h+12),f"F {m['visible_face_width']} px（y={m['face_y']}）",19,GREEN)
        text(d,(bx,py+h+42),f"平均眼宽/F {m['eye_width_over_visible_face']:.1%} · G/F {m['gap_over_visible_face']:.1%}",16,MUTED)
    y=110+2*ch
    text(d,(26,y),'可见截面受刘海和脸型影响，因此眼睛绝对像素尺寸是主对照，F 仅作辅助。',17,MUTED)
    text(d,(26,y+27),'当前 Vertin 与 Texas/Zima 的此处 F 均约 39 px，眼睛差异并非仅由脸的整体缩放造成。',16,MUTED)
    out.convert('RGB').save(OUT/'face_width_context.png')

def metrics_table():
    widths=[170,170,170,120,140,140,160];xs=[24]
    for w in widths:xs.append(xs[-1]+w)
    out=Image.new('RGB',(xs[-1]+24,630),BG);d=ImageDraw.Draw(out)
    text(d,(24,18),'像素对照结果 · 所选角色，不代表素材库统一规格',27)
    text(d,(24,60),'可见眼裂的人工包围框；混色边界约有 1 px 判读不确定性。',18,MUTED)
    headers=['角色','正面左眼 W×H','正面右眼 W×H','内缘 G','框中心 C','可见脸宽 F','侧眼 W×H']
    yy=111
    for j,h in enumerate(headers):text(d,(xs[j]+9,yy),h,17)
    for i,c in enumerate(CHARS):
        yy=152+i*55;d.rectangle((24,yy-3,xs[-1],yy+48),fill='#e4f0f5' if i==0 else ('#edf1f4' if i%2 else '#f7f9fb'))
        m=c['metrics'];vals=[c['label'],f"{m['left_width']}×{m['left_height']}",f"{m['right_width']}×{m['right_height']}",str(m['inner_gap']),num(m['box_center_distance']),str(m['visible_face_width']),f"{m['east_eye_width']}×{m['east_eye_height']}"]
        for j,v in enumerate(vals):text(d,(xs[j]+9,yy+8),v,20,BLUE if i==0 else INK)
    text(d,(24,505),'单位 px。C 是眼框中心的水平距离，不能等同于瞳距；G 是两眼框内缘的水平间隔。',17,MUTED)
    text(d,(24,539),'主要差异：Vertin 的眼宽、眼高偏小；与 Texas 的内缘间隔同为约 10 px。',20)
    text(d,(24,577),'因此优先评估眼睛尺寸；仅凭“显得间距大”就向内移动双眼，可能修正过度。',18,MUTED)
    out.save(OUT/'eye_metrics_table.png')

front_chart(True);front_chart(False);side_chart();face_context();metrics_table()

before=json.loads((OUT/'installed_hashes_before.json').read_text())
MOD=Path(r'C:\Users\29232\Desktop\Lannuosprojects\MIS_Lannuosproject\MIS_Reverse1999')
current={str(p.relative_to(MOD)):sha(p) for p in sorted((MOD/'Textures').rglob('*.png'))}
assert before==current,'Production textures changed during read-only analysis'
sources=json.loads((OUT/'sources.json').read_text(encoding='utf-8'))
for s in sources:
    assert sha(Path(s['source']))==s['sha256']==sha(OUT/s['local'])
    assert Image.open(OUT/s['local']).size==(256,256)
checks={'analysis_only':True,'installed_texture_count':len(before),'all_production_textures_unchanged':True,
        'source_hashes_verified':len(sources),'reference_count_quantified':5,'character_count_quantified':6,
        'resampling':'integer nearest neighbor only; no image edits, per-character resize, rotation or translation',
        'visible_measurement_annotations':'manual, source-coordinate boxes; about 1 px edge judgment uncertainty',
        'game_tested':False,'visual_review':'pending'}
(OUT/'validation.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'metrics':rows,'validation':checks},ensure_ascii=True))
