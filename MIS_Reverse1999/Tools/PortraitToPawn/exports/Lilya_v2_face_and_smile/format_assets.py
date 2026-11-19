"""AI-assisted texture formatting; artwork is generated separately, not painted here.

The recipe records source-to-canvas placement, optional row shifts and added outer
ink. Reproduce reviewed assets with --recipe recipe.json --out an_empty_directory.
"""
from pathlib import Path
import argparse, json, math, shutil
import numpy as np
from PIL import Image, ImageFilter

def normalize(source, target, outer_ink_px=0.5, row_warp=None):
    im = Image.open(source).convert('RGBA')
    data = np.array(im)
    alpha = data[:, :, 3]
    data[:, :, 3] = np.clip((alpha.astype(np.float32)-96)*255/159, 0, 255).astype(np.uint8)
    data[data[:, :, 3] == 0] = 0
    im = Image.fromarray(data)
    yy, xx = np.where(data[:, :, 3] >= 128)
    if not len(xx):
        raise ValueError(f'Empty source: {source}')
    box = (int(xx.min()), int(yy.min()), int(xx.max()+1), int(yy.max()+1))
    tw, th = target[2]-target[0], target[3]-target[1]
    sample = 4
    padx, pady = math.ceil((box[2]-box[0])/tw*3), math.ceil((box[3]-box[1])/th*3)
    crop = im.crop((box[0]-padx, box[1]-pady, box[2]+padx, box[3]+pady))
    size = (round((tw+6)*sample), round((th+6)*sample))
    crop = crop.convert('RGBa').resize(size, Image.Resampling.LANCZOS).convert('RGBA')
    canvas = Image.new('RGBA', (256*sample, 256*sample))
    canvas.alpha_composite(crop, (round((target[0]-3)*sample), round((target[1]-3)*sample)))
    if row_warp:
        premul = np.array(canvas.convert('RGBa'))
        dest = np.zeros_like(premul)
        anchors = np.array(row_warp, float)
        coord = np.arange(256*sample, dtype=float)/sample
        shifts = np.interp(coord, anchors[:, 0], anchors[:, 1])*sample
        for y, shift in enumerate(shifts):
            x = np.arange(256*sample)-shift
            lo = np.floor(x).astype(int)
            hi = lo+1
            frac = (x-lo)[:, None]
            ok = (lo >= 0) & (hi < 256*sample)
            dest[y, ok] = np.rint(premul[y, lo[ok]]*(1-frac[ok])+premul[y, hi[ok]]*frac[ok]).astype(np.uint8)
        canvas = Image.fromarray(dest, 'RGBa').convert('RGBA')
    if outer_ink_px:
        radius = round(outer_ink_px*sample)
        outline_alpha = canvas.getchannel('A').filter(ImageFilter.MaxFilter(radius*2+1))
        ink = Image.new('RGBA', canvas.size, (8, 7, 10, 0))
        ink.putalpha(outline_alpha)
        ink.alpha_composite(canvas)
        canvas = ink
    canvas = canvas.convert('RGBa').resize((256, 256), Image.Resampling.LANCZOS).convert('RGBA')
    result = np.array(canvas)
    result[result[:, :, 3] < 8] = 0
    return Image.fromarray(result)

def build(recipe_path, out, allow_overwrite=False):
    recipe_path, out = Path(recipe_path).resolve(), Path(out).resolve()
    root = recipe_path.parent
    if out.exists() and any(out.iterdir()) and not allow_overwrite:
        raise ValueError('Choose an empty output directory')
    recipe = json.loads(recipe_path.read_text(encoding='utf-8'))
    if recipe['canvas'] != [256, 256]:
        raise ValueError('This formatter exports 256x256 PNG only')
    for key, asset in recipe['assets'].items():
        source, destination = (root/asset.get('copy_from',asset['source'])).resolve(), (out/asset['relative_path']).resolve()
        if not source.is_relative_to(root) or not destination.is_relative_to(out):
            raise ValueError('Unsafe asset path')
        destination.parent.mkdir(parents=True, exist_ok=True)
        if 'copy_from' in asset:
            shutil.copy2(source,destination)
        else:
            normalize(source, asset['target_solid_bbox'], asset.get('outer_ink_px', 0.5), asset.get('row_warp')).save(destination)
    item = (out/recipe['item_copy']['relative_path']).resolve()
    front = (out/recipe['assets'][recipe['item_copy']['from_asset']]['relative_path']).resolve()
    if not item.is_relative_to(out):
        raise ValueError('Unsafe item path')
    item.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(front, item)
    return len(recipe['assets'])+1

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recipe', type=Path, default=Path('recipe.json'))
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(build(args.recipe, args.out))
