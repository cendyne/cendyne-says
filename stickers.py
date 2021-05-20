import os
import hashlib

def deleteSticker(sticker):
  os.unlink(sticker)

def validSize(sticker):
  return os.path.getsize(sticker) < 64000

def tempPath(input):
  return './temp/' + hashlib.md5(input.encode('utf-8')).hexdigest() + '.tgs'

def stickerExists(input):
  return False