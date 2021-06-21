import sys
import os
import traceback
import grapheme
import emoji
import uuid

import logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from telegram import Update, InlineQueryResultCachedSticker
from telegram.ext import Updater, InlineQueryHandler, CommandHandler, CallbackContext, ChatMemberHandler, MessageHandler, Filters
from telegram.utils.helpers import escape_markdown

from cendynesays import CendyneSays
from cendynesmol import CendyneSmol
from cendynebreaths import CendyneBreathes
import stickers
from dotenv import load_dotenv

load_dotenv()

say = CendyneSays()
smol = CendyneSmol()
breathes = CendyneBreathes()


token = os.environ["BOT_TOKEN"]
log_chan = int(os.getenv("LOG_CHAN"))

def makeSticker(text):
  if text == "":
    text = "Message Here"
  keep = False
  oldtext = text
  try:
    text = emoji.demojize(text, use_aliases=True)
    # print(text)
    text = emoji.emojize(text, use_aliases=True)
    # print(text.encode("raw_unicode_escape").decode("latin_1"))
  except Exception as ex:
    # print(ex)
    logging.exception("Error during emoji")
  
  if len(text) > 120:
    text = "UwU Desu: Your message was too long"
  # print("text ", text)
  if text != oldtext:
    logging.info("Text converted to %s", text)

  elements = list(grapheme.graphemes(text))

  try:
    le = len(elements)
    if le <= 4:
      if le == 3 and elements[0] == elements[1] and elements[1] == elements[2]:
        for count in [40, 30, 20, 10, 5, 4, 3, 2, 1, 0]:
          if count == 0:
            sticker = say.makeSticker("Unsupported :(")
            break
          sticker = breathes.makeSticker(text, count)
          if not stickers.validSize(sticker):
            # Try a smaller particle size until the file is
            # within Telegram's requirement
            # print("Count ", count, " resulted in too large of a file")
            logging.info("Count %n result in too large of a file", count)
            continue
          break
      else:
        act = None
        if elements[le - 1] == "!":
          act = smol.actExclaim
        elif elements[le - 1] == "?":
          act = smol.actQuestion
        elif le == 1:
          act = smol.actNormal
        if act is not None:
          # print("Smol sticker ", text)
          logging.info("Smol sticker %s", text)
          sticker = smol.makeSticker(text, act)
        else:
          # Fallback to the normal text thing
          sticker = say.makeSticker(text)
    else:
      sticker = say.makeSticker(text)
  except Exception as ex:
    # print("Exception ex", ex)
    # traceback.print_exception(*sys.exc_info())
    logging.exception("An error")
    text = ".-. An error"
    keep = True
    sticker = say.makeSticker(text)

  if not stickers.validSize(sticker):
    stickers.deleteSticker(sticker)
    text = "OwO Desu: The sticker was too big for Telegram"
    keep = True
    sticker = say.makeSticker(text)
  return sticker, keep

def start(update: Update, _: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    # print(update)
    logging.info("Start issued")
    update.message.reply_text('Use @CendyneSaysBot text here to make a message')


def messageHandler(update: Update, c: CallbackContext) -> None:
  # print("Message handler!!!", update)
  logging.info("Incoming message %s", update)
  try:
    if update.message:
      text = update.message.text
      
      sticker, keep = makeSticker(text)
      # print("About to reply with document ", sticker)
      logging.info("About to reply with sticker %s", sticker)
      # result = update.message.reply_document(document=open(sticker, "rb"))
      result = c.bot.send_document(chat_id=log_chan, document=open(sticker, "rb"))
      update.message.reply_document(document=result.sticker.file_id)
      # print("Result:", result)
      logging.info("Sent sticker result %s", str(result))
      if not keep:
        stickers.deleteSticker(sticker)
  except Exception as ex:
      # print("A problem I guess")
      # traceback.print_exception(*sys.exc_info())
      logging.exception("A problem I guess")
  

def inlinequery(update: Update, c: CallbackContext) -> None:
    """Handle the inline query."""
    query = update.inline_query.query
    keep = False

    if query == "":
      return
    
    # print(update)
    # print(update.inline_query.from_user)
    logging.info("Inline query %s", str(update))
    sticker, keep = makeSticker(query)

    result = c.bot.send_document(chat_id=log_chan, document=open(sticker, "rb"))
    
    results = [
      InlineQueryResultCachedSticker(
        id=uuid.uuid4(),
        sticker_file_id=result.sticker.file_id,
      ),
    ]

    update.inline_query.answer(results)

    if not keep:
      stickers.deleteSticker(sticker)


def main() -> None:
    # Create the Updater and pass it your bot's token.
    updater = Updater(token)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("start", start))

    # on non command i.e message - echo the message on Telegram
    dispatcher.add_handler(InlineQueryHandler(inlinequery))
    dispatcher.add_handler(ChatMemberHandler(messageHandler))
    dispatcher.add_handler(MessageHandler(Filters.text, messageHandler))

    # Start the Bot
    updater.start_polling()

    # Block until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()

