from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import hashlib, json, shutil

OUT = Path(__file__).resolve().parent
MOD = Path(r'C:\Users\29232\Desktop\Lannuosprojects\MIS_Lannuosproject\MIS_Reverse1999')
AK = MOD.parent / 'MIS_arknights'
SOURCES = {'Vertin': MOD/'Textures/Things/Hair/R99/Vertin',
           'Texas': AK/'Textures/Things/Hair/Vanguard/Texas',
           'Zima': AK/'Textures/Things/Hair/Vanguard/Zima',
           'Amiya': AK/'Textures/Things/Hair/Caster/Amiya',
           'Exusiai': AK/'Textures/Things/Hair/Sniper/Exusiai',
           'Angelina': AK/'Textures/Things/Hair/Supporter/Angelina',
           'Thorns': AK/'Textures/Things/Hair/Guard/Thorns',
           'Silence': AK/'Textures/Things/Hair/Medic/Silence'}
font=lambda n:ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',n)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(OUT/'inputs').mkdir(parents=True,exist_ok=True)
records=[]
for name,prefix in SOURCES.items():
    for di in ['south','east']:
        src=Path(str(prefix)+'_'+di+'.png'); dst=OUT/'inputs'/f'{name}_{di}.png'
        shutil.copy2(src,dst)
        im=Image.open(dst)
        records.append(dict(name=name,direction=di,source=str(src),local=str(dst.relative_to(OUT)),sha256=sha(src),size=im.size,mode=im.mode))
(OUT/'sources.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'installed_hashes_before.json').write_text(json.dumps({str(p.relative_to(MOD)):sha(p) for p in sorted((MOD/'Textures').rglob('*.png'))},indent=2),encoding='utf-8')
print(json.dumps(records,ensure_ascii=True))

for di in ['south','east']:
    crop=(94,116,170,178);scale=6;w=(crop[2]-crop[0])*scale;h=(crop[3]-crop[1])*scale
    sheet=Image.new('RGB',(40+4*(w+35),120+2*(h+80)), '#f6f8fa');d=ImageDraw.Draw(sheet)
    d.text((24,16),f'眼部定位工作图 · {di} · 6× · 坐标为原始像素',font=font(26),fill='#244052')
    for i,name in enumerate(SOURCES):
        x=24+(i%4)*(w+35);y=110+(i//4)*(h+80)
        im=Image.open(OUT/'inputs'/f'{name}_{di}.png').convert('RGBA')
        bg=Image.new('RGBA',im.size,'#dfe6eb');bg.alpha_composite(im)
        sheet.paste(bg.crop(crop).resize((w,h),Image.Resampling.NEAREST).convert('RGB'),(x,y))
        d.text((x,y-40),name,font=font(24),fill='#244052')
        grid=Image.new('RGBA',sheet.size);gd=ImageDraw.Draw(grid)
        for gx in range(crop[0],crop[2]+1):
            px=x+(gx-crop[0])*scale
            gd.line((px,y,px,y+h),fill=(28,88,125,90 if gx%4==0 else 28),width=1)
            if gx%8==0: d.text((px-10,y-16),str(gx),font=font(10),fill='#244052')
        for gy in range(crop[1],crop[3]+1):
            py=y+(gy-crop[1])*scale
            gd.line((x,py,x+w,py),fill=(28,88,125,90 if gy%4==0 else 28),width=1)
            if gy%8==0: d.text((x-22,py-6),str(gy),font=font(10),fill='#244052')
        sheet=Image.alpha_composite(sheet.convert('RGBA'),grid).convert('RGB');d=ImageDraw.Draw(sheet)
    sheet.save(OUT/f'locate_{di}.png')
