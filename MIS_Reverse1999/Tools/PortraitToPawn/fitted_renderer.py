"""AI-assisted, editable flat vector construction for the fitted tactical preset.

Contours are newly authored. Reference assets informed proportions only.
The same drawing instructions feed SVG paths and the PNG rasterizer.
"""
from html import escape

ACCENTS = {
    'rig':'#5e706c', 'pouch':'#9b8d70', 'webbing':'#55585b',
    'belt':'#884c55', 'radio':'#41464b', 'screen':'#dfa253',
    'boot_trim':'#4a4d56',
}


def front_or_back(r, back=False, sleeve_style='short'):
    r.layer('01_fitted_trousers')
    # The pelvis is wider than the shoulders. Below the hips the contours are
    # straight, converging segments, not inflated curves around the thighs.
    r.shape([('M',107,169),('L',149,169),('Q',159,176,163,187),
             ('L',147,230),('L',138,234),('L',118,234),('L',109,230),
             ('L',93,187),('Q',97,176,107,169)],'pants')
    r.linepath([('M',128,187),('L',128,233)],width=1.9)
    if back:
        r.linepath([('M',103,184),('L',113,189),('L',122,185)],width=1.7)
        r.linepath([('M',134,185),('L',143,189),('L',153,184)],width=1.7)
    else:
        r.linepath([('M',101,183),('L',108,192)],width=1.7)
        r.linepath([('M',155,183),('L',148,192)],width=1.7)

    r.layer('02_downward_boots')
    # Toes continue down the leg axes. They do not flare out sideways.
    r.shape([('M',109,226),('L',127,227),('L',127,243),
             ('Q',127,251,118,251),('Q',108,251,107,245),
             ('L',108,236)],'shoes')
    r.shape([('M',129,227),('L',147,226),('L',148,236),
             ('L',149,245),('Q',148,251,138,251),
             ('Q',129,251,129,243)],'shoes')
    r.shape([('M',109,227),('L',125,228),('L',125,234),
             ('L',110,234)],'boot_trim',width=1.7)
    r.shape([('M',131,228),('L',147,227),('L',146,234),
             ('L',131,234)],'boot_trim',width=1.7)
    r.linepath([('M',109,245),('Q',118,248,126,245)],width=1.4)
    r.linepath([('M',130,245),('Q',138,248,147,245)],width=1.4)
    if not back:
        r.linepath([('M',114,237),('L',122,237)],width=1.5)
        r.linepath([('M',134,237),('L',142,237)],width=1.5)

    r.layer('03_neck')
    r.shape([('M',118,93),('Q',127,89,137,94),('L',138,109),
             ('L',128,117),('L',116,109)],'skin')
    r.layer('04_white_shirt')
    r.shape([('M',108,108),('L',119,105),('L',128,114),
             ('L',137,105),('L',148,108),('L',154,129),
             ('Q',153,143,145,159),('L',150,174),('L',158,182),
             ('L',140,187),('L',128,182),('L',115,187),('L',98,181),
             ('L',110,160),('Q',101,143,101,129)],'shirt')
    if sleeve_style=='short':
        r.layer('04b_small_shoulder_caps')
        r.shape([('M',108,108),('Q',100,107,98,111),
                 ('L',95,119),('L',103,123),('L',111,113)],'shirt',width=2.6)
        r.shape([('M',148,108),('Q',156,107,158,111),
                 ('L',161,119),('L',153,123),('L',145,113)],'shirt',width=2.6)

    r.layer('05_fitted_waistcoat')
    if back:
        r.shape([('M',106,109),('L',116,107),('Q',128,112,140,107),
                 ('L',150,109),('Q',158,126,156,136),
                 ('L',146,158),('L',148,168),('L',160,180),
                 ('L',143,185),('L',128,179),('L',112,185),('L',96,180),
                 ('L',108,168),('L',110,158),('L',100,136),
                 ('Q',98,126,106,109)],'vest')
    else:
        r.shape([('M',106,109),('L',116,107),('L',128,133),
                 ('L',140,107),('L',150,109),('Q',158,126,156,136),
                 ('L',146,158),('L',148,168),('L',160,180),
                 ('L',143,185),('L',128,177),('L',112,185),('L',96,180),
                 ('L',108,168),('L',110,158),('L',100,136),
                 ('Q',98,126,106,109)],'vest')
        r.linepath([('M',128,157),('L',128,177)],width=1.7)

    r.layer('06_harness')
    r.shape([('M',108,111),('L',114,110),('L',119,140),
             ('L',112,142)],'webbing',width=1.8)
    r.shape([('M',142,110),('L',148,111),('L',144,142),
             ('L',137,140)],'webbing',width=1.8)
    r.layer('07_flat_plate')
    if back:
        r.shape([('M',118,120),('L',138,120),('L',144,129),
                 ('L',141,153),('L',115,153),('L',112,129)],'rig',width=2.4)
        r.linepath([('M',118,132),('L',138,132)],width=1.5)
        r.linepath([('M',118,143),('L',138,143)],width=1.5)
        r.shape([('M',123,121),('L',133,121),('L',133,126),
                 ('L',123,126)],'webbing',width=1.5)
    else:
        r.shape([('M',114,133),('L',140,133),('L',144,139),
                 ('L',141,154),('L',113,154),('L',110,140)],'rig',width=2.5)
        r.linepath([('M',114,141),('L',140,141)],width=1.5)
        r.layer('08_magazine_pouches')
        for x in (117,129):
            r.shape([('M',x,145),('L',x+9,145),('L',x+9,160),
                     ('L',x,160)],'pouch',width=1.8)
            r.linepath([('M',x,150),('L',x+9,150)],width=1.4)
            r.shape([('M',x+3,149),('L',x+6,149),('L',x+6,154),
                     ('L',x+3,154)],'webbing',width=1.2)

    r.layer('09_collar')
    if back:
        r.shape([('M',115,104),('Q',128,110,140,104),('L',146,111),
                 ('Q',128,117,109,111)],'shirt',width=2.5)
    else:
        r.shape([('M',113,104),('L',127,114),('L',119,128),
                 ('L',103,112)],'shirt',width=2.5)
        r.shape([('M',141,104),('L',129,114),('L',137,128),
                 ('L',153,112)],'shirt',width=2.5)

    r.layer('10_radio')
    # Keep the radio on the same anatomical side in front and rear views.
    x=102 if back else 144
    r.linepath([('M',x+6,119),('L',x+6,130)],width=2.8)
    r.shape([('M',x,129),('L',x+11,129),('L',x+11,150),
             ('L',x,150)],'radio',width=2)
    if not back:
        r.shape([('M',x+2,133),('L',x+8,133),('L',x+8,137),
                 ('L',x+2,137)],'screen',width=1.3)
    r.linepath([('M',x+2,141),('L',x+8,141)],width=1.3)
    r.linepath([('M',x+2,145),('L',x+8,145)],width=1.3)
    r.linepath([('M',x+4,151),('Q',x+2,157,128,160)],width=1.7)

    r.layer('11_cummerbund')
    r.shape([('M',109,159),('Q',128,164,147,159),('L',151,171),
             ('Q',128,176,105,171)],'belt',width=2.5)
    r.linepath([('M',108,165),('Q',128,169,148,165)],width=1.5)
    if not back:
        r.shape([('M',124,164),('L',133,164),('L',133,173),
                 ('L',124,173)],'pouch',width=1.8)
        r.linepath([('M',128,166),('L',128,171)],width=1.3)

    r.layer('12_hip_equipment')
    px=150 if back else 92
    r.shape([('M',px+1,175),('L',px+13,176),('L',px+14,196),
             ('Q',px+7,200,px,196),('L',px-1,182)],'pouch',width=2.4)
    r.linepath([('M',px,184),('L',px+13,185)],width=1.6)
    r.shape([('M',px+5,183),('L',px+9,183),('L',px+9,188),
             ('L',px+5,188)],'webbing',width=1.2)
    px=92 if back else 151
    r.shape([('M',px,177),('L',px+12,179),('L',px+13,193),
             ('L',px+2,195)],'rig',width=2.2)
    r.linepath([('M',px+1,183),('L',px+12,184)],width=1.5)

    r.layer('13_thigh_strap')
    if back:
        path=[('M',99,201),('L',124,205),('L',124,210),('L',101,206)]
        bx=108
    else:
        path=[('M',132,205),('L',157,201),('L',155,206),('L',132,210)]
        bx=143
    r.shape(path,'belt',width=1.7)
    r.shape([('M',bx,204),('L',bx+5,203),('L',bx+5,209),
             ('L',bx,210)],'metal',width=1.3)


def side(r, sleeve_style='short'):
    r.layer('01_fitted_trousers')
    r.shape([('M',115,168),('L',140,169),('Q',150,175,151,187),
             ('L',139,230),('L',119,233),('L',104,188),
             ('Q',106,176,115,168)],'pants')
    r.linepath([('M',126,190),('L',132,231)],width=1.7)
    r.layer('02_downward_boots')
    r.shape([('M',116,226),('L',128,226),('L',133,243),
             ('L',138,248),('Q',129,253,119,249),('L',116,240)],'shoes')
    r.shape([('M',126,226),('L',140,226),('L',140,239),
             ('L',147,246),('Q',148,250,141,251),('L',127,251),
             ('Q',123,246,124,241)],'shoes')
    r.shape([('M',126,227),('L',140,227),('L',139,233),
             ('L',125,234)],'boot_trim',width=1.7)
    r.linepath([('M',126,246),('Q',136,249,145,247)],width=1.5)
    r.layer('03_neck')
    r.shape([('M',119,93),('Q',128,89,136,94),('L',139,108),
             ('L',129,116),('L',117,109)],'skin')
    r.layer('04_white_shirt')
    r.shape([('M',114,107),('L',129,106),('L',142,114),
             ('Q',151,126,147,138),('L',138,160),('L',143,173),
             ('L',151,182),('L',129,188),('L',105,180),
             ('L',115,159),('L',108,132)],'shirt')
    r.layer('05_fitted_waistcoat')
    r.shape([('M',113,109),('L',123,107),('L',137,121),('L',142,115),
             ('Q',152,128,148,139),('L',139,159),('L',142,172),
             ('L',151,181),('L',136,186),('L',126,180),('L',106,181),
             ('L',115,160),('L',109,136)],'vest')
    r.layer('06_harness')
    r.shape([('M',115,112),('L',121,111),('L',123,153),
             ('L',116,154)],'webbing',width=1.7)
    r.shape([('M',139,132),('L',147,133),('L',145,151),
             ('L',138,154)],'rig',width=2.1)
    r.shape([('M',142,145),('L',150,145),('L',149,160),
             ('L',141,160)],'pouch',width=1.8)
    if sleeve_style=='short':
        r.layer('07_short_cap')
        r.shape([('M',113,110),('Q',124,108,129,117),('L',127,123),
                 ('L',110,121),('L',108,116)],'shirt',width=2.5)
    r.layer('08_collar')
    r.shape([('M',118,104),('L',131,111),('L',139,124),
             ('L',128,120),('L',120,111),('L',111,112)],'shirt',width=2.5)
    r.layer('09_cummerbund')
    r.shape([('M',115,160),('L',140,160),('L',145,171),
             ('L',110,171)],'belt',width=2.4)
    r.linepath([('M',113,166),('L',142,166)],width=1.4)
    r.layer('10_hip_pouch')
    r.shape([('M',106,175),('L',122,176),('L',125,196),
             ('Q',115,200,105,196),('L',103,182)],'pouch',width=2.4)
    r.linepath([('M',105,184),('L',123,185)],width=1.6)
    r.shape([('M',113,184),('L',118,184),('L',118,189),
             ('L',113,189)],'webbing',width=1.3)
    r.layer('11_thigh_strap')
    r.shape([('M',112,203),('L',144,201),('L',143,207),
             ('L',114,209)],'belt',width=1.7)


def draw(r, direction, sleeve_style='short'):
    if direction=='east': side(r,sleeve_style)
    else: front_or_back(r,direction=='north',sleeve_style)


class SVGRecorder:
    def __init__(self,palette,line):
        self.palette=palette;self.line=line;self.parts=[];self.open_group=False

    def layer(self,name):
        if self.open_group:self.parts.append('</g>')
        self.parts.append(f'<g id="{escape(name)}">');self.open_group=True

    @staticmethod
    def path(commands):
        return ' '.join(cmd[0]+' '+' '.join(str(v) for v in cmd[1:]) for cmd in commands)

    def shape(self,path,fill,stroke=True,width=None):
        self.parts.append(f'<path d="{self.path(path)} Z" fill="{self.palette.get(fill,fill)}" '
                          f'stroke="{self.palette["outline"] if stroke else "none"}" stroke-width="{width or self.line}"/>')

    def linepath(self,path,color=None,width=1.3):
        self.parts.append(f'<path d="{self.path(path)}" fill="none" stroke="{color or self.palette["outline"]}" stroke-width="{width}"/>')

    def dot(self,x,y,r,color):
        self.parts.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{self.palette.get(color,color)}"/>')

    def finish(self,transform):
        if self.open_group:self.parts.append('</g>');self.open_group=False
        content='\n'.join(self.parts)
        return ('<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256">\n'
                '<title>Fitted tactical body — AI-assisted editable vector</title>\n'
                f'<g transform="{transform}" stroke-linejoin="round" stroke-linecap="round">\n{content}\n</g>\n</svg>\n')


def svg_document(recipe,direction):
    palette={**ACCENTS,**recipe['palette']};p=recipe['parameters']
    recorder=SVGRecorder(palette,float(p.get('outline_px',3)))
    draw(recorder,direction,p.get('sleeve_style','short'))
    x0,y0,x1,y1=p['body_bbox']
    # A shared fixed coordinate frame preserves the designed shoulder/hip ratio.
    transform=f'translate({x0} {y0}) scale({(x1-x0)/84} {(y1-y0)/162}) translate(-86 -90)'
    return recorder.finish(transform)
