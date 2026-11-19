"""Deterministic 4x formatting of reviewed Regulus artwork, never generates art."""
from pathlib import Path
import argparse, json, math, shutil
import numpy as np
from PIL import Image, ImageFilter

def normalize(source, target, outer_ink_px=0.5, row_warp=None):
    im = Image.open(source).convert('RGBA')
    data = np.array(im)
    alpha = data[:, :, 3]
    data[:, :, 3] = np.clip((alpha.astype(np.float32) - 96) * 255 / 159, 0, 255).astype(np.uint8)
    data[data[:, :, 3] == 0] = 0
    im = Image.fromarray(data)
    yy, xx = np.where(data[:, :, 3] >= 128)
    if not len(xx):
        raise ValueError(f'Empty source: {source}')
    box = (int(xx.min()), int(yy.min()), int(xx.max() + 1), int(yy.max() + 1))
    width, height, scale = target[2] - target[0], target[3] - target[1], 4
    px = math.ceil((box[2] - box[0]) / width * 3)
    py = math.ceil((box[3] - box[1]) / height * 3)
    crop = im.crop((box[0] - px, box[1] - py, box[2] + px, box[3] + py))
    crop = crop.convert('RGBa').resize((round((width + 6) * scale), round((height + 6) * scale)), Image.Resampling.LANCZOS).convert('RGBA')
    canvas = Image.new('RGBA', (256 * scale, 256 * scale))
    canvas.alpha_composite(crop, (round((target[0] - 3) * scale), round((target[1] - 3) * scale)))
    if row_warp:
        source_array = np.array(canvas.convert('RGBa'))
        dest = np.zeros_like(source_array)
        anchors = np.array(row_warp, float)
        shifts = np.interp(np.arange(256 * scale, dtype=float) / scale, anchors[:, 0], anchors[:, 1]) * scale
        for y, shift in enumerate(shifts):
            x = np.arange(256 * scale) - shift
            low = np.floor(x).astype(int)
            high = low + 1
            fraction = (x - low)[:, None]
            valid = (low >= 0) & (high < 256 * scale)
            dest[y, valid] = np.rint(source_array[y, low[valid]] * (1 - fraction[valid]) + source_array[y, high[valid]] * fraction[valid]).astype('uint8')
        canvas = Image.fromarray(dest, 'RGBa').convert('RGBA')
    if outer_ink_px:
        radius = round(outer_ink_px * scale)
        alpha = canvas.getchannel('A').filter(ImageFilter.MaxFilter(radius * 2 + 1))
        ink = Image.new('RGBA', canvas.size, (8, 7, 10, 0))
        ink.putalpha(alpha)
        ink.alpha_composite(canvas)
        canvas = ink
    canvas = canvas.convert('RGBa').resize((256, 256), Image.Resampling.LANCZOS).convert('RGBA')
    data = np.array(canvas)
    data[data[:, :, 3] < 8] = 0
    return Image.fromarray(data)

def build(recipe_path, out, allow_overwrite=False):
    recipe_path, out = Path(recipe_path).resolve(), Path(out).resolve()
    root = recipe_path.parent
    if out.exists() and any(out.iterdir()) and not allow_overwrite:
        raise ValueError('Choose an empty output directory')
    recipe = json.loads(recipe_path.read_text(encoding='utf-8'))
    for key, asset in recipe['assets'].items():
        src = (root / asset['source']).resolve()
        dst = (out / asset['relative_path']).resolve()
        if not src.is_relative_to(root) or not dst.is_relative_to(out):
            raise ValueError('Unsafe path')
        dst.parent.mkdir(parents=True, exist_ok=True)
        normalize(src, asset['target_solid_bbox'], asset.get('outer_ink_px', 0.5), asset.get('row_warp')).save(dst)
    item = (out / recipe['item_relative_path']).resolve()
    if not item.is_relative_to(out):
        raise ValueError('Unsafe item path')
    item.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(out / recipe['assets']['body_south']['relative_path'], item)
    return len(recipe['assets']) + 1

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recipe', type=Path, default=Path('recipe.json'))
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(build(args.recipe, args.out))
