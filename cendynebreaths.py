import sys
import os
import random
import math
import logging

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "lib"
))

import grapheme
from lottie.utils import animation as anutils
from lottie.utils.font import FontStyle
from lottie.objects import easing
from lottie import Color, Point, PolarVector, NVector
from lottie.parsers.svg import parse_svg_file
from lottie import objects, exporters
import stickers



particle_start_single = Point(520, 280)
particle_start = Point(380, 500)
particle_scale = Point(50, 50)
particle_end = Point(1000, -100)
partical_radius = 1200.0
start_len_min = 0
start_len_max = 60
opacity_start = 100
opacity_end = 0
last_frame = 60


def follow_path(position_prop, bezier, start_time, end_time, n_keyframes,
                reverse=False, offset=NVector(0, 0), start_t=0):
    delta = (end_time - start_time) / (n_keyframes-1)
    fact = start_t
    factd = 1 / (n_keyframes-1)

    jumps = 0
    handled_jump = False
    for i in range(n_keyframes):
        time = start_time + i * delta
        if fact > 1 + factd/2:
            fact -= 1
            if time != start_time:
                jumps += 1
                easing.Jump()(position_prop.keyframes[-1])

        f = 1 - fact if reverse else fact
        position_prop.add_keyframe(time, bezier.point_at(f)+offset)
        if jumps == 1 and not handled_jump:
            # Hide it by shoving it off canvas
            x = position_prop.keyframes[-2]
            position_prop.add_keyframe(x.time + 1, NVector(1500,1500))
            easing.Jump()(position_prop.keyframes[-1])
            handled_jump = True

        fact += factd


class CendyneBreathes:
    def __init__(self):
        self.sticker = parse_svg_file(os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "assets/cendyne-smol.svg"
        )).layers[0]
        self.sticker.transform.position.value.y = 340

    def textToSticker(self, text, particle_count, reverse=False):

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

                bezier = objects.Bezier()
                outp = PolarVector(random.uniform(
                    start_len_min, start_len_max), random.random() * math.pi)
                angle = (random.random() * 2 - 1) * math.pi * 0.2
                local_particle_end = particle_start.clone()
                local_particle_end.x += partical_radius * math.cos(angle)
                local_particle_end.y += partical_radius * math.sin(angle)
                if reverse:
                    bezier.add_point(local_particle_end, outp=outp)
                    bezier.add_point(particle_start, outp)
                else:
                    bezier.add_point(particle_start, outp=outp)
                    bezier.add_point(local_particle_end, outp)

                follow_path(layer.transform.position,
                            bezier, 0, last_frame, 10, start_t=t)

            # No more particles
            an.add_layer(self.sticker.clone())

        exporters.export_tgs(an, stickers.tempPath(text), True, False)

    # exporters.export_svg(an, "says.svg")

    def makeSticker(self, text, count=10, reverse=False):
        self.textToSticker(text, count, reverse)
        return stickers.tempPath(text)
