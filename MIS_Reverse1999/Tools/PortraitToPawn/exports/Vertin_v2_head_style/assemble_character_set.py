"""AI-assisted: format authored head/body artwork into the existing mod texture layout.

This script imports six authored directional images; it does not generate artwork.
"""
from pathlib import Path
import argparse,hashlib,json,math,re,shutil
import numpy as np
from PIL import Image,ImageFilter

DIRS=('south','east','north')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def clean_image(path):
    a=np.asarray(Image.open(path).convert('RGBA')).copy()
    a[a[:,:,3]<16]=0
    return Image.fromarray(a)

def soften_and_reduce(image,radius,scale):
    if radius:image=image.convert('RGBa').filter(ImageFilter.GaussianBlur(radius*scale)).convert('RGBA')
    return image.resize((256,256),Image.Resampling.LANCZOS)

def body_canvas(path,frame,scale):
    image=clean_image(path);a=np.asarray(image)[:,:,3]
    ys,xs=np.where(a>=128)
    if not len(xs):raise ValueError(f'Empty source: {path}')
    bounds=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
    x0,y0,x1,y1=frame;w=x1-x0;h=y1-y0
    px=math.ceil((bounds[2]-bounds[0])*2/w);py=math.ceil((bounds[3]-bounds[1])*2/h)
    crop=image.crop((bounds[0]-px,bounds[1]-py,bounds[2]+px,bounds[3]+py))
    crop=crop.resize(((w+4)*scale,(h+4)*scale),Image.Resampling.LANCZOS)
    result=Image.new('RGBA',(256*scale,256*scale));result.alpha_composite(crop,((x0-2)*scale,(y0-2)*scale))
    return result,{'source_size':list(image.size),'source_solid_bbox':bounds,'target_frame':frame}

def head_canvas(path,registration,scale):
    image=clean_image(path);factor=registration['scale']
    sx,sy=registration['source_anchor'];tx,ty=registration['target_anchor']
    dx=tx-sx*factor;dy=ty-sy*factor
    coeff=(1/(factor*scale),0,-dx/factor,0,1/(factor*scale),-dy/factor)
    result=image.transform((256*scale,256*scale),Image.Transform.AFFINE,coeff,Image.Resampling.BICUBIC)
    return result,{'source_size':list(image.size),'registration':registration,'rotation_degrees':0}

def forward_offset(y,pose):
    fixed=pose['fixed_above_y'];waist=pose['waist_y']
    upper=math.tan(math.radians(pose['upper_degrees']));lower=math.tan(math.radians(pose['lower_degrees']))
    if y<=fixed:return 0
    if y<=waist:return -(y-fixed)*upper
    return -(waist-fixed)*upper-(y-waist)*lower

def pose_east(image,pose,scale):
    a=np.asarray(image);result=np.zeros_like(a);height,width=a.shape[:2]
    for row in range(height):
        delta=round(forward_offset((row+.5)/scale,pose)*scale)
        if abs(delta)>=width:raise ValueError('Pose shifts row outside canvas')
        if delta>=0:result[row,delta:]=a[row,:width-delta]
        else:result[row,:width+delta]=a[row,-delta:]
    return Image.fromarray(result)

def build(recipe_path,output):
    recipe_path=Path(recipe_path).resolve();output=Path(output).resolve();base=recipe_path.parent
    recipe=json.loads(recipe_path.read_text(encoding='utf-8'));name=recipe['name'];scale=recipe['supersample']
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*',name):raise ValueError('Invalid resource name')
    if output.exists() and any(output.iterdir()):raise ValueError('Choose an empty output directory')
    source={key:(base/value).resolve() for key,value in recipe['source_images'].items()}
    for path in source.values():
        if not path.is_file():raise FileNotFoundError(path)
    if recipe['east_pose']['head_rotation']!=0:raise ValueError('Head must remain upright')
    for radius in (recipe['head_soften_radius_px'],recipe['body_soften_radius_px']):
        if not 0<=radius<=1.5:raise ValueError('Softening out of range')
    body_rel=Path('Textures/Things/R99_Agents/Arcanist');head_rel=Path('Textures/Things/Hair/R99')
    for folder in (body_rel,head_rel,Path('source_art'),Path('neutral_body')):(output/folder).mkdir(parents=True,exist_ok=True)
    files=[];normalization={}
    for direction in DIRS:
        body,info=body_canvas(source['body_'+direction],recipe['body_frames'][direction],scale)
        soften_and_reduce(body,recipe['body_soften_radius_px'],scale).save(output/'neutral_body'/f'{name}_Thin_{direction}.png')
        if direction=='east':body=pose_east(body,recipe['east_pose'],scale)
        body_file=body_rel/f'{name}_Thin_{direction}.png'
        soften_and_reduce(body,recipe['body_soften_radius_px'],scale).save(output/body_file)
        head,head_info=head_canvas(source['head_'+direction],recipe['head_registration'][direction],scale)
        head_file=head_rel/f'{name}_{direction}.png'
        soften_and_reduce(head,recipe['head_soften_radius_px'],scale).save(output/head_file)
        files.extend((body_file.as_posix(),head_file.as_posix()))
        normalization[direction]={'body':info,'head':head_info}
    icon=body_rel/f'{name}.png';shutil.copy2(output/body_rel/f'{name}_Thin_south.png',output/icon);files.append(icon.as_posix())
    for key,path in source.items():shutil.copy2(path,output/'source_art'/f'{key}.png')
    shutil.copy2(base/recipe['source_portrait'],output/'portrait_reference.png')
    saved={**recipe,'source_images':{key:f'source_art/{key}.png' for key in source},'source_portrait':'portrait_reference.png'}
    (output/'recipe.json').write_text(json.dumps(saved,ensure_ascii=False,indent=2),encoding='utf-8')
    shutil.copy2(Path(__file__),output/'assemble_character_set.py')
    manifest={'name':name,'version':recipe['version'],'format':'256x256 RGBA PNG','files':files,
              'hashes':{rel:sha(output/rel) for rel in files},'source_hashes':{key:sha(path) for key,path in source.items()},
              'normalization':normalization,'east_pose':recipe['east_pose'],
              'head_soften_radius_px':recipe['head_soften_radius_px'],'body_soften_radius_px':recipe['body_soften_radius_px'],
              'game_tested':False,'method':'built-in image_gen directional drawing + local normalization and body pose'}
    (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    return manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--recipe',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();manifest=build(args.recipe,args.out)
    print(json.dumps({'output':str(args.out),'files':len(manifest['files']),'name':manifest['name']},ensure_ascii=False))
