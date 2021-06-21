import os
import hashlib
import logging

def deleteSticker(sticker):
  if os.path.exists(sticker):
    os.unlink(sticker)

def validSize(sticker):
  if os.path.exists(sticker):
    return os.path.getsize(sticker) < 64000
  else:
    logging.warn("No sticker could be exported, the file is missing")
    # print("ERROR no sticker could be exported")
    return False

def tempPath(input):
  return './temp/' + hashlib.md5(input.encode('utf-8')).hexdigest() + '.tgs'

def tempPathExt(input, ext):
  return './temp/' + hashlib.md5(input.encode('utf-8')).hexdigest() + '.' + ext

def stickerExists(input):
  return False
