"""AI-assisted local portrait -> template-driven RimWorld body sprite drafts.

The renderer composes original raster masks; it never copies reference pixels.
Only Pillow and NumPy are required. No cloud calls or model credentials.
"""
from __future__ import annotations

import argparse
from collections import deque
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

HERE = Path(__file__).resolve().parent
VERSION = "0.4.0"
FAMILIES = ("auto", "shirt_vest", "coat", "dress")
OUTLINE = "#17171c"


def rgb(value):
    if isinstance(value, str):
        value = value.lstrip("#")
        return tuple(int(value[i:i+2], 16) for i in (0, 2, 4))
    return tuple(int(v) for v in value[:3])


def hx(value):
    return "#" + "".join(f"{int(v):02x}" for v in value[:3])


def mix(a, b, t):
    return tuple(round(x * (1-t) + y*t) for x, y in zip(rgb(a), rgb(b)))


def luminance(a):
    return a[..., 0]*.2126 + a[..., 1]*.7152 + a[..., 2]*.0722


def connected_components(mask, minimum=1):
    """Bounded 4-connected components, used for skin and edge backgrounds."""
    h, w = mask.shape
    seen = np.zeros_like(mask)
    result = []
    for y, x in zip(*np.nonzero(mask)):
        if seen[y, x]:
            continue
        q = deque([(int(x), int(y))]); seen[y, x] = True
        points = []
        while q:
            cx, cy = q.popleft(); points.append((cx, cy))
            for nx, ny in ((cx-1,cy),(cx+1,cy),(cx,cy-1),(cx,cy+1)):
                if 0 <= nx < w and 0 <= ny < h and mask[ny,nx] and not seen[ny,nx]:
                    seen[ny,nx] = True; q.append((nx,ny))
        if len(points) >= minimum:
            pts = np.asarray(points)
            result.append((len(points), [int(pts[:,0].min()),int(pts[:,1].min()),
                                       int(pts[:,0].max())+1,int(pts[:,1].max())+1], pts))
    return sorted(result, key=lambda r:r[0], reverse=True)


def foreground(im):
    ar = np.asarray(im).copy()
    mask = ar[:,:,3] > 32
    notes = []
    if np.mean(ar[:,:,3] < 250) > .02:
        return mask, "input_alpha", notes
    # Remove only near-uniform background pixels connected to the image border.
    edge = np.concatenate([ar[0,:,:3],ar[-1,:,:3],ar[:,0,:3],ar[:,-1,:3]])
    bg = np.median(edge,axis=0)
    uniform = np.linalg.norm(edge.astype(float)-bg,axis=1) < 24
    if uniform.mean() < .7:
        notes.append("背景复杂：未自动抠出人物；建议提供透明或纯色背景立绘。")
        return mask, "opaque_complex_background", notes
    candidate = np.linalg.norm(ar[:,:,:3].astype(float)-bg,axis=2) < 24
    h,w=candidate.shape
    q=deque(); removed=np.zeros_like(candidate)
    for x,y in [(x,0) for x in range(w)]+[(x,h-1) for x in range(w)]+[(0,y) for y in range(h)]+[(w-1,y) for y in range(h)]:
        if candidate[y,x] and not removed[y,x]:
            q.append((x,y));removed[y,x]=True
    while q:
        x,y=q.popleft()
        for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
            if 0<=nx<w and 0<=ny<h and candidate[ny,nx] and not removed[ny,nx]:
                removed[ny,nx]=True;q.append((nx,ny))
    return mask & ~removed, "border_connected_background", notes


def color_from(values, default):
    return hx(np.median(values,axis=0).round().astype(int)) if len(values)>=8 else default


def analyze_portrait(path: Path, family="auto"):
    with Image.open(path) as raw:
        im=ImageOps.exif_transpose(raw).convert("RGBA")
    if min(im.size)<48:
        raise ValueError("立绘太小：请提供至少 48×48 像素、含服装区域的图片。")
    im.thumbnail((384,512),Image.Resampling.LANCZOS)
    mask,bg_method,notes=foreground(im)
    ys,xs=np.where(mask)
    if len(xs)<256:
        raise ValueError("没有足够的可见人物像素。")
    box=(int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1)
    im=im.crop(box);mask=mask[box[1]:box[3],box[0]:box[2]]
    ar=np.asarray(im); c=ar[:,:,:3].astype(float);h,w=mask.shape
    skin=mask & (c[:,:,0]>110) & (c[:,:,0]>c[:,:,1]*1.035) & (c[:,:,1]>c[:,:,2]*1.055) & ((c[:,:,0]-c[:,:,1])<95) & ((c[:,:,1]-c[:,:,2])<75)
    skin[int(h*.72):]=False
    components=connected_components(skin,minimum=max(15,int(w*h*.001)))
    # Prefer a central upper skin region, without claiming semantic face detection.
    candidates=[r for r in components if r[1][1]<h*.6 and .2*w<(r[1][0]+r[1][2])/2<.8*w]
    face=candidates[0] if candidates else None
    if face:
        _,fb,points=face
        head_h=fb[3]-fb[1]
        center=(fb[0]+fb[2])/2
        cloth_start=int(min(h*.77, fb[1]+head_h*.97))
        full_body=head_h/h < .25 and fb[3]<h*.47
        torso_end=int(min(h,fb[3]+head_h*2.1)) if full_body else h
        skin_color=color_from(c[points[:,1],points[:,0]],"#edc2a6")
    else:
        fb=None;center=w/2;cloth_start=int(h*.48);torso_end=h;full_body=False
        skin_color="#edc2a6"
        notes.append("未找到可靠的肤色区域：取图像下半部估计服装，肤色使用默认值。")
    if torso_end-cloth_start<12:
        raise ValueError("没有足够的服装区域；请换成至少露出胸部和肩膀的立绘。")
    yy,xx=np.indices((h,w));relx=(xx-center)/max(w,1)
    garment=mask & (yy>=cloth_start) & (yy<torso_end) & ~skin
    lum=luminance(c)
    saturation=(c.max(axis=2)-c.min(axis=2))/np.maximum(c.max(axis=2),1)
    bright=garment & (lum>170) & (saturation<.35)
    dark=garment & (lum<90)
    sleeve=garment & (np.abs(relx)>.25) & (np.abs(relx)<.47)
    central=garment & (np.abs(relx)<.12)
    panel=garment & (np.abs(relx)>.14) & (np.abs(relx)<.29)
    fraction=lambda region,test: float((region & test).sum()/max(region.sum(),1))
    features={
        "bright_cloth_fraction":round(fraction(garment,bright),3),
        "dark_cloth_fraction":round(fraction(garment,dark),3),
        "sleeve_bright_fraction":round(fraction(sleeve,bright),3),
        "center_bright_fraction":round(fraction(central,bright),3),
        "panel_dark_fraction":round(fraction(panel,dark),3),
        "full_body_inferred":bool(full_body),
    }
    vest_score=(features['sleeve_bright_fraction']*.45 + features['center_bright_fraction']*.25 + features['panel_dark_fraction']*.30)
    if family=='auto':
        if features['bright_cloth_fraction']>.12 and features['dark_cloth_fraction']>.14 and vest_score>.38:
            selected='shirt_vest'; confidence=round(min(.92,.45+vest_score*.5),2)
        else:
            selected='coat';confidence=.42
            notes.append("服装类别不确定，默认使用外套结构；可手动选择马甲、外套或连衣裙。")
        # Deliberately do not claim to infer a dress from a cropped portrait.
    else:
        selected=family;confidence=None
    clothing_pixels=c[garment]
    if not len(clothing_pixels):
        raise ValueError("未提取到服装像素。")
    if len(c[bright])>=8:
        shirt=color_from(c[bright],"#e9e9ec")
    else:
        shirt=color_from(clothing_pixels[luminance(clothing_pixels)>=np.quantile(luminance(clothing_pixels),.7)],"#e9e9ec")
    vest=color_from(c[dark],"#292a32")
    saturated=garment & (saturation>.22) & (lum>35) & (lum<205)
    primary=color_from(c[saturated],vest) if saturated.sum()>garment.sum()*.12 else vest
    # The upper portrait does not provide pants; explicitly choose a neutral default.
    trousers="#2c2b32"
    if full_body:
        low=mask & (yy>torso_end) & (yy<h*.88) & (lum<120)
        trousers=color_from(c[low],trousers)
    else:
        notes.append("输入为半身/裁切立绘，裤装与鞋采用可修改的中性黑色默认值。")
    notes.append("侧面和背面由服装模板推断，不是从单张正面立绘中恢复出的真实结构。")
    notes.append("自动分析基于肤色和空间色块启发式；复杂盔甲、异形身体及饰品需要配方或手动修订。")
    return {
        "version":VERSION,"source_path":str(path.resolve()),
        "source_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
        "family":selected,"family_selection":"automatic_heuristic" if family=='auto' else "user_override",
        "heuristic_score_not_probability":confidence,
        "palette":{"skin":skin_color,"shirt":shirt,"vest":vest,"primary":primary,
                   "pants":trousers,"shoes":"#242329","outline":"#101014","metal":"#7b7980"},
        "features":features,"analysis":{"background_method":bg_method,"subject_box_in_thumbnail":list(box),
            "skin_component_box":fb,"clothing_rows":[cloth_start,torso_end]},
        "parameters":{"outline_px":3.2,"supersample":4,"body_bbox":[86,90,170,252],
                      "buttons":2,"sleeve_style":"short","render_style":"flat","emit_layers":True},
        "inferred_or_limited":notes,
    }


class RasterPainter:
    """Each closed contour becomes an RGBA raster mask, then pixel compositing."""
    def __init__(self,palette,scale=4,line=2.6):
        self.s=scale;self.line=line;self.p={k:rgb(v) for k,v in palette.items()}
        self.image=Image.new('RGBA',(256*scale,256*scale));self.layers={}
        self.current=Image.new('RGBA',self.image.size);self.layer_name='base'

    def layer(self,name):
        self.flush();self.layer_name=name;self.current=Image.new('RGBA',self.image.size)

    def flush(self):
        if self.current.getbbox():
            self.image=Image.alpha_composite(self.image,self.current)
            self.layers[self.layer_name]=self.current.copy()
        self.current=Image.new('RGBA',self.image.size)

    def points(self,commands):
        result=[];last=(0,0)
        for cmd in commands:
            if cmd[0] in ('M','L'):
                last=(cmd[1],cmd[2]);result.append(last)
            elif cmd[0]=='C':
                p0=np.asarray(last,dtype=float);p1=np.asarray(cmd[1:3]);p2=np.asarray(cmd[3:5]);p3=np.asarray(cmd[5:7])
                for t in np.linspace(0,1,20)[1:]:
                    p=(1-t)**3*p0+3*(1-t)**2*t*p1+3*(1-t)*t*t*p2+t**3*p3
                    result.append(tuple(p))
                last=tuple(p3)
            elif cmd[0]=='Q':
                p0=np.asarray(last,dtype=float);p1=np.asarray(cmd[1:3]);p2=np.asarray(cmd[3:5])
                for t in np.linspace(0,1,14)[1:]:
                    result.append(tuple((1-t)**2*p0+2*(1-t)*t*p1+t*t*p2))
                last=tuple(p2)
        return [(round(x*self.s),round(y*self.s)) for x,y in result]

    def shape(self,path,fill,stroke=True,width=None):
        pts=self.points(path);d=ImageDraw.Draw(self.current)
        color=self.p.get(fill,fill) if isinstance(fill,str) else fill
        d.polygon(pts,fill=color)
        if stroke:
            d.line(pts+[pts[0]],fill=self.p['outline'],width=round((width or self.line)*self.s),joint='curve')

    def linepath(self,path,color=None,width=1.3):
        d=ImageDraw.Draw(self.current);pts=self.points(path)
        d.line(pts,fill=color or self.p['outline'],width=max(1,round(width*self.s)),joint='curve')

    def dot(self,x,y,r,color):
        d=ImageDraw.Draw(self.current)
        d.ellipse(tuple(round(v*self.s) for v in (x-r,y-r,x+r,y+r)),fill=self.p.get(color,color))

    def finish(self):
        self.flush()
        return self.image,self.layers


def draw_front_or_back(r,back=False,family='shirt_vest',buttons=3,sleeve_style='short'):
    p=r.p;shade=lambda k,t=.35:mix(p[k],p['outline'],t);light=lambda k,t=.25:mix(p[k],(230,232,239),t)
    r.layer('01_trousers')
    r.shape([('M',107,179),('Q',126,176,150,181),('L',151,207),('L',144,239),('Q',139,244,128,239),('L',126,211),('L',123,239),('Q',113,244,106,238),('L',101,209),('Z',)],'pants')
    r.shape([('M',106,190),('L',117,193),('L',118,222),('L',115,237),('L',108,237),('L',105,209)],light('pants',.16),False)
    r.shape([('M',139,191),('L',146,190),('L',146,214),('L',140,238),('L',132,238),('L',136,211)],shade('pants',.45),False)
    r.linepath([('M',126,192),('Q',130,200,127,213)],width=2)
    r.linepath([('M',110,218),('L',118,222)],color=light('pants',.2),width=1.3)
    r.linepath([('M',134,223),('L',143,218)],color=light('pants',.2),width=1.3)
    if back:r.linepath([('M',111,193),('Q',121,197,126,191),('Q',135,197,143,193)],width=1.6)
    r.layer('02_shoes')
    r.shape([('M',107,234),('Q',115,237,123,234),('L',125,244),('Q',126,250,116,250),('L',104,249),('Q',101,244,107,240)],'shoes')
    r.shape([('M',129,235),('Q',137,237,144,233),('L',148,241),('Q',153,248,144,250),('L',131,250),('Q',126,246,129,235)],'shoes')
    for x in (108,133):
        r.linepath([('M',x,243),('Q',x+4,241,x+10,243)],color=light('shoes',.25),width=2)
        r.linepath([('M',x-3,247),('L',x+12,247)],color=shade('shoes',.5),width=1.3)
    r.layer('03_neck')
    r.shape([('M',116,93),('Q',126,88,135,93),('L',138,108),('L',127,119),('L',113,107)],'skin')
    r.shape([('M',117,95),('Q',127,101,136,94),('L',137,104),('Q',128,111,116,104)],shade('skin',.15),False)
    r.layer('04_shirt')
    # Garment torso only. Shoulder caps are separate; no anatomical arms/hands.
    r.shape([('M',113,105),('L',126,116),('L',138,105),('L',148,112),
             ('Q',145,136,148,159),('L',147,192),('L',120,193),
             ('Q',108,190,107,178),('L',109,145),('L',105,113)],'shirt')
    if sleeve_style=='short':
        r.layer('04b_short_sleeve_caps')
        r.shape([('M',110,107),('Q',102,106,99,113),('L',97,122),
                 ('L',106,126),('Q',110,117,114,111)],'shirt',width=2.2)
        r.shape([('M',144,108),('Q',152,107,156,115),('L',158,122),
                 ('L',149,126),('Q',146,117,141,112)],'shirt',width=2.2)
        r.shape([('M',100,116),('L',99,121),('L',106,124),('L',108,120)],shade('shirt',.19),False)
        r.shape([('M',151,114),('L',155,121),('L',149,124),('L',147,119)],shade('shirt',.22),False)
        r.linepath([('M',98,122),('L',106,125)],width=1.3)
        r.linepath([('M',149,125),('L',157,122)],width=1.3)
    r.layer('05_waistcoat' if family=='shirt_vest' else '05_garment')
    if family=='shirt_vest':
        if back:
            r.shape([('M',111,105),('Q',125,110,141,105),('L',149,111),('Q',144,136,149,163),('L',149,184),('Q',138,192,127,194),('Q',111,190,104,184),('L',105,158),('Q',110,132,105,112)],'vest')
            r.shape([('M',112,113),('Q',121,117,128,115),('L',128,185),('L',108,181),('Q',113,150,112,113)],light('vest',.10),False)
            r.linepath([('M',113,121),('Q',117,149,113,171)],color=light('vest',.27),width=1.1)
            r.linepath([('M',140,121),('Q',136,147,141,172)],color=shade('vest',.6),width=1.3)
            r.linepath([('M',108,173),('Q',128,178,146,172)],color=shade('vest',.65),width=3)
            r.shape([('M',124,173),('L',130,173),('L',130,177),('L',124,177)],'metal',False)
        else:
            r.shape([('M',108,107),('L',116,106),('Q',122,123,129,138),('L',140,107),('L',147,109),('Q',143,127,148,144),('L',151,184),('L',141,192),('L',130,181),('L',120,192),('L',104,185),('Q',111,158,106,137),('Q',103,121,108,107)],'vest')
            r.shape([('M',112,111),('L',117,112),('L',126,137),('L',126,176),('L',118,185),('L',109,181),('Q',113,148,110,135)],light('vest',.17),False)
            r.shape([('M',142,112),('L',145,113),('L',143,132),('L',148,181),('L',141,186),('L',134,178),('L',134,138)],shade('vest',.2),False)
            r.linepath([('M',129,139),('L',131,179)],width=1.5)
            r.linepath([('M',110,167),('L',121,169)],color=light('vest',.4),width=1.8)
            r.linepath([('M',136,168),('L',144,166)],color=light('vest',.3),width=1.5)
            for y in [148,160,172][:buttons]:
                r.dot(131,y,1.3,'metal');r.dot(130.5,y-.4,.45,'shirt')
    elif family=='coat':
        r.shape([('M',107,105),('L',117,107),('L',128,132),('L',140,107),('L',150,109),('Q',150,152,154,171),('L',166,210),('Q',152,218,133,207),('L',128,179),('L',123,207),('Q',107,217,94,209),('L',104,168)],'primary')
        r.shape([('M',110,110),('L',119,116),('L',126,139),('L',116,134),('L',118,147),('L',108,154)],light('primary',.25))
        r.shape([('M',143,111),('L',134,137),('L',142,132),('L',140,147),('L',149,155)],light('primary',.17))
        r.linepath([('M',107,170),('L',119,173)],color=light('primary',.35),width=2)
        if back:
            r.shape([('M',111,108),('L',144,108),('L',148,166),('L',155,207),('L',128,204),('L',102,208),('L',108,164)],'primary')
            r.linepath([('M',128,116),('L',129,203)],color=shade('primary',.55),width=1.5)
    elif family=='dress':
        r.shape([('M',109,107),('L',118,108),('L',128,125),('L',139,108),('L',148,111),('Q',142,142,145,161),('Q',154,180,164,211),('Q',129,225,93,211),('Q',99,182,109,162),('Q',113,140,109,107)],'primary')
        r.shape([('M',115,169),('Q',110,194,106,212),('L',122,215),('L',128,170)],light('primary',.19),False)
        r.shape([('M',139,170),('L',143,215),('L',158,210),('Q',145,183,139,170)],shade('primary',.25),False)
        r.linepath([('M',110,164),('Q',128,168,145,163)],width=3)
        if back:r.linepath([('M',127,113),('L',128,162)],color=shade('primary',.45),width=1.3)
    r.layer('06_collar')
    if back:
        r.shape([('M',113,104),('Q',126,109,139,104),('L',143,111),('Q',128,116,109,111)],'shirt',width=2)
    else:
        r.shape([('M',119,108),('L',126,113),('L',134,108),('L',130,120),('L',127,124),('L',124,118)],'skin',False)
        r.shape([('M',113,103),('L',126,113),('L',120,128),('L',109,113)],'shirt',width=2.1)
        r.shape([('M',137,103),('L',128,113),('L',136,125),('L',145,111)],'shirt',width=2.1)
        r.linepath([('M',126,115),('L',128,131)],color=shade('shirt',.45),width=1)


def draw_side(r,family='shirt_vest',sleeve_style='short'):
    p=r.p;shade=lambda k,t=.35:mix(p[k],p['outline'],t);light=lambda k,t=.25:mix(p[k],(230,232,239),t)
    r.layer('01_trousers')
    r.shape([('M',112,177),('L',143,181),('L',148,203),('L',137,238),('L',124,239),('L',126,211),('L',119,238),('L',107,237),('L',105,210)],'pants')
    r.shape([('M',135,193),('L',143,193),('L',142,212),('L',133,236),('L',127,236),('L',131,209)],light('pants',.18),False)
    r.linepath([('M',120,195),('L',126,210),('L',118,232)],width=2)
    r.layer('02_shoes')
    r.shape([('M',106,233),('L',119,234),('L',120,240),('L',129,244),('Q',132,249,122,250),('L',105,249)],'shoes')
    r.shape([('M',125,233),('L',138,234),('L',138,240),('L',151,244),('Q',156,249,147,251),('L',127,250),('Q',122,246,125,233)],'shoes')
    r.linepath([('M',132,245),('Q',142,242,148,246)],color=light('shoes',.3),width=2)
    r.layer('03_neck')
    r.shape([('M',119,92),('Q',128,88,136,94),('L',139,107),('L',130,116),('L',116,109)],'skin')
    r.shape([('M',120,96),('L',135,101),('L',136,108),('L',119,109)],shade('skin',.2),False)
    r.layer('04_shirt')
    r.shape([('M',115,106),('Q',126,102,139,112),('Q',149,121,150,143),
             ('L',147,162),('L',139,188),('L',111,190),
             ('Q',110,174,112,156),('L',111,123),('Q',109,112,115,106)],'shirt')
    r.layer('05_garment')
    if family=='shirt_vest':
        r.shape([('M',115,107),('L',126,106),('L',135,119),('L',139,113),('Q',149,127,148,144),('L',144,171),('L',142,188),('L',131,194),('L',111,186),('Q',114,163,111,141)],'vest')
        r.shape([('M',118,111),('L',124,111),('Q',131,137,127,162),('L',125,185),('L',115,182),('L',119,149)],light('vest',.15),False)
        r.linepath([('M',141,144),('L',138,179)],color=light('vest',.2),width=1.4)
        r.linepath([('M',131,170),('L',141,166)],color=light('vest',.4),width=1.5)
        for y in (146,157,168):r.dot(144-(y-146)*.12,y,1,'metal')
    elif family=='coat':
        r.shape([('M',113,107),('L',127,106),('L',138,115),('Q',150,130,146,158),('L',142,174),('L',148,210),('L',130,214),('L',125,192),('L',117,212),('L',99,210),('L',110,168)],'primary')
        r.shape([('M',130,112),('L',139,119),('L',144,135),('L',134,131),('L',137,143),('L',126,154)],light('primary',.2))
    else:
        r.shape([('M',115,107),('L',129,107),('L',140,117),('Q',150,138,140,163),('L',157,213),('Q',127,222,99,211),('L',112,165)],'primary')
        r.shape([('M',121,169),('L',118,214),('L',133,215),('L',133,170)],light('primary',.2),False)
        r.linepath([('M',112,164),('L',141,165)],width=3)
    if sleeve_style=='short':
        r.layer('06_short_sleeve_cap')
        r.shape([('M',112,112),('Q',121,110,126,117),('L',128,124),
                 ('Q',118,130,108,125),('L',107,120),('Q',107,115,112,112)],'shirt',width=2.2)
        r.shape([('M',109,119),('L',110,124),('Q',117,128,126,124),
                 ('L',124,121),('Q',116,124,109,119)],shade('shirt',.21),False)
        r.linepath([('M',109,125),('Q',117,129,127,124)],width=1.4)
    r.layer('08_collar')
    r.shape([('M',119,104),('L',132,109),('L',136,119),('L',127,116),('L',122,111),('L',112,111)],'shirt',width=2)


def align_layers(image,layers,target,scale,source_frame):
    # Fixed design frame: removing sleeves must not stretch torso/legs to fill it.
    box=tuple(round(value*scale) for value in source_frame)
    x0,y0,x1,y1=map(int,target)
    def convert(im):
        crop=im.crop(box).resize(((x1-x0)*scale,(y1-y0)*scale),Image.Resampling.LANCZOS)
        result=Image.new('RGBA',(256*scale,256*scale))
        result.alpha_composite(crop,(x0*scale,y0*scale))
        return result.resize((256,256),Image.Resampling.LANCZOS)
    return convert(image),{k:convert(v) for k,v in layers.items()}


def render_body(recipe,direction):
    params=recipe['parameters'];scale=int(params.get('supersample',4))
    if scale not in (1,2,3,4,6):raise ValueError('supersample 必须为 1、2、3、4 或 6。')
    if params.get('render_style')=='fitted_tactical':
        import fitted_renderer
        r=RasterPainter({**fitted_renderer.ACCENTS,**recipe['palette']},scale,float(params.get('outline_px',3)))
        fitted_renderer.draw(r,direction,params.get('sleeve_style','short'))
        image,layers=r.finish()
        return align_layers(image,layers,params['body_bbox'],scale,[86,90,170,252])
    r=RasterPainter(recipe['palette'],scale,float(params.get('outline_px',2.6)))
    sleeve_style=params.get('sleeve_style','short')
    flat=params.get('render_style','shaded')=='flat'
    if flat:
        import flat_renderer
        if direction=='east':flat_renderer.side(r,recipe['family'],sleeve_style,int(params.get('buttons',2)))
        else:flat_renderer.front_or_back(r,direction=='north',recipe['family'],int(params.get('buttons',2)),sleeve_style)
    elif direction=='east':draw_side(r,recipe['family'],sleeve_style)
    else:draw_front_or_back(r,direction=='north',recipe['family'],int(params.get('buttons',3)),sleeve_style)
    image,layers=r.finish()
    target=list(params['body_bbox'])
    if direction=='east':
        mid=(target[0]+target[2])/2; width=(target[2]-target[0])*.79
        target[0]=round(mid-width/2);target[2]=round(mid+width/2)
    source_frame=[84.0,89.5,172.0,252.0] if flat else [86.0,89.5,168.25,251.25]
    if direction=='east' and flat:
        source_frame=[98.0,89.5,160.0,252.5]
    elif direction=='east':
        source_frame={'shirt_vest':[100.0,89.5,154.25,252.25],
                      'coat':[97.75,89.5,154.25,252.25],
                      'dress':[97.75,89.5,158.5,252.25]}[recipe['family']]
    return align_layers(image,layers,target,scale,source_frame)


def reference_profile(reference_dir):
    """Read geometry only. Reference image pixels never enter rendered assets."""
    result={"reference_dir":str(reference_dir),"pixel_copying":False,"measurements":{}}
    for name,sub in [('Thorns','Guard'),('Texas','Vanguard')]:
        path=reference_dir/sub/(name+'_Thin_south.png')
        if not path.is_file():continue
        with Image.open(path) as im:
            a=np.asarray(im.convert('RGBA'))[:,:,3];ys,xs=np.where(a>=128)
            if not len(xs):continue
            box=[int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
            result['measurements'][name]={'size':list(im.size),'alpha_128_bbox':box,
                'width_on_256':round((box[2]-box[0])/im.width*256,2),
                'height_on_256':round((box[3]-box[1])/im.height*256,2)}
    return result


def font(size):
    for path in [Path('C:/Windows/Fonts/msyh.ttc'),Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]:
        if path.is_file():return ImageFont.truetype(str(path),size)
    return ImageFont.load_default(size=size)


def checker(im,x,y,w,h,step=16):
    d=ImageDraw.Draw(im)
    for yy in range(0,h,step):
        for xx in range(0,w,step):
            col='#dce1e6' if (xx//step+yy//step)%2 else '#eef0f3'
            d.rectangle((x+xx,y+yy,x+min(xx+step,w)-1,y+min(yy+step,h)-1),fill=col)


def preview(source,images,path,recipe):
    sheet=Image.new('RGB',(1160,630),'#f7f8fa');d=ImageDraw.Draw(sheet)
    d.text((24,18),'立绘 → 像素衣片合成 · 躯干草稿',font=font(26),fill='#213448')
    sleeve_label='肩部短袖口' if recipe['parameters'].get('sleeve_style','short')=='short' else '不画袖口'
    style_label={'fitted_tactical':'贴身战术 · 矢量衣片','flat':'扁平 Q 版'}.get(recipe['parameters'].get('render_style'),'旧版色块模板')
    d.text((24,58),f"{style_label} / 无双臂 · {sleeve_label} / 256×256 RGBA",font=font(16),fill='#5c6774')
    for i,label in enumerate(['输入立绘','south 正面','east 侧面（推断）','north 背面（推断）']):
        x=24+i*284;d.text((x,104),label,font=font(18),fill='#213448')
        checker(sheet,x,142,256,320)
        if i==0:
            with Image.open(source) as raw:im=ImageOps.exif_transpose(raw).convert('RGBA')
            im.thumbnail((256,320),Image.Resampling.LANCZOS);sheet.paste(im,(x+(256-im.width)//2,142+(320-im.height)//2),im)
        else:
            im=images[['south','east','north'][i-1]]
            sheet.paste(im,(x,142),im)
            # The full-size canvas above is the authoritative scale comparison.
            tiny=im.resize((96,96),Image.Resampling.LANCZOS)
            checker(sheet,x+80,480,96,96);sheet.paste(tiny,(x+80,480),tiny)
    d.text((24,588),'小图用于缩小可读性检查；未叠加头部，非游戏内截图。',font=font(15),fill='#5c6774')
    sheet.save(path)


def safe_name(name):
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,63}',name):
        raise ValueError('角色名请用英文字母开头，后接字母、数字或下划线（最多 64 字符）。')
    return name


def validate_recipe(recipe):
    if recipe['family'] not in FAMILIES[1:]:raise ValueError('未知的服装模板。')
    for key,color in recipe['palette'].items():
        if not isinstance(color,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',color):
            raise ValueError(f'颜色 {key} 必须为 #RRGGBB。')
    p=recipe['parameters']
    allowed={'outline_px','supersample','body_bbox','buttons','sleeve_style','render_style','emit_layers'}
    extra=set(p)-allowed
    if extra:raise ValueError(f'不支持的参数：{sorted(extra)}')
    box=p['body_bbox']
    if len(box)!=4 or any(type(v) is not int for v in box) or not (1<=box[0]<box[2]<=254 and 1<=box[1]<box[3]<=254):
        raise ValueError('body_bbox 必须是画布内的整数 [左,上,右,下]，坐标范围 1～254。')
    if box[2]-box[0]<16 or box[3]-box[1]<32:raise ValueError('body_bbox 太小。')
    if not 1<=float(p['outline_px'])<=5:raise ValueError('outline_px 应在 1～5 之间。')
    if type(p['buttons']) is not int or not 0<=p['buttons']<=3:raise ValueError('buttons 应为 0～3 的整数。')
    if p['supersample'] not in (1,2,3,4,6):raise ValueError('supersample 应为 1、2、3、4 或 6。')
    if p.get('sleeve_style','short') not in ('short','none'):raise ValueError('sleeve_style 应为 short 或 none。')
    if p.get('render_style','shaded') not in ('flat','shaded','fitted_tactical'):raise ValueError('render_style 应为 flat、shaded 或 fitted_tactical。')
    if p.get('render_style')=='fitted_tactical' and recipe['family']!='shirt_vest':
        raise ValueError('贴身战术配方适用于 shirt_vest（衬衫＋马甲）。')


def generate(source,output,name,family='auto',recipe_path=None,reference_dir=None,sleeve_style=None):
    source=Path(source).resolve();output=Path(output).resolve();safe_name(name)
    if not source.is_file():raise FileNotFoundError(source)
    if output.exists() and any(output.iterdir()):
        raise ValueError(f'输出目录已有内容，改用新目录以保留已有文件：{output}')
    recipe=analyze_portrait(source,family)
    if reference_dir:
        recipe['style_reference']=reference_profile(Path(reference_dir))
        m=recipe['style_reference']['measurements'].get('Thorns')
        texas=recipe['style_reference']['measurements'].get('Texas')
        if m or texas:
            width=max(40,min(130,round((texas or m)['width_on_256'])))
            height=max(90,min(200,round((m or texas)['height_on_256'])))
            left=round(128-width/2)
            recipe['parameters']['body_bbox']=[left,252-height,left+width,252]
    if recipe_path:
        override=json.loads(Path(recipe_path).read_text(encoding='utf-8'))
        for key in ('family','palette','parameters'):
            if key in override:
                if isinstance(override[key],dict):recipe[key].update(override[key])
                else:recipe[key]=override[key]
        recipe['recipe_override']=str(Path(recipe_path).resolve())
    if sleeve_style is not None:recipe['parameters']['sleeve_style']=sleeve_style
    validate_recipe(recipe)
    fitted=recipe['parameters'].get('render_style')=='fitted_tactical'
    if fitted:
        import fitted_renderer
        recipe['palette']={**fitted_renderer.ACCENTS,**recipe['palette']}
        recipe['inferred_or_limited'].append('贴身战术款的轮廓和装备布局由本次矢量配方定义；程序读取立绘配色，不会自动理解任意立绘的装备结构。')
    out=output/'Textures'/'Things'/'R99_Agents'/'Arcanist';out.mkdir(parents=True,exist_ok=True)
    images={};files=[]
    for direction in ('south','east','north'):
        im,layers=render_body(recipe,direction);images[direction]=im
        dest=out/f'{name}_Thin_{direction}.png';im.save(dest);files.append(str(dest.relative_to(output)))
        if recipe['parameters'].get('emit_layers',True):
            layer_dir=output/'editable_layers'/direction;layer_dir.mkdir(parents=True,exist_ok=True)
            for key,layer in layers.items():layer.save(layer_dir/(key+'.png'))
        if fitted:
            svg_dir=output/'editable_svg';svg_dir.mkdir(exist_ok=True)
            (svg_dir/f'{name}_Thin_{direction}.svg').write_text(fitted_renderer.svg_document(recipe,direction),encoding='utf-8')
    images['south'].save(out/f'{name}.png');files.append(str((out/f'{name}.png').relative_to(output)))
    (output/'recipe.json').write_text(json.dumps(recipe,ensure_ascii=False,indent=2),encoding='utf-8')
    preview(source,images,output/'body_preview.png',recipe)
    manifest={"generator":VERSION,"name":name,"format":"256x256 RGBA PNG",
              "status":"draft_not_game_tested","source_sha256":recipe['source_sha256'],
              "generated_files":files,"head_generated":False,
              "body_style":{"arms":"omitted","hands":"omitted","sleeves":recipe['parameters']['sleeve_style'],
                            "render_style":recipe['parameters'].get('render_style','shaded'),
                            "leg_pose":"straight_inward_legs_downward_boots" if fitted else ("closed_tapered_with_low_wide_feet" if recipe['parameters'].get('render_style')=='flat' else "legacy"),
                            "scaling":"fixed design frame; transparent gaps do not change torso width"},
              "directions":{"south":"front template conditioned on portrait palette",
                            "east":"template inference","north":"template inference"},
              "hashes":{file:hashlib.sha256((output/file).read_bytes()).hexdigest() for file in files}}
    if fitted:
        manifest['editable_vectors']=[f'editable_svg/{name}_Thin_{d}.svg' for d in ('south','east','north')]
        manifest['body_style']['silhouette']='raised_fitted_waist_hips_wider_than_shoulders'
        manifest['body_style']['equipment']=['flat_chest_plate','magazine_pouches','radio','cummerbund','hip_pouches','thigh_strap']
    (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    return output,recipe


def main(argv=None):
    parser=argparse.ArgumentParser(description='本地立绘转 RimWorld 躯干 PNG 草稿；不调用云 API。')
    parser.add_argument('image',type=Path,help='含服装的立绘 PNG/JPEG/WebP')
    parser.add_argument('--name',required=True,help='新角色的资源英文名')
    parser.add_argument('--out',type=Path)
    parser.add_argument('--family',choices=FAMILIES,default='auto')
    parser.add_argument('--recipe',type=Path,help='覆盖颜色和结构参数的 JSON 配方')
    parser.add_argument('--sleeve-style',choices=('short','none'),help='肩部短袖口或完全省略袖口；均不画双臂和手')
    parser.add_argument('--reference-dir',type=Path,default=HERE.parents[2]/'MIS_arknights'/'Textures'/'Things'/'AK_Agents')
    args=parser.parse_args(argv)
    out=args.out or HERE/'exports'/(args.name+'_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    try:
        dest,recipe=generate(args.image,out,args.name,args.family,args.recipe,args.reference_dir,args.sleeve_style)
    except (OSError,ValueError,KeyError) as exc:
        parser.exit(2,f'生成失败：{exc}\n')
    print(json.dumps({'output':str(dest),'family':recipe['family'],'notes':recipe['inferred_or_limited']},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
