from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np, json, hashlib
from format_assets import build

WORK = Path(__file__).resolve().parent
ASSETS = WORK/'staging' if (WORK/'staging/Textures').exists() else WORK
H = 'Textures/Things/Hair/R99'; B = 'Textures/Things/R99_Agents/Arcanist'
DIRS = [('south','正面'),('east','侧面'),('north','背面')]
font = lambda n: ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', n)
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p, value): p.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def get(name, kind, direction):
    if name == 'Sonetto':
        rel = f'{H}/Sonetto_{direction}.png' if kind == 'head' else f'{B}/Sonetto_Thin_{direction}.png'
        return Image.open(ASSETS/rel).convert('RGBA')
    return Image.open(WORK/'references'/f'{name}_{kind}_{direction}.png').convert('RGBA')

def pawn(name, direction):
    # Shared preview offset and full canvases; no per-character height scaling.
    im = Image.new('RGBA',(256,384))
    im.alpha_composite(get(name,'body',direction),(0,80))
    im.alpha_composite(get(name,'head',direction),(0,15))
    return im

def tile(sheet, im, xy, crop, scale=2):
    im = im.crop(crop); bg = Image.new('RGBA',im.size,'#e9edf1'); dr=ImageDraw.Draw(bg)
    for y in range(0,bg.height,8):
        for x in range(0,bg.width,8):
            if (x//8+y//8)%2 == 0: dr.rectangle((x,y,x+7,y+7),fill='#dfe6eb')
    bg.alpha_composite(im)
    sheet.paste(bg.resize((round(bg.width*scale),round(bg.height*scale)),Image.Resampling.NEAREST).convert('RGB'),xy)

def main():
    for kind,label,crop in [('head','头部',(48,60,216,248)),('body','躯干',(48,80,216,256))]:
        height=130+(crop[3]-crop[1])*2
        sheet=Image.new('RGB',(1096,height),'#f7f9fb');dr=ImageDraw.Draw(sheet)
        dr.text((24,16),f'十四行诗 Sonetto · {label}三视图',font=font(27),fill='#213d50')
        for col,(direction,title) in enumerate(DIRS):
            x=24+col*360;dr.text((x,64),title,font=font(20),fill='#5a7383')
            tile(sheet,get('Sonetto',kind,direction),(x,100),crop)
        sheet.save(WORK/f'{kind}s_three_views.png')
    sheet=Image.new('RGB',(1096,712),'#f7f9fb');dr=ImageDraw.Draw(sheet)
    dr.text((24,16),'十四行诗 Sonetto · 完整人物三视图',font=font(28),fill='#213d50')
    for col,(direction,title) in enumerate(DIRS):
        x=24+col*360;dr.text((x,64),title,font=font(20),fill='#5a7383')
        tile(sheet,pawn('Sonetto',direction),(x,100),(48,60,216,340))
    dr.text((24,681),'表情参照本地立绘：认真、平静、略带疑问；长发单独保留在头部层。',font=font(18),fill='#5a7383')
    sheet.save(WORK/'three_views_final.png')

    names=['Sonetto','Vertin_v13','Texas','Silence']
    for kind in ['head','body','pawn']:
        images={};boxes=[]
        for name in names:
            for direction,_ in DIRS:
                im=pawn(name,direction) if kind=='pawn' else get(name,kind,direction)
                images[name,direction]=im
                boxes.append(im.getchannel('A').point(lambda a:255 if a>=8 else 0).getbbox())
        crop=(max(0,min(b[0] for b in boxes)-6),max(0,min(b[1] for b in boxes)-6),min(256,max(b[2] for b in boxes)+6),min(384 if kind=='pawn' else 256,max(b[3] for b in boxes)+6))
        w,h=(crop[2]-crop[0])*2,(crop[3]-crop[1])*2
        sheet=Image.new('RGB',(48+4*w+60,152+3*h+60),'#f7f9fb');dr=ImageDraw.Draw(sheet)
        title={'head':'头部','body':'躯干','pawn':'完整人物'}[kind]
        dr.text((24,16),f'{title}三视图 · 同像素比例比较',font=font(28),fill='#213d50')
        dr.text((24,60),'统一 2×、共同裁切范围；Vertin 为尺寸基准，Arknights 为画风参照。',font=font(18),fill='#5a7383')
        for col,name in enumerate(names):
            x=24+col*(w+20);dr.text((x,108),name,font=font(21),fill='#285168')
            for row,(direction,_) in enumerate(DIRS): tile(sheet,images[name,direction],(x,152+row*(h+20)),crop)
        sheet.save(WORK/f'{kind}_style_comparison.png')

    sheet=Image.new('RGB',(950,495),'#eef1f4');dr=ImageDraw.Draw(sheet)
    dr.text((14,8),'原尺寸画布 / 右侧 50% 缩小检查',font=font(21),fill='#213d50')
    for col,(direction,title) in enumerate(DIRS):
        im=pawn('Sonetto',direction);bg=Image.new('RGBA',im.size,'#e4e9ed');bg.alpha_composite(im)
        sheet.paste(bg.convert('RGB'),(col*256,50));small=bg.resize((128,192),Image.Resampling.LANCZOS)
        sheet.paste(small.crop((0,24,128,176)).convert('RGB'),(792,col*144+38))
    sheet.save(WORK/'native_and_reduced.png')

    sheet=Image.new('RGB',(1100,610),'#f7f9fb');dr=ImageDraw.Draw(sheet)
    dr.text((24,16),'表情与身份核对 · 本地立绘为主',font=font(27),fill='#213d50')
    original=Image.open(WORK/'references/sonetto_face_reference.png').convert('RGBA').resize((370,320),Image.Resampling.NEAREST)
    bg=Image.new('RGBA',original.size,'#e4e9ed');bg.alpha_composite(original);sheet.paste(bg.convert('RGB'),(24,95))
    dr.text((24,60),'主立绘面部（仅放大）',font=font(20),fill='#5a7383')
    for i,(direction,title,crop) in enumerate([('south','正面',(104,130,155,181)),('east','侧面',(124,130,176,184))]):
        x=430+i*330;dr.text((x,60),title+' · 原生像素 5×',font=font(20),fill='#5a7383')
        tile(sheet,get('Sonetto','head',direction),(x,95),crop,5)
    dr.text((24,465),'保留灰绿色瞳色、克制的眉眼、微张的小嘴；没有新增雀斑或伤痕。',font=font(22),fill='#285168')
    dr.text((24,510),'发色、格纹发带、侧辫与金色发夹按原设；头部直立，表情不随侧身前倾改变。',font=font(20),fill='#5a7383')
    sheet.save(WORK/'expression_reference_comparison.png')

    checks={}
    for p in sorted((ASSETS/'Textures').rglob('*.png')):
        rel=p.relative_to(ASSETS).as_posix();im=Image.open(p);a=np.array(im);alpha=a[:,:,3]
        assert im.mode=='RGBA' and im.size==(256,256)
        assert not any(np.any(edge) for edge in [alpha[0],alpha[-1],alpha[:,0],alpha[:,-1]]),rel
        assert not np.any(a[alpha==0,:3]),rel
        yy,xx=np.where(alpha>=128)
        checks[rel]={'sha256':sha(p),'solid_bbox':[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)],'format':'256x256 RGBA PNG','clear_canvas_border':True}
    assert len(checks)==7
    assert sha(ASSETS/B/'Sonetto.png')==sha(ASSETS/B/'Sonetto_Thin_south.png')
    for stem in [f'{H}/Sonetto',f'{B}/Sonetto_Thin']:
        assert len({sha(ASSETS/f'{stem}_{direction}.png') for direction,_ in DIRS})==3
    build(WORK/'recipe.json',WORK/'reproduction_check',allow_overwrite=True)
    for rel,record in checks.items():assert sha(WORK/'reproduction_check'/rel)==record['sha256']
    validation={'date':'2026-11-08','checks':checks,'format_reproduction_passed':True,'head_rotation_degrees':0,'preview_head_offset':[0,-65],'size_baseline':'Vertin_v13_arknights_skin','visual_review':'pending','game_tested':False,'back_view_provenance':'Conservative reconstruction; no authoritative orthographic rear sheet found.'}
    dump(WORK/'validation.json',validation)
    print(json.dumps({'asset_count':len(checks),'bounds':{k:v['solid_bbox'] for k,v in checks.items()},'reproduction_passed':True},ensure_ascii=True))

if __name__=='__main__':main()
