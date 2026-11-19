"""Format reviewed artwork to native RimWorld sprites; recipe records every transform."""
from pathlib import Path
import argparse,json,math,shutil
import numpy as np
from PIL import Image,ImageFilter

def normalize(source,target,outer_ink_px=0.5,row_warp=None):
    im=Image.open(source).convert('RGBA');data=np.array(im);a=data[:,:,3]
    # Remove low-alpha generator halos before resampling; resampling rebuilds a clean AA fringe.
    data[:,:,3]=np.clip((a.astype(np.float32)-96)*255/159,0,255).astype(np.uint8)
    data[data[:,:,3]==0]=0;im=Image.fromarray(data)
    yy,xx=np.where(data[:,:,3]>=128)
    if not len(xx):raise ValueError(f'Empty subject: {source}')
    box=(int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1))
    tw=target[2]-target[0];th=target[3]-target[1];S=4
    padx=math.ceil((box[2]-box[0])/tw*3);pady=math.ceil((box[3]-box[1])/th*3)
    crop=im.crop((box[0]-padx,box[1]-pady,box[2]+padx,box[3]+pady))
    crop=crop.convert('RGBa').resize(((tw+6)*S,(th+6)*S),Image.Resampling.LANCZOS).convert('RGBA')
    canvas=Image.new('RGBA',(256*S,256*S));canvas.alpha_composite(crop,((target[0]-3)*S,(target[1]-3)*S))
    if row_warp:
        source=np.array(canvas.convert('RGBa'));dest=np.zeros_like(source)
        anchors=np.array(row_warp,float);coord=np.arange(256*S,dtype=float)/S
        shifts=np.interp(coord,anchors[:,0],anchors[:,1])*S
        for y,shift in enumerate(shifts):
            x=np.arange(256*S)-shift
            lo=np.floor(x).astype(int);hi=lo+1;frac=(x-lo)[:,None]
            ok=(lo>=0)&(hi<256*S)
            dest[y,ok]=np.rint(source[y,lo[ok]]*(1-frac[ok])+source[y,hi[ok]]*frac[ok]).astype('uint8')
        canvas=Image.fromarray(dest,'RGBa').convert('RGBA')
    if outer_ink_px:
        radius=round(outer_ink_px*S)
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
        if not src.is_relative_to(root) or not dest.is_relative_to(out):raise ValueError('Unsafe path')
        dest.parent.mkdir(parents=True,exist_ok=True)
        normalize(src,r['target_solid_bbox'],r.get('outer_ink_px',.5),r.get('row_warp')).save(dest)
    item=out/'Textures/Things/R99_Agents/Arcanist/Vertin.png'
    shutil.copy2(item.with_name('Vertin_Thin_south.png'),item)
    return 7
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--recipe',type=Path,default=Path('recipe.json'));p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();print(build(a.recipe,a.out))

