"""Reproduce transparent Sonetto pawn textures from reviewed generated source art."""
from pathlib import Path
import argparse, json, shutil, math
import numpy as np
from PIL import Image, ImageFilter

def format_one(source, rule):
    im = Image.open(source).convert('RGBA')
    data = np.array(im)
    data[:, :, 3] = np.clip((data[:, :, 3].astype(float) - 96) * 255 / 159, 0, 255).astype('uint8')
    data[data[:, :, 3] == 0] = 0
    im = Image.fromarray(data)
    yy, xx = np.where(data[:, :, 3] >= 128)
    box = [int(xx.min()), int(yy.min()), int(xx.max() + 1), int(yy.max() + 1)]
    S = 4
    canvas = Image.new('RGBA', (256*S, 256*S))
    if rule.get('transform_mode') == 'landmark':
        # Fit the anatomical anchor, not all hair/accessory extensions.
        sx0, sy0, sx1, sy1 = rule['source_anchor_box']
        tx0, ty0, tx1, ty1 = rule['target_anchor_box']
        scale_x = (tx1-tx0)/(sx1-sx0)
        scale_y = (ty1-ty0)/(sy1-sy0)
        if rule.get('uniform_scale'):
            scale_y = scale_x
        anchor_x, anchor_y = rule.get('source_alignment_anchor', [sx0, sy0])
        target_x, target_y = rule.get('target_alignment_anchor', [tx0, ty0])
        size = (round(im.width*scale_x*S), round(im.height*scale_y*S))
        scaled = im.convert('RGBa').resize(size, Image.Resampling.LANCZOS).convert('RGBA')
        pos = (round((target_x-anchor_x*scale_x)*S), round((target_y-anchor_y*scale_y)*S))
        canvas.alpha_composite(scaled, pos)
    else:
        target = rule['target_solid_bbox']
        tw, th = target[2]-target[0], target[3]-target[1]
        padx = math.ceil((box[2]-box[0])/tw*3)
        pady = math.ceil((box[3]-box[1])/th*3)
        crop = im.crop((box[0]-padx, box[1]-pady, box[2]+padx, box[3]+pady))
        crop = crop.convert('RGBa').resize((round((tw+6)*S), round((th+6)*S)), Image.Resampling.LANCZOS).convert('RGBA')
        canvas.alpha_composite(crop, (round((target[0]-3)*S), round((target[1]-3)*S)))
    if rule.get('row_warp') or rule.get('row_scale'):
        src = np.array(canvas.convert('RGBa')); dest = np.zeros_like(src)
        ys = np.arange(256*S)/S
        shifts = np.zeros(256*S)
        if rule.get('row_warp'):
            anchors = np.array(rule['row_warp'], float)
            shifts = np.interp(ys, anchors[:, 0], anchors[:, 1])*S
        scales = np.ones(256*S); centers = np.full(256*S, 128*S)
        if rule.get('row_scale'):
            anchors = np.array(rule['row_scale'], float)
            scales = np.interp(ys, anchors[:,0], anchors[:,1])
            centers = np.interp(ys, anchors[:,0], anchors[:,2])*S
        for y, shift in enumerate(shifts):
            x = (np.arange(256*S)-centers[y]-shift)/scales[y]+centers[y]
            lo = np.floor(x).astype(int); hi = lo+1; f = (x-lo)[:, None]
            ok = (lo >= 0) & (hi < 256*S)
            dest[y, ok] = np.rint(src[y, lo[ok]]*(1-f[ok]) + src[y, hi[ok]]*f[ok]).astype('uint8')
        canvas = Image.fromarray(dest, 'RGBa').convert('RGBA')
    ink = rule.get('outer_ink_px', 0.5)
    if ink:
        radius = round(ink*S)
        alpha = canvas.getchannel('A').filter(ImageFilter.MaxFilter(radius*2+1))
        outline = Image.new('RGBA', canvas.size, (8, 7, 10, 0))
        outline.putalpha(alpha); outline.alpha_composite(canvas); canvas = outline
    canvas = canvas.convert('RGBa').resize((256, 256), Image.Resampling.LANCZOS).convert('RGBA')
    data = np.array(canvas); data[data[:, :, 3] < 8] = 0
    return Image.fromarray(data)

def build(recipe_path, out, allow_overwrite=False):
    recipe_path = Path(recipe_path).resolve(); root = recipe_path.parent; out = Path(out).resolve()
    if out.exists() and any(out.iterdir()) and not allow_overwrite:
        raise ValueError('Choose an empty output directory')
    recipe = json.loads(recipe_path.read_text(encoding='utf-8'))
    for key, rule in recipe['assets'].items():
        src = (root/rule['source']).resolve(); dst = (out/rule['relative_path']).resolve()
        if not src.is_relative_to(root) or not dst.is_relative_to(out): raise ValueError('Unsafe path')
        dst.parent.mkdir(parents=True, exist_ok=True)
        format_one(src, rule).save(dst)
    item = (out/recipe['item_relative_path']).resolve()
    if not item.is_relative_to(out): raise ValueError('Unsafe item path')
    shutil.copy2(out/recipe['assets']['body_south']['relative_path'], item)
    return 7

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--recipe', type=Path, default=Path('recipe.json'))
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args(); print(build(args.recipe, args.out))
