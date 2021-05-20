import os
import hashlib

def deleteSticker(sticker):
  if os.path.exists(sticker):
    os.unlink(sticker)

def validSize(sticker):
  if os.path.exists(sticker):
    return os.path.getsize(sticker) < 64000
  else:
    print("ERROR no sticker could be exported")
    return False

def tempPath(input):
  return './temp/' + hashlib.md5(input.encode('utf-8')).hexdigest() + '.tgs'

def stickerExists(input):
  return False