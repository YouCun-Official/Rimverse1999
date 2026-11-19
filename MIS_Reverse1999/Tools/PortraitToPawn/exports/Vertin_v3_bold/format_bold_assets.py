"""Normalize reviewed AI artwork to the original RimWorld 256x256 registration.
This script does not generate artwork or infer unseen views from a portrait.
"""
from pathlib import Path
import argparse,json,math,shutil
import numpy as np
from PIL import Image

def normalize(source,target):
    im=Image.open(source).convert('RGBA')
    a=np.array(im.getchannel('A'));yy,xx=np.where(a>=128)
    if not len(xx) or a.min()!=0:raise ValueError(f'Empty or opaque source: {source}')
    box=(int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1))
    tw=target[2]-target[0];th=target[3]-target[1]
    scale=max((box[2]-box[0])/tw,(box[3]-box[1])/th)
    pad=math.ceil(scale*2)
    cut=im.crop((box[0]-pad,box[1]-pad,box[2]+pad,box[3]+pad))
    pw=round(pad*tw/(box[2]-box[0]));ph=round(pad*th/(box[3]-box[1]))
    tile=cut.convert('RGBa').resize((tw+2*pw,th+2*ph),Image.Resampling.LANCZOS).convert('RGBA')
    canvas=Image.new('RGBA',(256,256))
    canvas.alpha_composite(tile,(target[0]-pw,target[1]-ph))
    pixels=np.array(canvas);pixels[pixels[:,:,3]<=3]=0
    return Image.fromarray(pixels)

def build(recipe_path,out):
    recipe_path=Path(recipe_path).resolve();root=recipe_path.parent;out=Path(out).resolve()
    if out.exists() and any(out.iterdir()):raise ValueError('Output directory must be empty; reviewed exports are never overwritten.')
    out.mkdir(parents=True,exist_ok=True)
    recipe=json.loads(recipe_path.read_text(encoding='utf-8'))
    for asset in recipe['assets']:
        source=(root/asset['source']).resolve()
        destination=(out/asset['relative_path']).resolve()
        if not source.is_relative_to(root) or not destination.is_relative_to(out):raise ValueError('Path escapes package/output')
        destination.parent.mkdir(parents=True,exist_ok=True)
        normalize(source,asset['target_solid_bbox']).save(destination)
    for item,body in recipe['duplicates'].items():
        dest=(out/item).resolve();src=(out/body).resolve()
        if not dest.is_relative_to(out) or not src.is_relative_to(out):raise ValueError('Duplicate path escapes output')
        shutil.copy2(src,dest)
    return len(recipe['assets'])+len(recipe['duplicates'])

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recipe',type=Path,default=Path('bold_recipe.json'))
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps({'files':build(args.recipe,args.out),'out':str(args.out)},ensure_ascii=False))

