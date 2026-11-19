"""Same-scale comparison using one union crop so long reference hair is not clipped."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import numpy as np
OUT=Path(__file__).resolve().parent
tex=OUT/'staging' if (OUT/'staging').exists() else OUT
names=['Vertin v12','Texas','Zima','Silence'];dirs=['south','east','north'];images={};boxes=[]
font=lambda n:ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',n)
for name in names:
    for di in dirs:
        p=tex/f'Textures/Things/Hair/R99/Vertin_{di}.png' if name=='Vertin v12' else OUT/f'references/{name}_head_{di}.png'
        im=Image.open(p).convert('RGBA');images[name,di]=im
        yy,xx=np.where(np.asarray(im)[:,:,3]>=8);boxes.append([int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)])
crop=(max(0,min(b[0] for b in boxes)-6),max(0,min(b[1] for b in boxes)-6),
      min(256,max(b[2] for b in boxes)+6),min(256,max(b[3] for b in boxes)+6))
w=(crop[2]-crop[0])*2;h=(crop[3]-crop[1])*2;gap=20
s=Image.new('RGB',(48+4*w+3*gap,156+3*h+2*gap+24),'#f7f9fb');d=ImageDraw.Draw(s)
d.text((24,16),'头部画法同尺度参考',font=font(28),fill='#213d50')
d.text((24,60),'共同裁切窗口，保留参考角色完整长发；维尔汀肤色取自自身立绘。',font=font(18),fill='#5a7383')
for col,name in enumerate(names):
    x=24+col*(w+gap);d.text((x,110),name,font=font(21),fill='#285168')
    for row,di in enumerate(dirs):
        im=images[name,di].crop(crop);bg=Image.new('RGBA',im.size,'#e8edf1');db=ImageDraw.Draw(bg)
        for yy in range(0,bg.height,10):
            for xx in range(0,bg.width,10):
                if (xx//10+yy//10)%2==0:db.rectangle((xx,yy,xx+9,yy+9),fill='#dfe6eb')
        bg.alpha_composite(im);s.paste(bg.resize((w,h),Image.Resampling.NEAREST).convert('RGB'),(x,156+row*(h+gap)))
s.save(OUT/'head_style_comparison.png')
print({'common_crop':crop,'scale':2,'size':s.size})
