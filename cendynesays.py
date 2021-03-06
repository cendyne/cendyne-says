import os
import sys
import logging

import grapheme
from lottie.objects import BoundingBox
from lottie.utils.font import FontStyle
from lottie import Color, Point
from lottie.parsers.svg import parse_svg_file
from lottie import objects, exporters
import shapes
import stickers





class CendyneSays:
    def __init__(self):
        
        if os.getenv("USE_GLEAM") is not None:
            self.sticker = parse_svg_file(os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "assets/gleamburp.svg"
            )).layers[0]
            self.sticker.transform.position.value.x = 280
            self.sticker.transform.position.value.y = 190
        else:
            self.sticker = parse_svg_file(os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "assets/cendyne-says.svg"
            )).layers[0]
            self.sticker.transform.position.value.x = 85
            self.sticker.transform.position.value.y = 90

    def splitWords(self, text, num):
        words = text.split(" ")
        for word in words:
            if len(word) > num:
                for i in range(0, len(word), num):
                    yield grapheme.slice(word, start=i, end=i+num)
            else:
                yield word

    def textToSticker(self, input_text):
        text = input_text.replace("\n", "")
        words = self.splitWords(text, 14)

        style = FontStyle("DejaVu Sans", 180, emoji_svg="emojis/")

        textlayers = []

        an = objects.Animation(1)
        an.height = 1024
        an.width = 1024

        for index, word in enumerate(words, start=1):
            if len(word) == 0:
                continue
            layer = objects.ShapeLayer()
            an.add_layer(layer)
            # print("word: ", word)
            logging.info("Word %s", word)
            t = layer.add_shape(style.render(word))

            layer.add_shape(objects.Fill(Color(0, 0, 0)))
            textlayers.append(
                {"t": t, "l": layer, "bb": t.bounding_box(), "lh": t.line_height, "w": word})

            t.transform.position.value.y += t.line_height
            layer.transform.position.value.x = 0
            layer.transform.position.value.y = 0

        max_w = 0
        max_h = 0
        y = 0
        textbb = BoundingBox()

        if len(textlayers) > 0:
            START_X = 35
            START_Y = 30
            SPACE_W = 80
            MAX_X = 450
            TOLERANCE_X = 20
            MAX_Y = 320
            for i in range(1, 399):
                y = START_Y
                line = 0
                x = START_X
                factor = 1 - (i * 0.0025)
                textbb = BoundingBox()
                # print("Factor ", factor)
                wordLineCount = 0
                unfit = False
                for index, tl in enumerate(textlayers, start=1):
                    bb = tl["bb"]
                    if bb is None:
                        # This text thing isn't real.
                        continue
                    if x > MAX_X:
                        # Move to the next line
                        y += tl["lh"] * factor
                        x = START_X
                        wordLineCount = 0
                    if wordLineCount > 0:
                        x += factor * SPACE_W  # TODO adjust
                    lh = tl["lh"] * factor
                    pos = tl["l"].transform.position.value
                    pos.x = x
                    pos.y = y
                    textbb.include(x, y)
                    scale = tl["l"].transform.scale.value
                    scale.x = factor * 100
                    scale.y = factor * 100
                    width = (bb.x2 - bb.x1) * factor
                    if wordLineCount > 0:
                        if x + width > MAX_X:
                            x = START_X
                            y += lh
                            pos.x = x
                            pos.y = y
                            x += width
                            wordLineCount = 1
                        else:
                            x += width
                            wordLineCount += 1
                            # print(tl["w"], " ", pos, " width ", width)
                    else:
                        x += width
                        wordLineCount += 1
                        # print(tl["w"], " ", pos, " width ", width)
                    textbb.include(x, y + lh * 1.25)
                    if y + lh > MAX_Y:
                        unfit = True
                        break
                    if wordLineCount == 1 and x > (MAX_X + TOLERANCE_X):
                        unfit = True
                        break
                if unfit:
                    continue
                break

        textboxLayer = an.add_layer(objects.ShapeLayer())
        logging.info("Bounding box for text %s", textbb)
        if os.getenv("USE_GLEAM") is not None:
            textboxLayer.add_shape(shapes.TextBox(Point(
                textbb.x1 - 20, textbb.y1), textbb.size() + Point(60, 20), 40, Point(550, 350)))
        else:
            textboxLayer.add_shape(shapes.TextBox(Point(
                textbb.x1 - 20, textbb.y1), textbb.size() + Point(60, 20), 40, Point(550, 400)))
        fill = textboxLayer.add_shape(objects.Fill(Color(1, 1, 1)))
        stroke = textboxLayer.add_shape(objects.Stroke(Color(0, 0, 0), 10))

        # an.add_layer(self.chatBubble.clone())
        an.add_layer(self.sticker.clone())

        exporters.export_tgs(an, stickers.tempPath(input_text), True, False)

    # exporters.export_svg(an, "says.svg")

    def makeSticker(self, text):
        if stickers.stickerExists(text):
            return stickers.tempPath(text)

        self.textToSticker(text)
        return stickers.tempPath(text)
