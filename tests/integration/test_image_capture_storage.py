"""V2-T22/25: real file decoding and no-clobber PNG publishing."""
from pathlib import Path
import pytest
from PIL import Image
from hand_v2.adapters.image_files import load_images
from hand_v2.adapters.capture_files import atomic_png


def test_loader_natural_order_duplicates_bad_files_alpha_and_exif(tmp_path):
    Image.new('RGBA',(40,60),(0,20,50,80)).save(tmp_path/'slide10.PNG')
    im=Image.new('RGB',(30,50)); exif=Image.Exif(); exif[274]=6
    im.save(tmp_path/'slide2.JPG',exif=exif)
    (tmp_path/'bad.jpg').write_bytes(b'broken')
    (tmp_path/'sub').mkdir()
    Image.new('RGB',(2,2)).save(tmp_path/'sub'/'hidden.png')
    result=load_images([str(tmp_path),str(tmp_path/'slide10.PNG')])
    assert [Path(a.key).name for a in result.assets] == ['slide2.JPG','slide10.PNG']
    assert (result.assets[0].width,result.assets[0].height)==(50,30)
    assert result.assets[1].rgba[3] == 80
    assert len(result.excluded)==1 and 'bad.jpg' in result.excluded[0]


def test_png_publish_collision_and_failure_preserve_existing_files(tmp_path):
    im=Image.new('RGB',(32,33),'red')
    first=atomic_png(im,tmp_path,stamp='20261117_120000_001')
    second=atomic_png(im,tmp_path,stamp='20261117_120000_001')
    assert first != second
    assert Image.open(first).size == (32,33)
    assert len(list(tmp_path.glob('capture_*.png')))==2
    original=first.read_bytes()
    class Broken:
        size=(32,33)
        def save(self,path,**kw):
            Path(path).write_bytes(b'not a png')
    with pytest.raises(Exception): atomic_png(Broken(),tmp_path,stamp='same')
    assert first.read_bytes()==original
    assert not list(tmp_path.glob('*.tmp'))
