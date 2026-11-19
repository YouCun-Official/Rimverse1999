"""Literal eye-pixel transfer requested by the user; no generated or drawn eyes.

The donor is an existing local texture. Only its iris colors are remapped;
neutral eyelid/sclera/highlight pixels are copied. All other target pixels are
protected. Run --recipe transfer_recipe.json --out an_empty_directory.
"""
from pathlib import Path
from PIL import Image
import numpy as np,json,argparse,hashlib

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rows_mask(rows):
    mask=np.zeros((256,256),bool)
    for y,(left,right) in rows.items():mask[int(y),int(left):int(right)+1]=True
    return mask
def build(recipe_path,out):
    recipe_path=Path(recipe_path).resolve();root=recipe_path.parent;out=Path(out).resolve()
    if out.exists() and any(out.iterdir()):raise ValueError('Use an empty output directory')
    recipe=json.loads(recipe_path.read_text(encoding='utf-8'))
    base=np.array(Image.open(root/recipe['base']).convert('RGBA'))
    donor=np.array(Image.open(root/recipe['donor']).convert('RGBA'))
    assert base.shape==donor.shape==(256,256,4)
    samples=np.array([base[y,x,:3] for x,y in recipe['target_iris_sample_points']],float)
    iris_mid=np.median(samples,axis=0)
    iris_luma=float(iris_mid @ np.array([.2126,.7152,.0722]))
    box=recipe['local_skin_repair_sample_box'];patch=base[box[1]:box[3],box[0]:box[2],:3]
    # This restores only the previous eye markings; it is not a skin-palette change.
    skin=np.median(patch.reshape(-1,3),axis=0)
    result=base.copy();changed_allowed=np.zeros((256,256),bool);records={};raw_layers={}
    protected=np.zeros((256,256),bool);protected[:140,:]=True;protected[151:,:]=True
    # Existing left hair edge remains over the eye, as in the base texture.
    for y,left in [(140,112),(141,112),(142,112),(143,111),(144,111),(145,111)]:protected[y,:left]=True
    for eye,config in recipe['eyes'].items():
        extraction=rows_mask(config['source_rows'])
        dx,dy=config['translation'];erase=rows_mask(config['erase_rows'])&~protected
        layer=np.zeros_like(base);original_layer=np.zeros_like(base);rgb_kept=0;recolored=0;skipped_skin=0;mapping=[]
        for sy,sx in zip(*np.where(extraction)):
            tx,ty=int(sx+dx),int(sy+dy)
            if not (0<=tx<256 and 0<=ty<256) or protected[ty,tx]:continue
            rgb=donor[sy,sx,:3].astype(float);r,g,b=rgb
            # Reject the donor's peach skin around the aperture; preserve all actual eye components.
            if r-g>16 and r-b>18:
                skipped_skin+=1;continue
            output=rgb.copy();is_iris=(g-r>6 and b-r>3 and r<200 and g>25)
            if is_iris:
                luminance=float(rgb @ np.array([.2126,.7152,.0722]))
                output=np.clip(iris_mid*(luminance/iris_luma),0,255);recolored+=1
            else:rgb_kept+=1
            layer[ty,tx,:3]=np.rint(output).astype(np.uint8);layer[ty,tx,3]=255
            original_layer[ty,tx]=donor[sy,sx]
            erase[ty,tx]=True
            mapping.append({'source':[int(sx),int(sy)],'target':[tx,ty],'iris_recolored':bool(is_iris)})
        result[erase,:3]=np.rint(skin).astype(np.uint8)
        active=layer[:,:,3]>0;result[active,:3]=layer[active,:3]
        changed_allowed|=erase
        raw_layers[eye]=(original_layer,layer)
        records[eye]={'donor_pixels_copied_without_rgb_change':rgb_kept,'iris_pixels_recolored':recolored,'donor_skin_pixels_omitted':skipped_skin,'native_translation':[dx,dy],'mapping':mapping}
    assert np.array_equal(result[:,:,3],base[:,:,3])
    assert np.array_equal(result[~changed_allowed],base[~changed_allowed])
    assert np.array_equal(result[:140],base[:140]) and np.array_equal(result[151:],base[151:])
    destination=(out/recipe['output']).resolve();assert destination.is_relative_to(out)
    destination.parent.mkdir(parents=True,exist_ok=True);Image.fromarray(result).save(destination)
    diagnostics=out/'diagnostics';diagnostics.mkdir(parents=True,exist_ok=True)
    Image.fromarray((changed_allowed*255).astype(np.uint8)).save(diagnostics/'allowed_eye_mask.png')
    changed=np.any(result!=base,axis=2);Image.fromarray((changed*255).astype(np.uint8)).save(diagnostics/'actual_changed_pixels.png')
    for eye,(original,layer) in raw_layers.items():
        Image.fromarray(original).save(diagnostics/f'{eye}_donor_pixels_at_target.png')
        Image.fromarray(layer).save(diagnostics/f'{eye}_recolored_pixels_at_target.png')
    y,x=np.where(changed)
    report={'method':recipe['method'],'donor_scale':[1,1],'target_iris_mid_rgb':np.rint(iris_mid).astype(int).tolist(),'local_eye_background_repair_rgb':np.rint(skin).astype(int).tolist(),'changed_pixel_count':int(changed.sum()),'changed_bbox':[int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)],'outside_eye_mask_byte_identical':True,'alpha_byte_identical':True,'brows_above_y140_unchanged':True,'nose_mouth_and_freckles_from_y151_unchanged':True,'source_sha256':{'base':digest(root/recipe['base']),'donor':digest(root/recipe['donor'])},'output_sha256':digest(destination),'eyes':records}
    (out/'transfer_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return report
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--recipe',type=Path,default=Path('transfer_recipe.json'));parser.add_argument('--out',type=Path,required=True);a=parser.parse_args();r=build(a.recipe,a.out)
    print(json.dumps({k:r[k] for k in ['target_iris_mid_rgb','changed_pixel_count','changed_bbox','outside_eye_mask_byte_identical']},ensure_ascii=True))
