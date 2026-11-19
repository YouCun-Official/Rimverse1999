"""Meaningful format, analysis, preservation, and renderer regression checks."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from PIL import Image, ImageDraw
from portrait_to_pawn import analyze_portrait, generate, render_body, validate_recipe


def portrait(path,shirt=(245,245,247),transparent=True):
    im=Image.new('RGBA',(256,320),(0,0,0,0) if transparent else (255,255,255,255))
    d=ImageDraw.Draw(im)
    d.ellipse((75,12,181,155),fill=(31,29,35))
    d.ellipse((94,52,164,148),fill=(237,190,166))
    d.rectangle((117,134,141,171),fill=(237,190,166))
    d.polygon([(42,183),(95,158),(117,165),(141,165),(171,158),(215,185),(230,319),(25,319)],fill=shirt,outline=(24,24,29),width=3)
    d.polygon([(87,162),(112,173),(109,319),(65,319)],fill=(35,35,42))
    d.polygon([(144,173),(168,162),(193,319),(151,319)],fill=(35,35,42))
    im.save(path)


class TextureTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'portrait.png';portrait(self.source)
        self.recipe=analyze_portrait(self.source)

    def test_auto_palette_and_vest_detection(self):
        self.assertEqual(self.recipe['family'],'shirt_vest')
        self.assertGreater(min(int(self.recipe['palette']['shirt'][i:i+2],16) for i in (1,3,5)),200)
        self.assertLess(max(int(self.recipe['palette']['vest'][i:i+2],16) for i in (1,3,5)),80)

    def test_format_alpha_and_anchors(self):
        im,_=render_body(self.recipe,'south');a=np.asarray(im)
        self.assertEqual(im.mode,'RGBA');self.assertEqual(im.size,(256,256))
        self.assertEqual(int(a[0,:,3].max()),0);self.assertEqual(int(a[:,0,3].max()),0)
        ys,xs=np.where(a[:,:,3]>=128)
        # The broad flat body is intentionally near Texas width; the frame is fixed.
        self.assertGreaterEqual(xs.min(),86);self.assertLessEqual(xs.max()+1,170)
        self.assertGreaterEqual(xs.max()+1-xs.min(),78)
        self.assertLessEqual(xs.max()+1-xs.min(),84)
        self.assertLessEqual(abs(ys.min()-90),1);self.assertLessEqual(abs(ys.max()+1-252),1)

    def test_directions_are_distinct_and_deterministic(self):
        output=[render_body(self.recipe,d)[0].tobytes() for d in ['south','east','north']]
        self.assertEqual(len(set(output)),3)
        self.assertEqual(output[0],render_body(self.recipe,'south')[0].tobytes())

    def test_palette_override_changes_sleeve_pixels(self):
        first=np.asarray(render_body(self.recipe,'south')[0]).copy()
        self.recipe['palette']['shirt']='#cf4444'
        second=np.asarray(render_body(self.recipe,'south')[0])
        changed=np.any(first[:,:,:3]!=second[:,:,:3],axis=2)
        self.assertGreater(int(changed.sum()),400)
        # Trousers remain identical when only the shirt changes.
        np.testing.assert_array_equal(first[214:235,110:140],second[214:235,110:140])

    def test_background_removal_preserves_subject(self):
        path=self.root/'opaque.png';portrait(path,transparent=False)
        info=analyze_portrait(path)
        self.assertEqual(info['analysis']['background_method'],'border_connected_background')
        self.assertEqual(info['family'],'shirt_vest')

    def test_manual_families_have_distinct_shapes(self):
        hashes=[]
        for family in ('shirt_vest','coat','dress'):
            self.recipe['family']=family
            hashes.append(hashlib.sha256(render_body(self.recipe,'south')[0].tobytes()).hexdigest())
        self.assertEqual(len(set(hashes)),3)

    def test_export_preserves_source_and_refuses_overwrite(self):
        before=self.source.read_bytes();out=self.root/'export'
        generate(self.source,out,'Example')
        paths=sorted((out/'Textures').rglob('*.png'))
        self.assertEqual(len(paths),4)
        self.assertEqual({p.name for p in paths},{'Example.png','Example_Thin_south.png','Example_Thin_east.png','Example_Thin_north.png'})
        self.assertEqual(before,self.source.read_bytes())
        hashes={str(p):p.read_bytes() for p in paths}
        with self.assertRaises(ValueError):generate(self.source,out,'Example')
        for path,data in hashes.items():self.assertEqual(Path(path).read_bytes(),data)
        manifest=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
        self.assertFalse(manifest['head_generated'])

    def test_bad_recipe_rejected_before_output(self):
        self.recipe['parameters']['body_bbox']=[-10,0,500,256]
        with self.assertRaises(ValueError):validate_recipe(self.recipe)

    def test_path_name_rejected(self):
        with self.assertRaises(ValueError):generate(self.source,self.root/'out','../escape')
        self.assertFalse((self.root/'out').exists())

    def test_no_skin_below_collar_in_all_directions(self):
        for family in ('shirt_vest','coat','dress'):
            self.recipe['family']=family
            for direction in ('south','east','north'):
                self.recipe['palette']['skin']='#ff00ff'
                first=np.asarray(render_body(self.recipe,direction)[0]).copy()
                self.recipe['palette']['skin']='#00ff00'
                second=np.asarray(render_body(self.recipe,direction)[0])
                self.assertTrue(np.any(first[:135]!=second[:135]))
                np.testing.assert_array_equal(first[135:],second[135:],err_msg=f'{family}/{direction}: skin below collar')

    def test_sleeve_toggle_changes_only_shoulder_region(self):
        for family in ('shirt_vest','coat','dress'):
            self.recipe['family']=family
            for direction in ('south','east','north'):
                self.recipe['parameters']['sleeve_style']='short'
                short=np.asarray(render_body(self.recipe,direction)[0]).copy()
                self.recipe['parameters']['sleeve_style']='none'
                none=np.asarray(render_body(self.recipe,direction)[0])
                self.assertGreater(int(np.any(short!=none,axis=2).sum()),20)
                np.testing.assert_array_equal(short[135:],none[135:],err_msg=f'{family}/{direction}: torso or legs resized')

    def test_full_sleeves_are_not_a_supported_style(self):
        self.recipe['parameters']['sleeve_style']='full'
        with self.assertRaises(ValueError):validate_recipe(self.recipe)

    def test_broad_torso_and_trousers_match_requested_width(self):
        alpha=np.asarray(render_body(self.recipe,'south')[0])[:,:,3]
        for y,low,high in [(135,58,70),(165,60,76),(205,60,72)]:
            xs=np.where(alpha[y]>=128)[0]
            self.assertTrue(low<=xs.max()+1-xs.min()<=high,(y,xs.max()+1-xs.min()))

    def test_flat_material_interiors_have_no_lighting_variation(self):
        im=np.asarray(render_body(self.recipe,'south')[0])
        from portrait_to_pawn import rgb
        for box,key in [((108,145,120,155),'vest'),((116,212,122,216),'pants'),((114,245,121,247),'shoes')]:
            x0,y0,x1,y1=box;area=im[y0:y1,x0:x1]
            self.assertTrue(np.all(area[:,:,3]==255),key)
            self.assertTrue(np.all(area[:,:,:3]==rgb(self.recipe['palette'][key])),key)

    def test_flat_templates_use_palette_colors_without_added_highlights(self):
        import flat_renderer
        from portrait_to_pawn import rgb
        palette={k:rgb(v) for k,v in self.recipe['palette'].items()}
        class Recorder:
            def __init__(self):self.colors=[]
            def layer(self,name):pass
            def shape(self,path,fill,stroke=True,width=None):self.colors.append(palette.get(fill,fill))
            def linepath(self,path,color=None,width=1):self.colors.append(color or palette['outline'])
            def dot(self,x,y,r,color):self.colors.append(palette.get(color,color))
        for family in ('shirt_vest','coat','dress'):
            recorder=Recorder()
            flat_renderer.front_or_back(recorder,False,family)
            flat_renderer.front_or_back(recorder,True,family)
            flat_renderer.side(recorder,family)
            self.assertGreater(len(recorder.colors),30)
            self.assertTrue(set(recorder.colors)<=set(palette.values()))

    def test_closed_legs_taper_into_wider_continuous_foot_base(self):
        for direction in ('south','north','east'):
            alpha=np.asarray(render_body(self.recipe,direction)[0])[:,:,3]
            def run_width(y):
                xs=np.where(alpha[y]>=128)[0]
                self.assertTrue(np.all(alpha[y,xs.min():xs.max()+1]>=128),(direction,y))
                return xs.max()+1-xs.min()
            thigh=run_width(208);ankle=run_width(234);sole=run_width(247)
            self.assertLess(ankle,thigh-12,(direction,thigh,ankle))
            self.assertGreater(sole,ankle+12,(direction,ankle,sole))
            self.assertTrue(np.all(alpha[215:249,126:129]>=128),direction)

    def test_fitted_preset_has_high_waist_wider_hips_and_vertical_feet(self):
        self.recipe['parameters']['render_style']='fitted_tactical'
        for direction in ('south','north'):
            alpha=np.asarray(render_body(self.recipe,direction)[0])[:,:,3]
            def width(y):
                xs=np.where(alpha[y]>=128)[0]
                return xs.max()+1-xs.min()
            self.assertGreater(width(180),width(117)+4)
            self.assertLess(width(164),width(117)-18)
            self.assertLessEqual(width(247),width(229)+4)
            # Straight outer contours: intermediate rows remain on the line.
            for side in ('left','right'):
                def edge(y):
                    xs=np.where(alpha[y]>=128)[0]
                    return xs.min() if side=='left' else xs.max()
                start,end=edge(211),edge(225)
                for y in range(212,225):
                    expected=start+(end-start)*(y-211)/14
                    self.assertLessEqual(abs(edge(y)-expected),1.2)

    def test_fitted_svg_uses_flat_palette_and_named_editable_layers(self):
        import xml.etree.ElementTree as ET
        import fitted_renderer
        self.recipe['parameters']['render_style']='fitted_tactical'
        allowed=set({**fitted_renderer.ACCENTS,**self.recipe['palette']}.values())|{'none'}
        for direction in ('south','east','north'):
            svg=fitted_renderer.svg_document(self.recipe,direction)
            root=ET.fromstring(svg)
            self.assertEqual(root.attrib['viewBox'],'0 0 256 256')
            self.assertNotIn('Gradient',svg)
            self.assertNotIn('<image',svg)
            groups=[x for x in root.iter() if x.attrib.get('id')]
            self.assertGreaterEqual(len(groups),10)
            for element in root.iter():
                for attr in ('fill','stroke'):
                    if attr in element.attrib:self.assertIn(element.attrib[attr],allowed)

    def test_fitted_skin_and_sleeves_remain_only_at_neck_and_shoulders(self):
        self.recipe['parameters']['render_style']='fitted_tactical'
        for direction in ('south','east','north'):
            self.recipe['palette']['skin']='#ff00ff'
            self.recipe['parameters']['sleeve_style']='short'
            first=np.asarray(render_body(self.recipe,direction)[0]).copy()
            self.recipe['palette']['skin']='#00ff00'
            self.recipe['parameters']['sleeve_style']='none'
            second=np.asarray(render_body(self.recipe,direction)[0])
            self.assertTrue(np.any(first[:132]!=second[:132]))
            np.testing.assert_array_equal(first[132:],second[132:])

    def test_fitted_export_includes_reproducible_vector_source(self):
        override=self.root/'fitted.json'
        override.write_text(json.dumps({'family':'shirt_vest','parameters':{'render_style':'fitted_tactical'}}),encoding='utf-8')
        out=self.root/'fitted_export'
        _,recipe=generate(self.source,out,'Example',recipe_path=override)
        manifest=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(len(manifest['editable_vectors']),3)
        self.assertEqual(manifest['body_style']['leg_pose'],'straight_inward_legs_downward_boots')
        for name in manifest['editable_vectors']:self.assertTrue((out/name).is_file())
        for direction in ('south','east','north'):
            actual=Image.open(out/f'Textures/Things/R99_Agents/Arcanist/Example_Thin_{direction}.png')
            expected=render_body(recipe,direction)[0]
            self.assertEqual(actual.tobytes(),expected.tobytes())


if __name__=='__main__':unittest.main(verbosity=2)
