from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json

W=Path(__file__).resolve().parent
A=W/'staging' if (W/'staging/Textures').exists() else W
H='Textures/Things/Hair/R99';B='Textures/Things/R99_Agents/Arcanist'
font=lambda s:ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',s)
names=[('before','十四行诗 v1 · 修改前'),('current','十四行诗 v2 · 当前'),('Vertin_v13','Vertin v13 · 尺寸参考'),('Texas','Texas · 画风参考')]
directions=[('south','正面'),('east','侧面'),('north','背面')]
def read(n,d):
    if n=='before':p=W/'before'/H/f'Sonetto_{d}.png'
    elif n=='current':p=A/H/f'Sonetto_{d}.png'
    else:p=W/'references'/f'{n}_head_{d}.png'
    return Image.open(p).convert('RGBA')
def panel(sheet,im,xy,crop,scale):
    bg=Image.new('RGBA',im.size,'#e4eaf0');bg.alpha_composite(im)
    area=bg.crop(crop);sheet.paste(area.resize((area.width*scale,area.height*scale),Image.Resampling.NEAREST).convert('RGB'),xy)

def main():
    boxes=[read(n,d).getchannel('A').point(lambda a:255 if a>=8 else 0).getbbox() for n,_ in names for d,_ in directions]
    crop=(max(0,min(b[0] for b in boxes)-5),max(0,min(b[1] for b in boxes)-5),min(256,max(b[2] for b in boxes)+5),min(256,max(b[3] for b in boxes)+5))
    cw=(crop[2]-crop[0])*2+26;rh=(crop[3]-crop[1])*2+16
    sheet=Image.new('RGB',(24+4*cw,150+3*rh+42),'#f7f9fb');dr=ImageDraw.Draw(sheet)
    dr.text((24,18),'十四行诗 · 头部比例修正前后',font=font(28),fill='#213d50')
    dr.text((24,62),'同一 2× 像素比例与裁切范围；取消纵向拉伸，重新校准眼线、下巴和三向头部高度。',font=font(19),fill='#5a7383')
    for col,(n,title) in enumerate(names):
        x=24+col*cw;dr.text((x,112),title,font=font(18),fill='#285168')
        for row,(d,_) in enumerate(directions):panel(sheet,read(n,d),(x,150+row*rh),crop,2)
    dr.text((24,sheet.height-34),'发型、瞳色、鼻嘴和神情沿用原稿；躯干与物品图未改动。',font=font(18),fill='#5a7383')
    sheet.save(W/'head_before_after_comparison.png')

    sheet=Image.new('RGB',(1360,775),'#f7f9fb');dr=ImageDraw.Draw(sheet)
    dr.text((24,18),'面部近看 · 同一原生像素倍率',font=font(28),fill='#213d50')
    dr.text((24,64),'统一 4×；重点比较眼线以下脸长、下巴与眼睛开度。各人物未按脸部包围框另行缩放。',font=font(18),fill='#5a7383')
    for col,(n,title) in enumerate(names):
        x=24+col*330;dr.text((x,110),title,font=font(18),fill='#285168')
        for row,(d,_) in enumerate(directions[:2]):panel(sheet,read(n,d),(x,150+row*268),(96,120,174,182),4)
    dr.text((24,708),'正面 / 侧面：采用等比缩放，保留原始脸型、五官与表情关系，避免额外拉长头脸。',font=font(19),fill='#5a7383')
    sheet.save(W/'face_before_after_comparison.png')

    sheet=Image.new('RGB',(1100,690),'#f7f9fb');dr=ImageDraw.Draw(sheet)
    dr.text((24,18),'十四行诗 · 完整人物前后对照',font=font(28),fill='#213d50')
    for col,(n,d,title) in enumerate([('before','south','正面 · 修改前'),('current','south','正面 · 当前'),('before','east','侧面 · 修改前'),('current','east','侧面 · 当前')]):
        x=24+col*270;dr.text((x,70),title,font=font(20),fill='#285168')
        im=Image.new('RGBA',(256,384))
        im.alpha_composite(Image.open(A/B/f'Sonetto_Thin_{d}.png').convert('RGBA'),(0,80))
        im.alpha_composite(read(n,d),(0,15))
        panel(sheet,im,(x,110),(60,80,186,340),2)
    dr.text((24,651),'头部预览偏移均为 (0,-65)，躯干使用同一文件。',font=font(18),fill='#5a7383')
    sheet.save(W/'pawn_before_after.png')
    print('Created three comparison boards')

if __name__=='__main__':main()
