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
from lottie.parsers.svg import parse_svg_file
from lottie.utils.animation import spring_pull
from lottie import Color, Point
from lottie.utils.font import FontStyle
import stickers
from PIL import Image
import logging

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
    style = FontStyle("Roboto", 300, emoji_svg="emojis/")

    an = self.sticker.clone()

    if len(text) > 0:
      layer = objects.ShapeLayer()
      an.add_layer(layer)
      t = layer.add_shape(style.render(text))
      bb = t.bounding_box()

      layer.add_shape(objects.Fill(Color(0, 0, 0)))
      
      t.transform.position.value.y += t.line_height
      layer.transform.position.value = particle_start.clone()
      layer.transform.scale.value = particle_scale.clone()
      # print("bb", bb)
      w = bb.width
      if w > 800:
        f = 800 / w
        layer.transform.scale.value.x *= f
        layer.transform.scale.value.y *= f
        # Add stroke with dynamic scaling to text
        layer.add_shape(objects.Stroke(Color(1, 1, 1), width=40 * (0.5 / f)))
      else:
        layer.add_shape(objects.Stroke(Color(1, 1, 1), width=40))
    exporters.export_tgs(an, stickers.tempPath(text), True, False)

  def imageToSticker(self, img, id):
    sticker = Image.new('RGBA', (512,512))
    sticker.paste(img)
    sticker.paste(self.img, (0,0), self.img)
    path = stickers.tempPathExt(id, "webp")
    sticker.save(path)
    return path
  
  def animatedToStickerSvg(self, file, id, max_width, max_height):
    an = self.sticker.clone()
    svg = parse_svg_file(file).layers[0]
    bb = objects.shapes.BoundingBox()
    svg.out_point = an.out_point
    for shape in svg.shapes:
      bb.expand(shape.bounding_box())
    l = an.add_layer(svg.clone())
    
    logging.debug("Bounding box %s", bb)

    wpercent = float(max_width) / bb.width
    hpercent = float(max_height)/ bb.height
    minpercent = min(wpercent, hpercent)

    l.transform.scale.value.x = minpercent * 100.0
    l.transform.scale.value.y = minpercent * 100.0
    l.transform.position.value.x = -1 * bb.x1 * minpercent
    l.transform.position.value.y = -1 * bb.y1 * minpercent - (max_height / 4)

    spring_pull(l.transform.position, Point(-1 * bb.x1 * minpercent, -1 * bb.y1 * minpercent + (max_height / 4)), 0, int(an.out_point * 0.5), 30, 7)
    l.transform.position.add_keyframe(int(an.out_point * 0.8), Point(-1 * bb.x1 * minpercent, -1 * bb.y1 * minpercent - (max_height / 4)))

    path = stickers.tempPath(id)
    exporters.export_tgs(an, path, True, False)
    return path


  def animatedToSticker(self, file, id):
    an = objects.Animation(self.sticker.out_point, self.sticker.frame_rate)
    yellUuid = str(uuid.uuid4())
    precomp = objects.Precomp(yellUuid, an)
    for asset in self.sticker.assets:
      an.assets.append(asset.clone())
    for layer in self.sticker.layers:
      precomp.add_layer(layer.clone())
    an.add_layer(objects.PreCompLayer(yellUuid))

    yellTime = (self.sticker.out_point - self.sticker.in_point) / self.sticker.frame_rate
    # print("yell out point ", self.sticker.out_point, " yell frame rate", self.sticker.frame_rate, " yell time " , yellTime)

    sticker = parse_tgs(file)

    importUuid = str(uuid.uuid4())
    precomp = objects.Precomp(importUuid, an)
    for asset in sticker.assets:
      an.assets.append(asset.clone())
    for layer in sticker.layers:
      precomp.add_layer(layer.clone())

    stickerTime = (sticker.out_point - sticker.in_point) / sticker.frame_rate
    
    # print("in point ", sticker.in_point, " out point ", sticker.out_point, " frame rate", sticker.frame_rate, " time ", stickerTime)

    # print("Difference y/s: ", yellTime / stickerTime)
    # print("Difference s/y: ", stickerTime / yellTime)
    # print("Difference 1/y: ", 1 / yellTime)
    # print("Difference 1/s: ", 1 / stickerTime)

    player = an.add_layer(objects.PreCompLayer(importUuid))
    # player.time_remapping.add_keyframe(an.out_point, 1)
    player.transform.scale.value = Point(50, 50)
    player.stretch = yellTime / stickerTime * (an.frame_rate / sticker.frame_rate)
    if sticker.in_point != 0:
      # The stretch facter affects the start time
      # Set the start time to the in_point.. but in reverse relative to the yell sticker
      player.start_time = -1 * sticker.in_point * player.stretch
    # print("stretch ", player.stretch)
    
    
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

  def makeStickerAnimatedSvg(self, file, max_width, max_height):
    id = str(uuid.uuid4())
    return self.animatedToStickerSvg(file, id, max_width, max_height)