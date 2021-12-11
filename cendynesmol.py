import sys
import os
import logging

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "lib"
))

import grapheme
from lottie.utils.animation import shake, rot_shake
from lottie.utils.font import FontStyle
from lottie import Color, Point
from lottie.parsers.svg import parse_svg_file
from lottie import objects, exporters
import stickers


particle_start = Point(520, 280)
particle_scale = Point(50, 50)


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

    @property
    def actNormal(self):
        return 0

    @property
    def actExclaim(self):
        return 1

    @property
    def actQuestion(self):
        return 2

    def textToSticker(self, text, act=0):
        style = FontStyle("Comic Mono", 300, emoji_svg="emojis/")

        an = objects.Animation(59)
        an.height = 1024
        an.width = 1024

        elements = list(grapheme.graphemes(text))
        printtext = elements[0]

        if not (act in [0, 1, 2]):
            printtext = ""
            for i in elements:
                printtext += i

        if len(elements) > 0:
            layer = objects.ShapeLayer()
            an.insert_layer(0, layer)
            t = layer.add_shape(style.render(printtext))
            layer.add_shape(objects.Fill(Color(0, 0, 0)))
            layer.add_shape(objects.Stroke(Color(1, 1, 1), width=40))

            t.transform.position.value.y += t.line_height
            layer.transform.position.value = particle_start.clone()
            layer.transform.scale.value = particle_scale.clone()
            # print("Act ", act)
            logging.debug("Act Variant %d", act)
            if act == 0:
                shake(layer.transform.position, 10, 15, 0, 59, 25)
            elif act == 1:
                shake(layer.transform.position, 40, 60, 0, 59, 25)
            elif act == 2:
                rot_shake(layer.transform.rotation, Point(-15, 15), 0, 60, 10)
            else:
                logging.info("No action detected for %d", act)
                # print("No action detected")
            an.add_layer(self.sticker.clone())
            an.add_layer(self.stickerdash.clone())
        exporters.export_tgs(an, stickers.tempPath(text), True, False)

    def makeSticker(self, text, act=0):
        if stickers.stickerExists(text):
            return stickers.tempPath(text)

        self.textToSticker(text, act)
        return stickers.tempPath(text)
