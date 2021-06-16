import sys
import os
import uuid
from lottie.objects.properties import OffsetKeyframe

sys.path.insert(0, os.path.join(
  os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
  "lib"
))
from lottie.utils import script
from lottie import objects, exporters
from lottie.parsers.tgs import parse_tgs
from lottie import Color, Point
from lottie.utils.font import FontStyle
import stickers
from PIL import Image

particle_start = Point(10, 0)
particle_scale = Point(50, 50)

class CendyneYells:
  def __init__(self):
    self.sticker = parse_tgs(os.path.join(
      os.path.dirname(os.path.abspath(__file__)),
      "assets/cendyne-yells.tgs"
    ))
    self.img = Image.open("assets/cendyne-yells.png")

  def textToSticker(self, text):
    style = FontStyle("Comic Mono", 300, emoji_svg="emojis/")

    an = self.sticker.clone()

    if len(text) > 0:
      layer = objects.ShapeLayer()
      an.insert_layer(0, layer)
      t = layer.add_shape(style.render(text))
      layer.add_shape(objects.Fill(Color(0, 0, 0)))
      layer.add_shape(objects.Stroke(Color(1, 1, 1), width=40))

      t.transform.position.value.y += t.line_height
      layer.transform.position.value = particle_start.clone()
      layer.transform.scale.value = particle_scale.clone()
    exporters.export_tgs(an, stickers.tempPath(text), True, False)

  def imageToSticker(self, img, id):
    sticker = Image.new('RGBA', (512,512))
    sticker.paste(img)
    sticker.paste(self.img, (0,0), self.img)
    path = stickers.tempPathExt(id, "webp")
    sticker.save(path)
    return path
  
  def animatedToSticker(self, file, id):
    an = self.sticker.clone()

    sticker = parse_tgs(file)

    an.out_point = max(an.out_point, sticker.out_point)

    for layer in an.layers:
      layer.out_point = an.out_point

    for layer in sticker.layers:
      l = objects.NullLayer()
      
      cloned = layer.clone()
      cloned.out_point = an.out_point
      an.insert_layer(0, l)
      l.add_child(cloned)
      l.transform.scale.value = Point(50, 50)
    
    path = stickers.tempPath(id)
    exporters.export_tgs(an, path, True, False)
    return path

  def makeSticker(self, text):
    self.textToSticker(text)
    return stickers.tempPath(text)

  def makeStickerImg(self, img):
    id = str(uuid.uuid4())
    return self.imageToSticker(img, id)

  def makeStickerAnimated(self, file):
    id = str(uuid.uuid4())
    return self.animatedToSticker(file, id)
