import sys
import os
import random
import math
import grapheme
from lottie.utils import animation as anutils
from lottie.utils.font import FontStyle
from lottie import Color, Point, PolarVector
from lottie.parsers.svg import parse_svg_file
from lottie import objects, exporters
import stickers

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "lib"
))

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


class CendyneBreathes:
    def __init__(self):
        self.sticker = parse_svg_file(os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "assets/cendyne-smol.svg"
        )).layers[0]
        self.sticker.transform.position.value.y = 340

    def textToSticker(self, text, particle_count):

        style = FontStyle("Comic Mono", 300, emoji_svg="emojis/")

        an = objects.Animation(59)
        an.height = 1024
        an.width = 1024

        elements = list(grapheme.graphemes(text))
        le = len(elements)
        if le > 0:
            for i in range(0, particle_count):
                layer = objects.ShapeLayer()
                an.insert_layer(0, layer)
                t = layer.add_shape(style.render(elements[i % le]))
                layer.add_shape(objects.Fill(Color(0, 0, 0)))
                layer.add_shape(objects.Stroke(Color(1, 1, 1), width=40))

                t.transform.position.value.y += t.line_height
                layer.transform.position.value = particle_start.clone()
                layer.transform.scale.value = particle_scale.clone()

                t = i / particle_count
                for thing in layer.shapes:
                    if hasattr(thing, 'opacity'):
                        thing.opacity.add_keyframe(
                            0, opacity_start + (opacity_end - opacity_start) * t)
                        thing.opacity.add_keyframe(
                            (1 - t) * last_frame, opacity_end)
                        thing.opacity.add_keyframe(
                            (1 - t) * last_frame+1, opacity_start)
                        thing.opacity.add_keyframe(
                            last_frame, opacity_start + (opacity_end - opacity_start) * t)
                    elif hasattr(thing, 'shapes'):
                        for thingy in thing.shapes:
                            if hasattr(thingy, 'opacity'):
                                thingy.opacity.add_keyframe(
                                    0, opacity_start + (opacity_end - opacity_start) * t)
                                thingy.opacity.add_keyframe(
                                    (1 - t) * last_frame, opacity_end)
                                thingy.opacity.add_keyframe(
                                    (1 - t) * last_frame+1, opacity_start)
                                thingy.opacity.add_keyframe(
                                    last_frame, opacity_start + (opacity_end - opacity_start) * t)

                bezier = objects.Bezier()
                outp = PolarVector(random.uniform(
                    start_len_min, start_len_max), random.random() * math.pi)
                angle = (random.random() * 2 - 1) * math.pi * 0.2
                local_particle_end = particle_start.clone()
                local_particle_end.x += partical_radius * math.cos(angle)
                local_particle_end.y += partical_radius * math.sin(angle)
                bezier.add_point(particle_start, outp=outp)
                bezier.add_point(local_particle_end, outp)

                # b.size.value = particle_size
                anutils.follow_path(layer.transform.position,
                                    bezier, 0, last_frame, 10, start_t=t)
            # No more particles
            an.add_layer(self.sticker.clone())

        exporters.export_tgs(an, stickers.tempPath(text), True, False)

    # exporters.export_svg(an, "says.svg")

    def makeSticker(self, text, count=10):
        self.textToSticker(text, count)
        return stickers.tempPath(text)
