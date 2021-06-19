from dotenv import load_dotenv

import logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from telegram import Update, InlineQueryResultCachedSticker, InlineKeyboardMarkup, InlineKeyboardButton
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
import sqlite3
import uuid
import random

load_dotenv()

token = os.environ["YELL_TOKEN"]
db = os.getenv("DB")

review_chan = int(os.getenv("REVIEW_CHAN"))
log_chan = int(os.getenv("LOG_CHAN"))
admin = int(os.getenv("ADMIN"))
no_results = os.getenv("NO_RESULTS")

max_width = 448
max_height = 220

yell = CendyneYells()

def getConnection(_: CallbackContext) -> sqlite3.Connection:
  return sqlite3.connect(db)

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
    update.message.reply_text('Send a picture, a sticker, or some words. Later you can teach me about it with /learn')

def callback(update: Update, c: CallbackContext) -> None:
  print(update)
  data = update.callback_query.data
  args = data.split(" ", maxsplit=1)
  command = args[0]
  print(args)
  con = getConnection(c)
  chatId = None
  messageId = None
  action = None
  response = None
  try:
    cursor = con.cursor()
    if command == "YES" and len(args) == 2:
      result = cursor.execute("select name, file_id, chat_id, message_id from yell_pending where id = :id", {"id": args[1]}).fetchone()
      if result:
        (name, fileId, chatId, messageId) = result
        cursor.execute("insert into yell_learn (name, file_id) values (:name, :file_id)", {"name": name, "file_id": fileId})
        cursor.execute("delete from yell_pending where id = :id", {"id": args[1]})
        action = "delete"
        response = "Approved!"
        print("Learned! ", name)
      else:
        print("not found in db")
        action = "delete"
    elif command == "NO" and len(args) == 2:
      result = cursor.execute("select name, file_id, chat_id, message_id from yell_pending where id = :id", {"id": args[1]}).fetchone()
      if result:
        (name, fileId, chatId, messageId) = result
        cursor.execute("delete from yell_pending where id = :id", {"id": args[1]})
        action = "delete"
        response = "Rejected! " + name + " will not be used"
        print("rejected", name)
      else:
        print("not found in db")
        action = "delete"
    else:
      print("Unsupported?", command, len(args))
    con.commit()
  finally:
    con.close()
  if action == "delete":
    deleted = c.bot.delete_message(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id)
    print(deleted)
  if response:
    send = c.bot.send_message(chat_id=chatId, text=response, reply_to_message_id=messageId)
    print(send)



def learn(update: Update, c: CallbackContext) -> None:
    print(update)
    if not c.args or len(c.args) == 0:
      update.message.reply_text("Reply to a sticker with\n/learn name here\nto learn the name for that sticker")
      return
    name = (" ".join(c.args)).strip().lower()
    print("Learn '", name, "'", sep="")
    if update.message.reply_to_message:
      msg = update.message.reply_to_message
      if msg.sticker:
        if update.message.from_user and update.message.from_user.id == admin:
          con = getConnection(c)
          try:
            cursor = con.cursor()
            cursor.execute("insert into yell_learn(name, file_id) values (:name, :file_id)", {
              "name": name,
              "file_id": msg.sticker.file_id,
            })
            con.commit()
            update.message.reply_text("OK")
          finally:
            con.close()
        elif msg.from_user.id == c.bot.id:
          id = str(uuid.uuid4())
          con = getConnection(c)
          try:
            cursor = con.cursor()
            [result] = cursor.execute("select count(*) from yell_learn where name = :name and file_id = :file_id", {
              "name": name,
              "file_id": msg.sticker.file_id,
            }).fetchone()
            if result > 0:
              update.message.reply_text("I already know that!")
              return
            [result] = cursor.execute("select count(*) from yell_pending where name = :name and file_id = :file_id", {
              "name": name,
              "file_id": msg.sticker.file_id,
            }).fetchone()
            if result > 0:
              update.message.reply_text("Still waiting for review!")
              return
            cursor.execute("insert into yell_pending(id, name, file_id, chat_id, message_id) values (:id, :name, :file_id, :chat_id, :message_id)", {
              "id": id,
              "name": name,
              "file_id": msg.sticker.file_id,
              "chat_id": update.message.chat_id,
              "message_id": update.message.message_id,
            })
            con.commit()
          finally:
            con.close()
          fromUser = update.message.from_user and (update.message.from_user.username or update.message.from_user.first_name)

          sticker = c.bot.send_document(
            chat_id=review_chan,
            document=msg.sticker.file_id,
            reply_markup=InlineKeyboardMarkup([
              [InlineKeyboardButton(name, callback_data="YES " + id)],
              [InlineKeyboardButton("\u274C " + fromUser, callback_data="NO " + id)]
            ]))
          update.message.reply_text("Submitting for approval")
          print("review", sticker)
        # elif msg.from_user.id == admin:
        #   pass
        else:
          update.message.reply_text("I didn't send that!")
      else:
        update.message.reply_text("That's not a sticker!")
    else:
      update.message.reply_text('Reply to which sticker (from me) you want me to learn')


def messageHandler(update: Update, c: CallbackContext) -> None:
  print("Message handler!!!", update)
  try:
    if update.message:
      if update.message.text:
        sticker = makeSticker(update.message.text)
        result = update.message.reply_document(document=open(sticker, "rb"))
        c.bot.send_document(chat_id=log_chan, document=result.sticker.file_id)
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
        wpercent = (max_width/float(img.size[0]))
        hpercent = (max_height/float(img.size[1]))
        minpercent = min(wpercent, hpercent)
        hsize = int((float(img.size[1])*float(minpercent)))
        wsize = int((float(img.size[0])*float(minpercent)))
        resized = img.resize((wsize,hsize))
        sticker = makeImageSticker(resized)
        result = update.message.reply_sticker(sticker=open(sticker, "rb"))
        c.bot.send_document(chat_id=log_chan, document=result.sticker.file_id)
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
            c.bot.send_document(chat_id=log_chan, document=result.sticker.file_id)
            print("Result:", result)
          else:
            # Delete the too big sticker
            stickers.deleteSticker(sticker)
            # Make a new one saying too big
            sticker = makeSticker("File Size\nToo Big!")
            result = update.message.reply_document(document=open(sticker, "rb"))
            # No need to send it to the channel
            # c.bot.send_document(chat_id=log_chan, document=result.sticker.file_id)
            pass
          
          stickers.deleteSticker(sticker)
          os.unlink(path)
        else:
          if update.message.sticker.set_name == 'OMYACendyne':
            # Ignore this pack
            return
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
          print("Result:", result)
          stickers.deleteSticker(sticker)
          os.unlink(path)
      elif update.message.document:
        doc = update.message.document
        print("got document with mime type", doc.mime_type)
        if doc.mime_type == "image/png" or doc.mime_type == "image/jpeg":
          if doc.file_size > 2000000:
            update.message.reply_text("Too Big!")
            return
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
          print("Result:", result)
          stickers.deleteSticker(sticker)
          os.unlink(path)
        else:
          update.message.reply_text("I can do PNGs and JPEGs but not this")
          print("Mime type: ", doc.mime_type)
      else:
        update.message.reply_text("unsupported")
        return
  except Exception as ex:
      print("A problem I guess")
      traceback.print_exception(*sys.exc_info())
  

def inlinequery(update: Update, c: CallbackContext) -> None:
    """Handle the inline query."""
    query = update.inline_query.query.lower()
    print(update)
    results = []
    con = getConnection(c)
    count = 0
    try:
      cursor = con.cursor()
      files = set()
      names = {}
      for result in cursor.execute("select name, file_id from yell_learn where name like :name order by random() LIMIT 200", {
        "name": "%" + query + "%"
      }):
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
          if count < 50:
            print(query, name, file)
            results.append(InlineQueryResultCachedSticker(
              id=uuid.uuid4(),
              sticker_file_id=file,
            ))
    finally:
      con.close()
    random.shuffle(results)
    if no_results and len(results) == 0:
      results.append(InlineQueryResultCachedSticker(
        id=uuid.uuid4(),
        sticker_file_id=no_results,
      ))
    update.inline_query.answer(results)


def initDb(con: sqlite3.Connection):
  cur = con.cursor()
  cur.execute("create table if not exists yell_cache (input_file_id, file_id)")
  cur.execute("create table if not exists yell_learn (name, file_id)")
  cur.execute("create table if not exists yell_pending (id, name, file_id, chat_id, message_id)")
  cur.close()


def main() -> None:
  connection = sqlite3.connect(db)
  initDb(connection)
  connection.close()
  # Create the Updater and pass it your bot's token.
  updater = Updater(token)

  # Get the dispatcher to register handlers
  dispatcher = updater.dispatcher

  # on different commands - answer in Telegram
  dispatcher.add_handler(CommandHandler("start", start))
  dispatcher.add_handler(CommandHandler("help", start))
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