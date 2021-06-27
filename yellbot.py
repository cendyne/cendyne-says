from dotenv import load_dotenv

import logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from telegram import Update, Message, InlineQueryResultCachedSticker, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, InlineQueryHandler, CommandHandler, CallbackContext, ChatMemberHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram.utils.helpers import escape_markdown
import collections
import stickers
import sys
import os
import traceback
import emoji
from cendyneyells import CendyneYells
from PIL import Image
import uuid
import random
import textwrap
import yelldb
from typing import Text

load_dotenv()

token = os.environ["YELL_TOKEN"]
db = os.getenv("DB")

review_chan = int(os.getenv("REVIEW_CHAN"))
log_chan = int(os.getenv("LOG_CHAN"))
admin = int(os.getenv("ADMIN"))
no_results = os.getenv("NO_RESULTS")
yell_tutorial = os.getenv("YELL_TUTORIAL")

max_width = 448
max_height = 220

yell = CendyneYells()


def makeSticker(text):
  try:
    text = emoji.demojize(text, use_aliases=True)
    # print(text)
    text = emoji.emojize(text, use_aliases=True)
    # print(text.encode("raw_unicode_escape").decode("latin_1"))
  except Exception as ex:
    # print(ex)
    logging.exception("A problem during emjoi")
    # pass
  return yell.makeSticker(text)

def makeImageSticker(img):
  return yell.makeStickerImg(img)

def makeAnimatedSticker(file):
  return yell.makeStickerAnimated(file)

def makeAnimatedStickerSvg(file):
  return yell.makeStickerAnimatedSvg(file, max_width, max_height)

def start(update: Update, _: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    # print(update)
    logging.info("Help or Start %s", update)
    update.message.reply_text('Send a picture, a sticker, or some words. Later you can teach me about it with /learn by replying to the sticker I make')
    if yell_tutorial:
      update.message.reply_animation(yell_tutorial)

@yelldb.with_connection
def cancel(update: Update, _: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    # print(update)
    logging.info("Cancel %s", update)
    update.message.reply_text("Alrighty")
    state = yelldb.chatState(update.message.chat_id)
    state.file_id = None
    state.message_id = None
    state.learning = False
    state.input = None
    yelldb.saveChatState(state)


@yelldb.with_connection
def callback(update: Update, c: CallbackContext) -> None:
  logging.info("%s", str(update))
  data = update.callback_query.data
  args = data.split(" ", maxsplit=1)
  command = args[0]
  logging.info("args: %s", str(args))
  chatId = None
  messageId = None
  action = None
  response = None
  if command == "YES" and len(args) == 2:
    id = args[1]
    result = yelldb.findPending(id)
    if result:
      (name, fileId, chatId, messageId) = result
      yelldb.learn(name, fileId)
      yelldb.deletePending(id)
      action = "delete"
      response = "Approved!"
      # print("Learned! ", name)
      logging.info("Learned %s", name)
    else:
      # print("not found in db")
      logging.info("%s not found in db", name)
      action = "delete"
  elif command == "NO" and len(args) == 2:
    id = args[1]
    result = yelldb.findPending(id)
    if result:
      (name, fileId, chatId, messageId) = result
      yelldb.deletePending(id)
      action = "delete"
      response = "Rejected! " + name + " will not be used"
      # print("rejected", name)
      logging.info("Rejected %s",name)
    else:
      # print("not found in db")
      logging.info("%s not found in db", name)
      action = "delete"
  else:
    # print("Unsupported?", command, len(args))
    logging.info("Unsupported %s %n", command, len(args))

  if action == "delete":
    deleted = c.bot.delete_message(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id)
    # print(deleted)
    logging.info("Deleted response: %s", str(deleted))
  if response:
    send = c.bot.send_message(chat_id=chatId, text=response, reply_to_message_id=messageId)
    # print(send)
    logging.info("Sent response: %s", str(send))

def clearState(state: yelldb.ChatState):
  state.file_id = None
  state.input = None
  state.learning = False
  state.message_id = None
  yelldb.saveChatState(state)

def submitForReview(update: Update, c: CallbackContext, state: yelldb.ChatState):
  if yelldb.countLearned(state.input, state.file_id) > 0:
      update.message.reply_text("I already know that!")
      clearState(state)
      return
  if update.message.from_user and update.message.from_user.id == admin:
    yelldb.learn(state.input, state.file_id)
    update.message.reply_text("OK")
    clearState(state)
    return
  elif state.file_id:
    if yelldb.countPending(state.input, state.file_id) > 0:
      update.message.reply_text("Still waiting for review!")
      clearState(state)
      return

    id = str(uuid.uuid4())
    yelldb.submit(id, state.input, state.file_id, update.message.chat_id, update.message.message_id)
    fromUser = update.message.from_user and (update.message.from_user.username or update.message.from_user.first_name)

    sticker = c.bot.send_document(
      chat_id=review_chan,
      document=state.file_id,
      reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton(state.input, callback_data="YES " + id)],
        [InlineKeyboardButton("\u274C " + fromUser, callback_data="NO " + id)]
      ]))
    update.message.reply_text("Submitting for approval")

    clearState(state)
  else:
    update.message.reply_text("Something's not right!")


@yelldb.with_connection
def learn(update: Update, c: CallbackContext) -> None:
    # print(update)
    logging.info("Learn update: %s", str(update))
    state = yelldb.chatState(update.message.chat_id)
    if not c.args or len(c.args) == 0:
      if update.message.reply_to_message and update.message.reply_to_message.sticker:
        msg = update.message.reply_to_message
        if msg.from_user.id == c.bot.id or (msg.forward_from_chat and msg.forward_from_chat.id == log_chan):
          state.file_id = msg.sticker.file_id
          state.message_id = msg.message_id
          update.message.reply_text("Reply with the label you want for this message", reply_to_message_id = state.message_id)
          state.learning = True
          yelldb.saveChatState(state)
        else:
          update.message.reply_text("If you use /learn, it should be against a sticker I sent!")
      elif state.file_id:
        update.message.reply_text("Reply with the label you want for this message", reply_to_message_id = state.message_id)
        state.learning = True
        yelldb.saveChatState(state)
      else:
        update.message.reply_text("Reply to a sticker I've made with /learn or create a new one by sending me text, a sticker, a photo, or a picture file")
      return
    name = (" ".join(c.args)).strip().lower()
    # print("Learn '", name, "'", sep="")
    logging.info("Learn %s", str(name))
    if update.message.reply_to_message:
      msg = update.message.reply_to_message
      if msg.sticker:
        state.input = name
        if msg.from_user.id == c.bot.id or (msg.forward_from_chat and msg.forward_from_chat.id == log_chan):
          state.file_id = msg.sticker.file_id
          state.message_id = msg.message_id
          submitForReview(update, c, state)
        else:
          update.message.reply_text("I didn't make that sticker!")
      else:
        update.message.reply_text("That's not a sticker!")
    elif state.file_id:
      state.input = name
      submitForReview(update, c, state)
    else:
      update.message.reply_text('Reply to which sticker (from me) you want me to learn')


def messageHandler(update: Update, c: CallbackContext) -> None:
  # print("Message handler!!!", update)
  logging.info("Message Update %s", str(update))
  
  try:
    if update.message:
      state = yelldb.chatState(update.message.chat_id)
      if update.message.text:
        if state.learning:
          logging.info("Learning state active")
          state.input = update.message.text
          submitForReview(update, c, state)
          return
        # Generate a sticker
        if len(update.message.text) > 125:
          logging.info("Too much text")
          update.message.reply_text("Too much text, sorry")
          return
        cached = yelldb.cachedText(update.message.text)
        if cached:
          result = update.message.reply_document(document=cached)
          state.input = update.message.text
          state.file_id = cached
          state.message_id = result.message_id
          yelldb.saveChatState(state)
          logging.info("Sent text sticker: %s", str(result))
          return
        if yelldb.isTombstoned(update.message.text):
          update.message.reply_text("Too much text, sorry")
          return
        text = "\n".join(textwrap.wrap(update.message.text, 25))
        sticker = makeSticker(text)
        if stickers.validSize(sticker):
          result = update.message.reply_document(document=open(sticker, "rb"))
          c.bot.send_document(chat_id=log_chan, document=result.sticker.file_id)
          logging.info("Sent text sticker: %s", str(result))
          yelldb.cacheText(update.message.text, result.sticker.file_id)
          state.input = update.message.text
          state.file_id = result.sticker.file_id
          state.message_id = result.message_id
          yelldb.saveChatState(state)
        else:
          logging.info("Too much text")
          update.message.reply_text("Too much text, sorry")
          yelldb.tombstone(update.message.text)

        # print("Result:", result)
        
        stickers.deleteSticker(sticker)
      elif update.message.photo:
        # print("Got image")
        logging.info("Got image %s", str(update.message.photo))
        photo = update.message.photo[len(update.message.photo)-1]

        if yelldb.isTombstoned(photo.file_id):
          update.message.reply_text("Can't do it")
          return
        cached = yelldb.cachedFile(photo.file_unique_id)
        if cached:
          result = update.message.reply_document(document=cached)
          state.file_id = cached
          state.message_id = result.message_id
          state.input = None
          yelldb.saveChatState(state)
          return

        f = c.bot.get_file(photo.file_id)
        path = stickers.tempPathExt(photo.file_id, "jpg")
        f.download(path)
        # print("got file ", f)
        logging.info("Got downloaded file %s", str(f))
        img = Image.open(path)
        wpercent = (max_width/float(img.size[0]))
        hpercent = (max_height/float(img.size[1]))
        minpercent = min(wpercent, hpercent)
        hsize = int((float(img.size[1])*float(minpercent)))
        wsize = int((float(img.size[0])*float(minpercent)))
        resized = img.resize((wsize,hsize))
        sticker = makeImageSticker(resized)
        result = update.message.reply_sticker(sticker=open(sticker, "rb"))
        c.bot.send_document(chat_id=log_chan, document=result.sticker.file_id)
        yelldb.cacheFile(photo.file_unique_id, result.sticker.file_id)
        # print("Result:", result)
        logging.info("Sent sticker %s", str(result))
        stickers.deleteSticker(sticker)
        os.unlink(path)

        state.file_id = result.sticker.file_id
        state.message_id = result.message_id
        state.input = None
        yelldb.saveChatState(state)
      elif update.message.sticker:
        if update.message.forward_from_chat and update.message.forward_from_chat.id == log_chan:
          # Do nothing if the message is from the log
          # This is for recovery relabeling
          state.file_id = update.message.sticker.file_id
          state.message_id = result.message_id
          state.input = None
          yelldb.saveChatState(state)
          return
        if yelldb.isTombstoned(update.message.sticker.file_unique_id):
          logging.info("Sending tombstone")
          update.message.reply_text("Can't do it")
          return
        cached = yelldb.cachedFile(update.message.sticker.file_unique_id)
        if cached:
          logging.info("Sending cached sticker")
          result = update.message.reply_document(document=cached)
          state.file_id = cached
          state.message_id = result.message_id
          state.input = None
          yelldb.saveChatState(state)
          return
        if update.message.sticker.is_animated:
          f = c.bot.get_file(update.message.sticker.file_id) 
          path = stickers.tempPathExt(update.message.sticker.file_id, "tgs")
          f.download(path)
          sticker = makeAnimatedSticker(path)
          if stickers.validSize(sticker):
            result = update.message.reply_sticker(sticker=open(sticker, "rb"))
            c.bot.send_document(chat_id=log_chan, document=result.sticker.file_id)
            # print("Result:", result)
            logging.info("Sent sticker %s", str(result))
            yelldb.cacheFile(update.message.sticker.file_unique_id, result.sticker.file_id)
          else:
            update.message.reply_text("File Size too big")
            yelldb.tombstone(update.message.sticker.file_unique_id)
          
          stickers.deleteSticker(sticker)
          os.unlink(path)
          state.file_id = result.sticker.file_id
          state.message_id = result.message_id
          state.input = None
          yelldb.saveChatState(state)
        else:
          f = c.bot.get_file(update.message.sticker.file_id) 
          path = stickers.tempPathExt(update.message.sticker.file_id, "webp")
          f.download(path)
          img = Image.open(path)
          wpercent = (max_width/float(img.size[0]))
          hpercent = (max_height/float(img.size[1]))
          minpercent = min(wpercent, hpercent)
          hsize = int((float(img.size[1])*float(minpercent)))
          wsize = int((float(img.size[0])*float(minpercent)))
          resized = img.resize((wsize,hsize))
          sticker = makeImageSticker(resized)
          result = update.message.reply_sticker(sticker=open(sticker, "rb"))
          c.bot.send_document(chat_id=log_chan, document=result.sticker.file_id)
          yelldb.cacheFile(update.message.sticker.file_unique_id, result.sticker.file_id)
          # print("Result:", result)
          logging.info("Sent sticker %s", str(result))
          stickers.deleteSticker(sticker)
          os.unlink(path)
          state.file_id = result.sticker.file_id
          state.message_id = result.message_id
          state.input = None
          yelldb.saveChatState(state)
      elif update.message.document:
        doc = update.message.document
        # print("got document with mime type", doc.mime_type)
        logging.info("Received document %s", str(doc.mime_type))
        if doc.file_size > 2000000:
            update.message.reply_text("Too Big!")
            # No need to tombstone it since we never download it.
            return
        if yelldb.isTombstoned(doc.file_unique_id):
          logging.info("Sending tombstone")
          update.message.reply_text("Can't do it")
          return
        cached = yelldb.cachedFile(doc.file_unique_id)
        if cached:
          logging.info("Sending cached sticker")
          result = update.message.reply_document(document=cached)
          state.file_id = cached
          state.message_id = result.message_id
          state.input = None
          yelldb.saveChatState(state)
          return

        if doc.mime_type == "image/png" or doc.mime_type == "image/jpeg":
          f = c.bot.get_file(doc.file_id) 
          path = stickers.tempPathExt(doc.file_id, "png")
          f.download(path)
          img = Image.open(path)
          wpercent = (max_width/float(img.size[0]))
          hpercent = (max_height/float(img.size[1]))
          minpercent = min(wpercent, hpercent)
          hsize = int((float(img.size[1])*float(minpercent)))
          wsize = int((float(img.size[0])*float(minpercent)))
          resized = img.resize((wsize,hsize))
          sticker = makeImageSticker(resized)
          result = update.message.reply_sticker(sticker=open(sticker, "rb"))
          c.bot.send_document(chat_id=log_chan, document=result.sticker.file_id)
          logging.info("Sent sticker %s", str(result))
          yelldb.cacheFile(doc.file_unique_id, result.sticker.file_id)
          stickers.deleteSticker(sticker)
          os.unlink(path)

          state.file_id = result.sticker.file_id
          state.message_id = result.message_id
          state.input = None
          yelldb.saveChatState(state)
        elif doc.mime_type == "image/svg+xml":
          f = c.bot.get_file(doc.file_id) 
          path = stickers.tempPathExt(doc.file_id, "png")
          f.download(path)
          sticker = makeAnimatedStickerSvg(path)
          if stickers.validSize(sticker):
            result = update.message.reply_document(document=open(sticker, "rb"))
            c.bot.send_document(chat_id=log_chan, document=result.sticker.file_id)
            logging.info("Sent text sticker: %s", str(result))
            yelldb.cacheFile(doc.file_unique_id, result.sticker.file_id)
            state.file_id = result.sticker.file_id
            state.input = None
            state.message_id = result.message_id
            yelldb.saveChatState(state)
          else:
            logging.info("Could not fit image")
            update.message.reply_text("SVG too complex could not import")
            yelldb.tombstone(doc.file_unique_id)
          # print("Result:", result)
          
          stickers.deleteSticker(sticker)
          os.unlink(path)
        else:
          update.message.reply_text("I can do PNGs and JPEGs, and SVGs but not this")
          # print("Mime type: ", doc.mime_type)
          logging.info("Mime type %s not supported", doc.mime_type)
      else:
        update.message.reply_text("unsupported")
        return
  except Exception as ex:
      # print("A problem I guess")
      logging.exception("A problem I guess")
      # traceback.print_exception(*sys.exc_info())
  
@yelldb.with_connection
def inlinequery(update: Update, c: CallbackContext) -> None:
    """Handle the inline query."""
    query = update.inline_query.query.lower()
    # print(update)
    logging.info("Inline query %s", str(update))
    results = []
    count = 0
    files = set()
    names = {}
    for result in yelldb.findLearned(query):
      name = result[0]
      file_id = result[1]
      if not file_id in files:
        files.add(file_id)
        l = names.get(name, [])
        l.append(file_id)
        names[name] = l
    for name in collections.OrderedDict(sorted(names.items())):
      for file in names[name]:
        count = count+1
        # No more than 50 results are allowed
        if count < 50:
          # print(query, name, file)
          logging.debug("Query result %s %s %s", query, name, file)
          results.append(InlineQueryResultCachedSticker(
            id=uuid.uuid4(),
            sticker_file_id=file,
          ))
    random.shuffle(results)
    switch_pm_text = None
    switch_pm_parameter = None
    if len(results) == 0:
      if no_results:
        results.append(InlineQueryResultCachedSticker(
          id=uuid.uuid4(),
          sticker_file_id=no_results,
        ))
      switch_pm_text = "Learn " + query[0:40]
      # Todo figure out a switch_pm_parameter
      # It only accepts 1-64 characters A-Za-z0-9\-_
      switch_pm_parameter = "learn"
    update.inline_query.answer(results, switch_pm_text=switch_pm_text, switch_pm_parameter=switch_pm_parameter)



def main() -> None:
  yelldb.init()
  # Create the Updater and pass it your bot's token.
  updater = Updater(token)

  # Get the dispatcher to register handlers
  dispatcher = updater.dispatcher

  # on different commands - answer in Telegram
  dispatcher.add_handler(CommandHandler("start", start))
  dispatcher.add_handler(CommandHandler("help", start))
  dispatcher.add_handler(CommandHandler("cancel", cancel))
  dispatcher.add_handler(CommandHandler("learn", learn))

  # on non command i.e message - echo the message on Telegram
  dispatcher.add_handler(ChatMemberHandler(messageHandler))
  dispatcher.add_handler(MessageHandler(Filters.all, messageHandler))
  dispatcher.add_handler(CallbackQueryHandler(callback=callback))
  dispatcher.add_handler(InlineQueryHandler(inlinequery))

  # Start the Bot
  updater.start_polling()

  # Block until the user presses Ctrl-C or the process receives SIGINT,
  # SIGTERM or SIGABRT. This should be used most of the time, since
  # start_polling() is non-blocking and will stop the bot gracefully.
  updater.idle()


if __name__ == '__main__':
    main()
