"""Reproduce reviewed X artwork as transparent 256px RimWorld texture parts."""
from pathlib import Path
import argparse, json, math, shutil
import numpy as np
from PIL import Image, ImageFilter

def normalize(source, target, outer_ink_px=0.5, row_warp=None):
    data=np.array(Image.open(source).convert('RGBA'))
    data[:,:,3]=np.clip((data[:,:,3].astype(np.float32)-96)*255/159,0,255).astype(np.uint8)
    data[data[:,:,3]==0]=0
    im=Image.fromarray(data)
    yy,xx=np.where(data[:,:,3]>=128)
    if not len(xx):raise ValueError(f'Empty artwork: {source}')
    bbox=(int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1))
    tw,th=target[2]-target[0],target[3]-target[1]
    scale=4
    px=math.ceil((bbox[2]-bbox[0])/tw*3)
    py=math.ceil((bbox[3]-bbox[1])/th*3)
    crop=im.crop((bbox[0]-px,bbox[1]-py,bbox[2]+px,bbox[3]+py))
    crop=crop.convert('RGBa').resize((round((tw+6)*scale),round((th+6)*scale)),Image.Resampling.LANCZOS).convert('RGBA')
    canvas=Image.new('RGBA',(256*scale,256*scale))
    canvas.alpha_composite(crop,(round((target[0]-3)*scale),round((target[1]-3)*scale)))
    if row_warp:
        arr=np.array(canvas.convert('RGBa'));dest=np.zeros_like(arr)
        anchors=np.asarray(row_warp,float)
        shifts=np.interp(np.arange(256*scale,dtype=float)/scale,anchors[:,0],anchors[:,1])*scale
        for y,shift in enumerate(shifts):
            x=np.arange(256*scale)-shift
            lo=np.floor(x).astype(int);hi=lo+1;fraction=(x-lo)[:,None]
            valid=(lo>=0)&(hi<256*scale)
            dest[y,valid]=np.rint(arr[y,lo[valid]]*(1-fraction[valid])+arr[y,hi[valid]]*fraction[valid]).astype('uint8')
        canvas=Image.fromarray(dest,'RGBa').convert('RGBA')
    if outer_ink_px:
        radius=round(outer_ink_px*scale)
        alpha=canvas.getchannel('A').filter(ImageFilter.MaxFilter(radius*2+1))
        ink=Image.new('RGBA',canvas.size,(8,7,10,0));ink.putalpha(alpha);ink.alpha_composite(canvas);canvas=ink
    canvas=canvas.convert('RGBa').resize((256,256),Image.Resampling.LANCZOS).convert('RGBA')
    data=np.array(canvas);data[data[:,:,3]<8]=0
    return Image.fromarray(data)

def build(recipe_path,out,allow_overwrite=False):
    recipe_path=Path(recipe_path).resolve();root=recipe_path.parent;out=Path(out).resolve()
    if out.exists() and any(out.iterdir()) and not allow_overwrite:raise ValueError('Choose an empty output directory')
    recipe=json.loads(recipe_path.read_text(encoding='utf-8'))
    for key,r in recipe['assets'].items():
        src=(root/r['source']).resolve();dest=(out/r['relative_path']).resolve()
        if not src.is_relative_to(root) or not dest.is_relative_to(out):raise ValueError('Unsafe asset path')
        dest.parent.mkdir(parents=True,exist_ok=True)
        normalize(src,r['target_solid_bbox'],r.get('outer_ink_px',0.5),r.get('row_warp')).save(dest)
    item=(out/recipe['item_relative_path']).resolve()
    front=(out/recipe['assets']['body_south']['relative_path']).resolve()
    if not item.is_relative_to(out):raise ValueError('Unsafe item path')
    item.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(front,item)
    return len(recipe['assets'])+1

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recipe',type=Path,default=Path('recipe.json'))
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();print(build(args.recipe,args.out))
