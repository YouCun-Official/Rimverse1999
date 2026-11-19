"""Same-native-scale garment cross sections; widths are not hidden anatomical measurements."""
from pathlib import Path
import json,numpy as np
from PIL import Image,ImageDraw,ImageFont

W=Path(__file__).resolve().parent
A=W/'staging' if (W/'staging/Textures').exists() else W
B='Textures/Things/R99_Agents/Arcanist'
font=lambda n:ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',n)
def read(name,direction):
    if name=='Sonetto_before':p=W/'candidates/before_visibility_and_leg'/B/f'Sonetto_Thin_{direction}.png'
    elif name=='Sonetto':p=A/B/f'Sonetto_Thin_{direction}.png'
    else:p=W/'references'/f'{name}_body_{direction}.png'
    return Image.open(p).convert('RGBA')
def section(im,y):
    x=np.where(np.array(im.getchannel('A'))[y]>=128)[0]
    return {'y':y,'x0':int(x.min()),'x1_exclusive':int(x.max()+1),'span_px':int(x.max()+1-x.min())}

def main():
    names=['Sonetto_before','Sonetto','Vertin_v13','Texas']
    titles=['十四行诗 · 修订前','十四行诗 · 当前','Vertin v13 尺寸基准','Texas 画风参考']
    sheet=Image.new('RGB',(1220,1080),'#f5f8fa');dr=ImageDraw.Draw(sheet)
    dr.text((24,18),'原生像素参考线 · 侧腿厚度与衣物截面',font=font(28),fill='#203c50')
    dr.text((24,62),'全部采用同一 2× 倍率；披肩、裙摆和挂件计入着衣轮廓，不能当作身体肩宽或臀宽。',font=font(19),fill='#597080')
    crop=(56,80,192,256);colors=['#d07b29','#2d8c7c','#9864a7'];records={}
    for col,(name,title) in enumerate(zip(names,titles)):
        x=24+col*298
        dr.text((x,112),title,font=font(19),fill='#285168')
        records[name]={}
        for row,direction in enumerate(['east','south']):
            top=150+row*430;im=read(name,direction);bg=Image.new('RGBA',(256,256),'#e2e9ee');bg.alpha_composite(im)
            sheet.paste(bg.crop(crop).resize((272,352),Image.Resampling.NEAREST).convert('RGB'),(x,top))
            if direction=='east':
                ys=[120,220,240];labels=['上身衣物','腿/衣摆截面','脚踝/靴筒']
            else:
                ys=[115,150,175] if name.startswith('Sonetto') else ([115,140,170] if name=='Vertin_v13' else [115,145,170])
                labels=['肩部衣物','可见腰部衣物','裙摆' if name.startswith('Sonetto') else '髋部衣物/附件']
            data=[]
            for y,label,color in zip(ys,labels,colors):
                s=section(im,y);s['scope']=label;data.append(s)
                px0=x+(s['x0']-crop[0])*2;px1=x+(s['x1_exclusive']-crop[0])*2;py=top+(y-crop[1])*2
                dr.line((px0,py,px1,py),fill=color,width=2)
                dr.line((px0,py-5,px0,py+5),fill=color,width=2);dr.line((px1,py-5,px1,py+5),fill=color,width=2)
            records[name][direction]=data
            text=' / '.join(f'{d["span_px"]} px' for d in data)
            dr.text((x,top+359),text,font=font(19),fill='#285168')
    dr.text((24,995),'侧面：橙＝上身衣物；绿＝腿/衣摆截面；紫＝脚踝/靴筒。衣物遮挡的截面不作人体精确测量。',font=font(18),fill='#597080')
    dr.text((24,1030),'正面：橙＝肩部衣物；绿＝可见腰部；紫＝裙摆或髋部衣物。位置按各角色结构选取。',font=font(18),fill='#597080')
    sheet.save(W/'alignment_guides.png')
    data={'unit':'native pixels','alpha_threshold':128,'display_scale':2,'records':records,
          'scope':'Full clothed row extents, not an estimate of hidden anatomy. Sonetto cape/skirt are loose layers; Vertin coat tails contribute to some lower-leg rows.',
          'baseline':'Vertin_v13_arknights_skin','head_calibration':'Facial anchor transforms in recipe.json; long-hair dimensions are independent extensions.',
          'side_pose':'Upright head, continuous diagonal body; shoe sole baseline at native y252 exclusive.'}
    (W/'measurements.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'side_ankle_y240':{n:records[n]['east'][2]['span_px'] for n in names}},ensure_ascii=False))

if __name__=='__main__':main()
