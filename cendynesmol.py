import sys
import os
import grapheme
import random
import math

sys.path.insert(0, os.path.join(
  os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
  "lib"
))
from lottie.utils import script
from lottie import objects, exporters
from lottie.parsers.svg import parse_svg_file
from lottie import Color, Point, PolarVector
from lottie.utils.font import FontStyle
from lottie.utils.animation import shake, rot_shake
from lottie.utils import animation as anutils
import stickers

PARTICAL_COUNT = 40
particle_start_single = Point(520, 280)
particle_start = Point(380, 440)
particle_scale = Point(50, 50)
particle_end = Point(1000, -100)
partical_radius = 1200.0
start_len_min = 0
start_len_max = 60
opacity_start = 100
opacity_end = -20
last_frame = 60

class CendyneSmol:
  def __init__(self):
    self.sticker = parse_svg_file(os.path.join(
      os.path.dirname(os.path.abspath(__file__)),
      "assets/cendyne-smol.svg"
    )).layers[0]
    self.sticker.transform.position.value.y = 340

    self.stickerdash = parse_svg_file(os.path.join(
      os.path.dirname(os.path.abspath(__file__)),
      "assets/cendyne-smol-dash.svg"
    )).layers[0]
    self.stickerdash.transform.position.value.y = 340



  def textToSticker(self, text):

    style = FontStyle("Comic Mono", 300, emoji_svg="twemoji/assets/svg/")

    an = objects.Animation(59)
    an.height = 1024
    an.width = 1024

    act = 0

    elements = list(grapheme.graphemes(text))
    printtext = elements[0]

    if len(elements) == 2 and elements[1] == "!":
      act = 1
    elif len(elements) == 2 and elements[1] == "?":
      act = 2
    elif len(elements) == 3 and elements[0] == elements[1] and elements[1] == elements[2]:
      act = 3
    else:
      printtext = ""
      for i in elements:
        printtext += i


    if len(elements) > 0:
      if act in [0, 1, 2]:
        layer = objects.ShapeLayer()
        an.insert_layer(0, layer)
        t = layer.add_shape(style.render(printtext))
        layer.add_shape(objects.Fill(Color(0, 0, 0)))
        layer.add_shape(objects.Stroke(Color(1, 1, 1), width=40))

        t.transform.position.value.y += t.line_height
        layer.transform.position.value = particle_start_single.clone()
        layer.transform.scale.value = particle_scale.clone()
        print("Act ", act)
        if act == 0:
          shake(layer.transform.position, 10, 15, 0, 59, 25)
        elif act == 1:
          shake(layer.transform.position, 40, 60, 0, 59, 25)
        elif act == 2:
          rot_shake(layer.transform.rotation, Point(-15, 15), 0, 60, 10)
        else:
          print("No action detected")
        an.add_layer(self.sticker.clone())
        an.add_layer(self.stickerdash.clone())
        print("Set shake parameters")
      elif act == 3:
        for i in range(0, PARTICAL_COUNT):
          layer = objects.ShapeLayer()
          an.insert_layer(0, layer)
          t = layer.add_shape(style.render(printtext))
          fill = layer.add_shape(objects.Fill(Color(0, 0, 0)))
          stroke = layer.add_shape(objects.Stroke(Color(1, 1, 1), width=40))

          t.transform.position.value.y += t.line_height
          layer.transform.position.value = particle_start.clone()
          layer.transform.scale.value = particle_scale.clone()

          t = i / PARTICAL_COUNT
          for thing in layer.shapes:
            if hasattr(thing,'opacity'):
              thing.opacity.add_keyframe(0, opacity_start + (opacity_end - opacity_start) * t)
              thing.opacity.add_keyframe((1 - t) * last_frame, opacity_end)
              thing.opacity.add_keyframe((1 - t) * last_frame+1, opacity_start)
              thing.opacity.add_keyframe(last_frame, opacity_start + (opacity_end - opacity_start) * t)
            elif hasattr(thing, 'shapes'):
              for thingy in thing.shapes:
                if hasattr(thingy, 'opacity'):
                  thingy.opacity.add_keyframe(0, opacity_start + (opacity_end - opacity_start) * t)
                  thingy.opacity.add_keyframe((1 - t) * last_frame, opacity_end)
                  thingy.opacity.add_keyframe((1 - t) * last_frame+1, opacity_start)
                  thingy.opacity.add_keyframe(last_frame, opacity_start + (opacity_end - opacity_start) * t)

          bezier = objects.Bezier()
          outp = PolarVector(random.uniform(start_len_min, start_len_max), random.random() * math.pi)
          angle = (random.random() * 2 - 1) * math.pi * 0.2
          particle_end = particle_start.clone()
          particle_end.x += partical_radius * math.cos(angle)
          particle_end.y += partical_radius * math.sin(angle)
          # inp = Point(0,  random.random() * (particle_end.y - particle_start.y) / 3)
          bezier.add_point(particle_start, outp=outp)
          bezier.add_point(particle_end, outp)
        
          # b.size.value = particle_size
          anutils.follow_path(layer.transform.position, bezier, 0, last_frame, 10, start_t=t)
        # No more particles
        an.add_layer(self.sticker.clone())
   
    

    exporters.export_tgs(an, stickers.tempPath(text), True, False)

  # exporters.export_svg(an, "says.svg")

  def makeSticker(self, text):
    if stickers.stickerExists(text):
      return stickers.tempPath(text)
    
    self.textToSticker(text)
    return stickers.tempPath(text)


