"""Reproducible, stratified random skin-color sampling; does not recolor artwork."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageCms
import io,json,hashlib
import numpy as np

OUT=Path(__file__).resolve().parent
portrait=OUT/'references/vertin_original.webp'
im=Image.open(portrait)
icc=im.info.get('icc_profile')
if icc:
    im=ImageCms.profileToProfile(im,ImageCms.ImageCmsProfile(io.BytesIO(icc)),ImageCms.createProfile('sRGB'),outputMode='RGBA')
else:im=im.convert('RGBA')
a=np.asarray(im)
regions=[('额头', [1107,350,1130,376]),('鼻梁侧皮肤',[1090,430,1122,459]),
         ('面颊',[1140,470,1173,507]),('下颊',[1176,520,1193,538])]
seed=20261105;size=7;radius=size//2;rng=np.random.default_rng(seed)
samples=[];selected=[]
for label,(x0,y0,x1,y1) in regions:
    candidates=[]
    for y in range(y0+radius,y1-radius):
        for x in range(x0+radius,x1-radius):
            patch=a[y-radius:y+radius+1,x-radius:x+radius+1]
            if np.all(patch[:,:,3]>=250) and float(np.max(patch[:,:,:3].std(axis=(0,1))))<12:
                candidates.append((x,y))
    rng.shuffle(candidates);count=0
    for x,y in candidates:
        box=[x-radius,y-radius,x+radius+1,y+radius+1]
        if any(not (box[2]<=b[0] or b[2]<=box[0] or box[3]<=b[1] or b[3]<=box[1]) for b in selected):continue
        patch=a[box[1]:box[3],box[0]:box[2],:3].astype(float)
        mean=patch.mean(axis=(0,1));rgb=np.rint(mean).astype(int).tolist()
        samples.append({'id':len(samples)+1,'region':label,'box_xyxy_exclusive':box,'pixels':size*size,
                        'mean_srgb_unrounded':mean.tolist(),'rgb':rgb,'hex':'#'+''.join(f'{v:02X}' for v in rgb)})
        selected.append(box);count+=1
        if count==2:break
    assert count==2,label
mean=np.mean([s['mean_srgb_unrounded'] for s in samples],axis=0)
rgb=np.rint(mean).astype(int).tolist();color='#'+''.join(f'{v:02X}' for v in rgb)
source_current=Image.open(OUT/'inputs/head_south_v11.png').convert('RGBA')
current_rois=[(570,630,630,680),(475,835,535,880),(690,835,750,880)]
means=[np.asarray(source_current)[b[1]:b[3],b[0]:b[2],:3].astype(float).mean(axis=(0,1)) for b in current_rois]
old=np.rint(np.mean(means,axis=0)).astype(int).tolist();oldhex='#'+''.join(f'{v:02X}' for v in old)
record={'source':'references/vertin_original.webp','source_sha256':hashlib.sha256(portrait.read_bytes()).hexdigest(),
    'original_size':list(im.size),'color_space':'sRGB','profile_handling':'embedded ICC converted to sRGB' if icc else 'no embedded ICC; assumed sRGB',
    'seed':seed,'patch_size':[size,size],'sampling':'two non-overlapping random blocks per manually verified face-skin region; no brightness/hue gating',
    'eligibility':{'alpha_min':250,'max_channel_std_lt':12,'excluded':'hair, eyes/eyebrows, nose/lip marks, outlines, specular rim light, deep shadow, background'},
    'regions':[{'name':label,'box':box} for label,box in regions],'samples':samples,
    'aggregation':'equal arithmetic mean of the eight unrounded block means in encoded sRGB; round only final color',
    'base_srgb_unrounded':mean.tolist(),'base_rgb':rgb,'base_hex':color,
    'previous_head_reference':{'part':'head_south source_art','skin_rois':current_rois,'mean_rgb':old,'mean_hex':oldhex},
    'scope':'Base color from this portrait; source lighting retained. Not an estimate of illumination-independent physical skin reflectance.'}
(OUT/'skin_sampling.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
font=lambda n:ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',n)
s=Image.new('RGB',(1220,850),'#f6f8fa');d=ImageDraw.Draw(s)
d.text((24,16),'肤色取样 · 维尔汀原始立绘',font=font(29),fill='#213e50')
d.text((24,62),'4 处面部皮肤区域 × 各随机 2 块；每块 7×7 原始像素，固定随机种子。',font=font(18),fill='#5b7383')
crop=(1060,330,1220,555);face=im.crop(crop);bg=Image.new('RGBA',face.size,'#e2e8ee');bg.alpha_composite(face)
view=bg.resize((480,675),Image.Resampling.NEAREST);dv=ImageDraw.Draw(view)
for sample in samples:
    x0,y0,x1,y1=sample['box_xyxy_exclusive'];rect=((x0-crop[0])*3,(y0-crop[1])*3,(x1-crop[0])*3,(y1-crop[1])*3)
    dv.rectangle(rect,outline='#1a84b3',width=2)
    dv.text((rect[0]-1,rect[1]-22),str(sample['id']),font=font(18),fill='#064469',stroke_width=1,stroke_fill='#f4f8fa')
s.paste(view.convert('RGB'),(24,116))
for i,sample in enumerate(samples):
    x=540+(i%2)*324;y=119+(i//2)*96
    d.rectangle((x,y,x+72,y+62),fill=sample['hex'],outline='#bac7d0',width=1)
    d.text((x+85,y+3),f"{sample['id']} · {sample['region']}",font=font(19),fill='#294e63')
    d.text((x+85,y+33),sample['hex'],font=font(18),fill='#5b7383')
for x,title,c in [(540,'旧版头部原稿肤色',oldhex),(865,'原画采样平均基准',color)]:
    d.text((x,534),title,font=font(21),fill='#294e63');d.rectangle((x,574,x+286,711),fill=c,outline='#b6c4ce',width=1)
    d.text((x,727),c,font=font(24),fill='#294e63')
d.text((24,817),'样本只取面部皮肤；保留原画色调，避开五官、头发、强高光与深阴影。',font=font(18),fill='#5b7383')
s.save(OUT/'skin_sampling_board.png')
swatch=Image.new('RGB',(512,512),tuple(rgb));swatch.save(OUT/'references/skin_base_swatch.png')

# Current native heads with a coordinate grid for choosing clean verification patches.
s=Image.new('RGB',(1410,450),'#f6f8fa');d=ImageDraw.Draw(s)
for i,di in enumerate(['south','east','north']):
    src=Image.open(OUT/f'inputs/native_head_{di}_v11.png').convert('RGBA')
    bg=Image.new('RGBA',src.size,'#e2e8ee');bg.alpha_composite(src)
    tile=bg.crop((95,120,175,185)).resize((400,325),Image.Resampling.NEAREST);dt=ImageDraw.Draw(tile)
    for x in range(100,175,5):
        px=(x-95)*5;dt.line((px,0,px,324),fill='#7093a2',width=1);dt.text((px+1,0),str(x),font=font(10),fill='#204456')
    for y in range(125,185,5):
        py=(y-120)*5;dt.line((0,py,399,py),fill='#7093a2',width=1);dt.text((0,py+1),str(y),font=font(10),fill='#204456')
    x=20+i*465;d.text((x,14),di,font=font(20),fill='#294e63');s.paste(tile.convert('RGB'),(x,50))
s.save(OUT/'references/head_skin_grid.png')
print(json.dumps({'samples':len(samples),'base_rgb':rgb,'base_hex':color,'previous_front_skin_reference_rgb':old,'previous_front_skin_reference_hex':oldhex},ensure_ascii=True))
