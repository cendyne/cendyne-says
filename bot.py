import sys
import os
import traceback
import grapheme
import emoji
import uuid

import logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from telegram import InlineQueryResultArticle, ParseMode, InputTextMessageContent, Update, InlineQueryResultCachedSticker
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

def makeSticker(text):
  if text == "":
    text = "Message Here"
  keep = False

  try:
    text = emoji.demojize(text, use_aliases=True)
    print(text)
    text = emoji.emojize(text, use_aliases=True)
    print(text.encode("raw_unicode_escape").decode("latin_1"))
  except Exception as ex:
    print(ex)
    pass
  
  if len(text) > 120:
    text = "UwU Desu: Your message was too long"
  print("text ", text)

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
            print("Count ", count, " resulted in too large of a file")
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
          print("Smol sticker ", text)
          sticker = smol.makeSticker(text, act)
        else:
          # Fallback to the normal text thing
          sticker = say.makeSticker(text)
    else:
      sticker = say.makeSticker(text)
  except Exception as ex:
    print("Exception ex", ex)
    traceback.print_exception(*sys.exc_info())
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
    print(update)
    update.message.reply_text('Use @CendyneSaysBot text here to make a message')


def messageHandler(update: Update, c: CallbackContext) -> None:
  print("Message handler!!!", update)
  try:
    if update.message:
      text = update.message.text
      
      sticker, keep = makeSticker(text)
      print("About to reply with document ", sticker)
      # result = update.message.reply_document(document=open(sticker, "rb"))
      result = c.bot.send_document(chat_id=-1001346187913, document=open(sticker, "rb"))
      update.message.reply_document(document=result.sticker.file_id)
      print("Result:", result)
      if not keep:
        stickers.deleteSticker(sticker)
  except Exception as ex:
      print("A problem I guess")
      traceback.print_exception(*sys.exc_info())
  

def inlinequery(update: Update, c: CallbackContext) -> None:
    """Handle the inline query."""
    query = update.inline_query.query
    keep = False

    if query == "":
      return
    
    print(update)
    print(update.inline_query.from_user)
    sticker, keep = makeSticker(query)

    result = c.bot.send_document(chat_id=-1001346187913, document=open(sticker, "rb"))
    
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

