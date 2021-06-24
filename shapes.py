from lottie.nvector import NVector, Point
from lottie.objects import Path, Bezier
import logging
## @ingroup Lottie
class TextBox(Path):
    def __init__(self, pos=None, size=None, rounded=0, pointer=None):
        Path.__init__(self)
        ## Rect's position
        position = pos or Point(0, 0)
        ## Rect's size
        size = size or Point(0, 0)
        ## Rect's rounded corners
        rounded = rounded or 0
        pointer = pointer or (size + position)
        logging.debug("Pos %s Size %s round %s Pointer %s", pos, size, rounded, pointer)
        tl = position
        tr = position + Point(size.x, 0)
        br = position + size
        bl = position + Point(0, size.y)
        logging.debug("TL %s TR %s BR %s BL %s", tl, tr, br, bl)

        hh = Point(rounded/2, 0)
        vh = Point(0, rounded/2)
        hd = Point(rounded, 0)
        vd = Point(0, rounded)
        bezier = Bezier()
        bezier.add_point(tl+vd, outp=-vh)
        bezier.add_point(tl+hd, -hh)
        bezier.add_point(tr-hd, outp=hh)
        bezier.add_point(tr+vd, -vh)
        bezier.add_point(br-vd, outp=vh)
        bezier.add_point(br-hd, hh)
        bezier.add_point(br - vd)
        bezier.add_point(pointer)
        bezier.add_point(br - hd)
        bezier.add_point(bl+hd, outp=-hh)
        bezier.add_point(bl-vd, vh)

        bezier.close()
        self.shape.value = bezier
