"""Format newly imagegen-drawn Sonetto heads; copy retained bodies byte-for-byte."""
from pathlib import Path
from PIL import Image,ImageFilter
import numpy as np
import argparse,json,hashlib,shutil

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def format_one(source,rule,sampling=4):
    data=np.array(Image.open(source).convert('RGBA'))
    # Only discard almost-transparent generation dust; keep the useful original alpha.
    data[data[:,:,3]<8]=0
    im=Image.fromarray(data);scale=rule['uniform_scale']
    ax,ay=rule['source_alignment_anchor'];tx,ty=rule['target_alignment_anchor']
    scaled=im.convert('RGBa').resize((round(im.width*scale*sampling),round(im.height*scale*sampling)),Image.Resampling.LANCZOS).convert('RGBA')
    position=(round((tx-ax*scale)*sampling),round((ty-ay*scale)*sampling))
    canvas=Image.new('RGBA',(256*sampling,256*sampling));canvas.alpha_composite(scaled,position)
    radius=round(rule.get('outer_ink_px',0)*sampling)
    if radius:
        ink=Image.new('RGBA',canvas.size,(12,10,11,0))
        ink.putalpha(canvas.getchannel('A').filter(ImageFilter.MaxFilter(radius*2+1)))
        ink.alpha_composite(canvas);canvas=ink
    canvas=canvas.convert('RGBa').resize((256,256),Image.Resampling.LANCZOS).convert('RGBA')
    data=np.array(canvas);data[data[:,:,3]<8]=0
    return Image.fromarray(data)
def build(recipe_path,out):
    recipe_path=Path(recipe_path).resolve();root=recipe_path.parent;out=Path(out).resolve()
    if out.exists() and any(out.iterdir()):raise ValueError('Choose an empty output directory')
    recipe=json.loads(recipe_path.read_text(encoding='utf-8'));files={}
    for key,rule in recipe['assets'].items():
        src=(root/rule['source']).resolve();dst=(out/rule['relative_path']).resolve()
        assert src.is_relative_to(root) and dst.is_relative_to(out)
        assert sha(src)==rule['source_sha256'],('source changed',key)
        dst.parent.mkdir(parents=True,exist_ok=True)
        if rule['mode']=='copy':shutil.copy2(src,dst)
        else:format_one(src,rule,recipe['supersampling']).save(dst)
        im=Image.open(dst);a=np.array(im.getchannel('A'))
        assert im.mode=='RGBA' and im.size==(256,256)
        assert not a[0,:].any() and not a[-1,:].any() and not a[:,0].any() and not a[:,-1].any(),key
        box=im.getchannel('A').getbbox();assert box
        files[key]={'path':rule['relative_path'],'sha256':sha(dst),'mode':im.mode,'size':list(im.size),'alpha_bbox':box,'copied_byte_identically':rule['mode']=='copy','source_sha256':sha(src),'transparent_border':True}
    assert files['body_south']['sha256']==files['item']['sha256']
    report={'character':'Sonetto','version':recipe['version'],'method':recipe['generation_method'],'files':files,'uniform_head_scaling':True,'head_rotation_degrees':0,'body_item_retained_byte_identically':True,'game_tested':False}
    dump(out/'validation.json',report)
    return report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--recipe',type=Path,default=Path('recipe.json'));p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=build(a.recipe,a.out)
    print(json.dumps({k:{'bbox':v['alpha_bbox'],'retained':v['copied_byte_identically']} for k,v in r['files'].items()}))
