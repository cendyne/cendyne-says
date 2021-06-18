from dotenv import load_dotenv

import logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from telegram import InlineQueryResultArticle, ParseMode, InputTextMessageContent, Update, InlineQueryResultCachedSticker
from telegram.ext import Updater, InlineQueryHandler, CommandHandler, CallbackContext, ChatMemberHandler, MessageHandler, Filters
from telegram.utils.helpers import escape_markdown

import stickers
import sys
import os
import traceback
import emoji
from cendyneyells import CendyneYells
from PIL import Image

load_dotenv()

token = os.environ["YELL_TOKEN"]

yell = CendyneYells()

def makeSticker(text):
  try:
    text = emoji.demojize(text, use_aliases=True)
    # print(text)
    text = emoji.emojize(text, use_aliases=True)
    # print(text.encode("raw_unicode_escape").decode("latin_1"))
  except Exception as ex:
    print(ex)
    pass
  return yell.makeSticker(text)

def makeImageSticker(img):
  return yell.makeStickerImg(img)

def makeAnimatedSticker(file):
  return yell.makeStickerAnimated(file)

def start(update: Update, _: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    print(update)
    update.message.reply_text('Use @CendyneSaysBot text here to make a message')


def messageHandler(update: Update, c: CallbackContext) -> None:
  print("Message handler!!!", update)
  try:
    if update.message:
      if update.message.text:
        sticker = makeSticker(update.message.text)
        result = update.message.reply_document(document=open(sticker, "rb"))
        c.bot.send_document(chat_id=-1001346187913, document=result.sticker.file_id)
        print("Result:", result)
        stickers.deleteSticker(sticker)
      elif update.message.photo:
        print("Got image")
        photo = update.message.photo[len(update.message.photo)-1]
        f = c.bot.get_file(photo.file_id)
        path = stickers.tempPathExt(photo.file_id, "jpg")
        f.download(path)
        print("got file ", f)
        img = Image.open(path)
        wpercent = (256/float(img.size[0]))
        hsize = int((float(img.size[1])*float(wpercent)))
        resized = img.resize((256,hsize))
        sticker = makeImageSticker(resized)
        result = update.message.reply_sticker(sticker=open(sticker, "rb"))
        c.bot.send_document(chat_id=-1001346187913, document=result.sticker.file_id)
        print("Result:", result)
        stickers.deleteSticker(sticker)
        os.unlink(path)
      elif update.message.sticker:
        if update.message.sticker.is_animated:
          f = c.bot.get_file(update.message.sticker.file_id) 
          path = stickers.tempPathExt(update.message.sticker.file_id, "tgs")
          f.download(path)
          sticker = makeAnimatedSticker(path)
          if stickers.validSize(sticker):
            result = update.message.reply_sticker(sticker=open(sticker, "rb"))
            c.bot.send_document(chat_id=-1001346187913, document=result.sticker.file_id)
            print("Result:", result)
          else:
            # Delete the too big sticker
            stickers.deleteSticker(sticker)
            # Make a new one saying too big
            sticker = makeSticker("File Size\nToo Big!")
            result = update.message.reply_document(document=open(sticker, "rb"))
            # No need to send it to the channel
            # c.bot.send_document(chat_id=-1001346187913, document=result.sticker.file_id)
            pass
          
          stickers.deleteSticker(sticker)
          os.unlink(path)
        else:
          f = c.bot.get_file(update.message.sticker.file_id) 
          path = stickers.tempPathExt(update.message.sticker.file_id, "webp")
          f.download(path)
          img = Image.open(path)
          wpercent = (256/float(img.size[0]))
          hsize = int((float(img.size[1])*float(wpercent)))
          resized = img.resize((256,hsize))
          sticker = makeImageSticker(resized)
          result = update.message.reply_sticker(sticker=open(sticker, "rb"))
          c.bot.send_document(chat_id=-1001346187913, document=result.sticker.file_id)
          print("Result:", result)
          stickers.deleteSticker(sticker)
          os.unlink(path)
      else:
        update.message.reply_text("unsupported")
        return
  except Exception as ex:
      print("A problem I guess")
      traceback.print_exception(*sys.exc_info())
  


def main() -> None:
    # Create the Updater and pass it your bot's token.
    updater = Updater(token)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("start", start))

    # on non command i.e message - echo the message on Telegram
    dispatcher.add_handler(ChatMemberHandler(messageHandler))
    dispatcher.add_handler(MessageHandler(Filters.all, messageHandler))

    # Start the Bot
    updater.start_polling()

    # Block until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()