"""User-selected deterministic light pixel grouping, with immutable shape and facial features.

Always process the recorded pre-pass inputs; do not repeatedly filter the outputs.
Usage: python soft_pixel.py --recipe recipe.json --out NEW_EMPTY_DIRECTORY
"""
from pathlib import Path
from PIL import Image,ImageFilter
import numpy as np
import argparse,json,hashlib,shutil

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def protected_mask(boxes):
    m=np.zeros((256,256),bool)
    for x0,y0,x1,y1 in boxes:m[y0:y1,x0:x1]=True
    return m
def process(im,params,boxes):
    base=np.array(im.convert('RGBA'));rgb=base[:,:,:3].astype(float);alpha=base[:,:,3]
    # A restrained median contribution only in low-contrast opaque interiors.
    median=np.array(Image.fromarray(base[:,:,:3]).filter(ImageFilter.MedianFilter(3))).astype(float)
    flat=(np.max(np.abs(median-rgb),axis=2)<=params['median_local_limit'])&(alpha>=250)
    rubbed=rgb+(median-rgb)*(flat*params['median_mix'])[:,:,None]
    step=params['color_step'];grouped=np.clip(np.rint(rubbed/step)*step,0,255)
    rgba=base.copy();rgba[:,:,:3]=np.rint(grouped).astype(np.uint8)
    # Premultiplied-alpha averaging avoids pulling invisible RGB/background into edges.
    guide=Image.fromarray(rgba).convert('RGBa').resize((params['guide_grid'],params['guide_grid']),Image.Resampling.BOX)
    guide=guide.resize((256,256),Image.Resampling.NEAREST).convert('RGBA')
    g=np.array(guide);grgb=g[:,:,:3].astype(float)
    valid=(alpha>0)&(g[:,:,3]>8)
    strength=np.full((256,256),params['pixel_mix'],float)
    # Keep partial-alpha boundary colors conservative; the alpha itself never changes.
    strength*=.3+.7*(alpha.astype(float)/255)
    exact=protected_mask(boxes)
    feather=np.array(Image.fromarray((exact*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(params['protection_feather_px']))).astype(float)/255
    strength*=1-feather;strength[exact]=0;strength[~valid]=0
    delta=(grgb-rgb)*strength[:,:,None]
    delta=np.clip(delta,-params['max_channel_delta'],params['max_channel_delta'])
    luma=rgb@np.array([.2126,.7152,.0722]);dluma=delta@np.array([.2126,.7152,.0722])
    dark=(luma<params['dark_stroke_luma'])&(dluma>params['max_dark_stroke_lightening'])
    ratio=np.ones((256,256),float)
    ratio[dark]=params['max_dark_stroke_lightening']/dluma[dark]
    delta*=ratio[:,:,None]
    result=base.copy();result[:,:,:3]=np.clip(np.rint(rgb+delta),0,255).astype(np.uint8)
    result[alpha==0]=base[alpha==0];result[exact]=base[exact]
    assert np.array_equal(result[:,:,3],alpha)
    assert np.array_equal(result[exact],base[exact])
    return Image.fromarray(result),exact
def run(recipe_path,out):
    recipe_path=Path(recipe_path).resolve();root=recipe_path.parent;out=Path(out).resolve()
    if out.exists() and any(out.iterdir()):raise ValueError('Choose an empty output directory')
    r=json.loads(recipe_path.read_text(encoding='utf-8'));reports={}
    for key,cfg in r['assets'].items():
        src=(root/cfg['source']).resolve();dst=(out/cfg['relative_path']).resolve()
        assert src.is_relative_to(root) and dst.is_relative_to(out)
        assert sha(src)==cfg['source_sha256'],('source changed',key)
        im=Image.open(src);assert im.mode=='RGBA' and im.size==(256,256)
        output,mask=process(im,r['profiles'][cfg['profile']],cfg['protected_boxes'])
        dst.parent.mkdir(parents=True,exist_ok=True);output.save(dst)
        a=np.array(im);b=np.array(output);visible=a[:,:,3]>0;changed=np.any(a!=b,axis=2)
        assert np.array_equal(a[:,:,3],b[:,:,3])
        assert im.getchannel('A').getbbox()==output.getchannel('A').getbbox()
        assert not changed[~visible].any()
        diagnostic=out/'diagnostics'/key;diagnostic.mkdir(parents=True,exist_ok=True)
        Image.fromarray((mask*255).astype(np.uint8)).save(diagnostic/'protected_features.png')
        Image.fromarray((changed*255).astype(np.uint8)).save(diagnostic/'changed_pixels.png')
        reports[key]={'path':cfg['relative_path'],'source_sha256':sha(src),'output_sha256':sha(dst),'rgba_size':[256,256],
            'alpha_pixel_identical':True,'alpha_bbox':im.getchannel('A').getbbox(),'transparent_rgb_unchanged':True,
            'protected_boxes':cfg['protected_boxes'],'protected_pixels_identical':True,'changed_pixel_count':int(changed.sum()),
            'mean_abs_rgb_delta_over_visible':round(float(np.abs(a[:,:,:3].astype(float)-b[:,:,:3])[visible].mean()),4),
            'max_rgb_channel_delta':int(np.abs(a[:,:,:3].astype(int)-b[:,:,:3].astype(int)).max()),'profile':cfg['profile']}
    items={}
    for key,cfg in r['items'].items():
        src=out/r['assets'][cfg['copy_from']]['relative_path'];dst=out/cfg['relative_path'];dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(src,dst);items[key]={'path':cfg['relative_path'],'sha256':sha(dst),'front_body_sha256':sha(src),'byte_identical_to_front_body':True}
    v={'batch':r['batch'],'method':r['method'],'files':reports,'items':items,'all_alpha_and_placement_unchanged':True,'all_protected_features_pixel_identical':True,'game_tested':False}
    dump(out/'validation.json',v);return v
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--recipe',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();v=run(a.recipe,a.out)
    print(json.dumps({'processed_parts':len(v['files']),'front_body_item_copies':len(v['items']),'alpha_unchanged':True,'protected_features_unchanged':True}))
