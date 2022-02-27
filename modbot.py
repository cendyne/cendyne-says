import time
import os
import logging
import re
import traceback
import sys
from typing import List, Text, Union
import telegram
from telegram.chatmember import ChatMember
from telegram.chatpermissions import ChatPermissions
from telegram.constants import CHAT_CHANNEL, CHAT_GROUP, CHAT_PRIVATE, CHAT_SENDER, CHAT_SUPERGROUP
from telegram.botcommandscope import BotCommandScopeAllChatAdministrators
from expiringdict import ExpiringDict
import secrets
# import uuid

from telegram.ext import Updater, InlineQueryHandler, CommandHandler, CallbackContext, MessageHandler, Filters, CallbackQueryHandler
from telegram import Update, BotCommand, BotCommandScopeAllPrivateChats
from dotenv import load_dotenv
from telegram.inline.inlinekeyboardbutton import InlineKeyboardButton
from telegram.inline.inlinekeyboardmarkup import InlineKeyboardMarkup
from telegram.user import User

import moddb
from captchasays import CaptchaSays
from db import with_connection
import stickers
captcha = CaptchaSays()

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logging.getLogger('pscheduler.executors.default').setLevel(logging.WARN)

load_dotenv()

LETTERS = "cdefhjkmnprtvwxy2345689"

token = os.environ["MOD_TOKEN"]
log_chan = int(os.getenv("LOG_CHAN"))

admins_by_chat_id = ExpiringDict(max_len=100, max_age_seconds=60)

def random_challenge() -> Text:
    """Generates a random challenge text"""
    challenge = "".join([secrets.choice(LETTERS).upper() for i in range(8)])
    logging.info("Generated challenge: %s", challenge)
    return challenge

def get_admins(c: CallbackContext, chat_id: int) -> List[ChatMember]:
    """Gets list of admins for this chat"""
    if chat_id in admins_by_chat_id:
        try:
            return admins_by_chat_id[chat_id]
        except:
            pass
    admins = c.bot.get_chat_administrators(chat_id)
    admins_by_chat_id[chat_id] = admins
    return admins


def get_my_admin_user(c: CallbackContext, chat_id: int) -> Union[ChatMember, None]:
    """Tests if the bot itself is listed as an admin"""
    for user in get_admins(c, chat_id):
        if user.user and user.user.id == c.bot.id:
            return user
    return None


def do_i_have_delete_permissions(c: CallbackContext, chat_id: int) -> bool:
    """Checks if this bot has delete permissions"""
    user = get_my_admin_user(c, chat_id)
    if user:
        return user.can_delete_messages
    return False


def do_i_have_restrict_permissions(c: CallbackContext, chat_id: int) -> bool:
    """Checks if this bot has restriction permissions"""
    user = get_my_admin_user(c, chat_id)
    if user:
        return user.can_restrict_members
    return False


def is_user_an_admin(c: CallbackContext, chat_id: int, user: User) -> bool:
    """Checks if a specified user is in the admin list"""
    logging.info("Is user %s an admin in chat %s?", user, chat_id)
    if user.is_bot and user.username == "GroupAnonymousBot":
        # Only admins can use GroupAnonymousBot
        return True
    for admin in get_admins(c, chat_id):
        logging.info("Inspecting user %s", user)
        if admin.user and admin.user.id == user.id:
            logging.info("Yes, user %s is an admin in chat %s", user, chat_id)
            return True
    logging.info("No, user %s is not an admin in chat %s", user, chat_id)
    return False


@with_connection
def start(update: Update, _: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    logging.info("Start issued %s", update)
    # TODO handle start with contextual command thing from a group
    message = update.message
    if message:
        chat_id = message.chat_id
        chat_type = message.chat.type
        # from_username = message.from_user.username
        # from_firstname = message.from_user.first_name
        from_user_id = message.from_user.id
        if chat_type == CHAT_PRIVATE:
            if message.text.startswith("/start "):
                regarding_chat_id = message.text[7:]
                if regarding_chat_id.isnumeric():
                    regarding_chat_id = int(regarding_chat_id)
                elif regarding_chat_id.startswith("-") and regarding_chat_id[1:].isnumeric():
                    regarding_chat_id = int(regarding_chat_id)
                else:
                    # This isn't normal
                    return
                if moddb.is_challenged(regarding_chat_id, from_user_id):
                    state = moddb.chat_state_with_user(chat_id, from_user_id)
                    state.challenge_chat_id = regarding_chat_id
                    moddb.save_chat_state(state)
                    message.reply_text('Hello you are about to challenged with a captcha. Your goal is to type the sequence of letters from left to right, top to bottom.', reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("I understand", callback_data="understood")]
                    ]))
                else:
                    message.reply_text("Hello, you came here pressing a button from one group, but you do not have an active challenge. Consider messaging an admin for the group you came from.")
            else:
                message.reply_text("Hello, you may want to use /help")


@with_connection
def enable_challenge(update: Update, c: CallbackContext) -> None:
    """Handler for enabling the challenge"""
    if not is_user_an_admin(c, update.message.chat_id, update.message.from_user):
        logging.info("Update ignored %s", update)
        return
    logging.info("Enable Challenge issued %s", update)
    state = moddb.chat_state(update.message.chat_id)
    if moddb.enable_challenge_no_save(state):
        moddb.save_chat_state(state)
        update.message.reply_text('Challenges are now enabled')
    else:
        update.message.reply_text('Challenges were already enabled')


@with_connection
def disable_challenge(update: Update, c: CallbackContext) -> None:
    """Handler for disabling the challenge"""
    if not is_user_an_admin(c, update.message.chat_id, update.message.from_user):
        logging.info("Update ignored %s", update)
        return
    logging.info("Disable Challenge issued %s", update)
    state = moddb.chat_state(update.message.chat_id)
    if moddb.disable_challenge_no_save(state):
        moddb.save_chat_state(state)
        update.message.reply_text('Challenges are now disabled')
    else:
        update.message.reply_text('Challenges were already disabled')


@with_connection
def enable_channel_posts(update: Update, c: CallbackContext) -> None:
    """Handler for enabling posts from channels"""
    if not is_user_an_admin(c, update.message.chat_id, update.message.from_user):
        logging.info("Update ignored %s", update)
        return
    logging.info("Enable Channel posting issued %s", update)
    state = moddb.chat_state(update.message.chat_id)
    if moddb.enable_channel_posting_no_save(state):
        moddb.save_chat_state(state)
        update.message.reply_text('Anonymous Channel Posting is now enabled')
    else:
        update.message.reply_text(
            'Anonymous Channel Posting was already enabled')


@with_connection
def disable_channel_posts(update: Update, c: CallbackContext) -> None:
    """Handler for disabling posts from channels"""
    if not is_user_an_admin(c, update.message.chat_id, update.message.from_user):
        logging.info("Update ignored %s", update)
        return
    logging.info("Disable Channel posting issued %s", update)
    state = moddb.chat_state(update.message.chat_id)
    if moddb.disable_channel_posting_no_save(state):
        moddb.save_chat_state(state)
        update.message.reply_text('Anonymous Channel Posting is now disabled')
    else:
        update.message.reply_text(
            'Anonymous Channel Posting was already disabled')


@with_connection
def enable_auto_ban_channel_posts(update: Update, c: CallbackContext) -> None:
    """Handler for auto banning channel posts"""
    if not is_user_an_admin(c, update.message.chat_id, update.message.from_user):
        logging.info("Update ignored %s", update)
        return
    logging.info("Enable Auto Ban Channel posting issued %s", update)
    state = moddb.chat_state(update.message.chat_id)

    if moddb.enable_auto_ban_channel_posting_no_save(state):
        also = None
        if not state.channel_post_disabled:
            moddb.disable_channel_posting_no_save(state)
            also = "Also, Anonymous Channel Posting is now disabled"
        moddb.save_chat_state(state)
        update.message.reply_text('Anonymous Channel Posting which will ban the senders ability to post anonymously is now enabled')
        if also:
            update.message.reply_text(also)
    else:
        update.message.reply_text(
            'Anonymous Channel Posting which will ban the senders ability to post anonymously was already enabled')


@with_connection
def disable_auto_ban_channel_posts(update: Update, c: CallbackContext) -> None:
    """Handler for disabling auto ban of channel posts"""
    if not is_user_an_admin(c, update.message.chat_id, update.message.from_user):
        logging.info("Update ignored %s", update)
        return
    logging.info("Disable Auto Ban Channel posting issued %s", update)
    state = moddb.chat_state(update.message.chat_id)

    if moddb.disable_auto_ban_channel_posting_no_save(state):
        moddb.save_chat_state(state)
        update.message.reply_text('Anonymous Channel Posting which will ban the senders ability to post anonymously is now disabled')
    else:
        update.message.reply_text(
            'Anonymous Channel Posting which will ban the senders ability to post anonymously was already disabled')

@with_connection
def help_handler(update: Update, c: CallbackContext) -> None:
    """Handler that gives help text"""
    logging.info("Help issued %s", update)
    # TODO handle start with contextual command thing from a group
    if update.message:
        message = update.message
        chat_type = message.chat.type
        if chat_type == CHAT_PRIVATE or chat_type == CHAT_SENDER:
            update.message.reply_text('''
Hello, this bot can be added to groups to challenge newcomers in anti-bot ways, it may also remove anonymous posting from channels.
You yourself may be facing a challenge right now. Good luck!
            ''')
        elif chat_type == CHAT_GROUP or chat_type == CHAT_SUPERGROUP:
            if not is_user_an_admin(c, update.message.chat_id, update.message.from_user):
                logging.info("Update ignored %s", update)
                return
            update.message.reply_text('''
Hello, this bot should be added as an administrator with permissions to delete messages and restrict users.

You're an admin, so guess what, there's a few commands available to you!
/enchallenge - Enable Challenges when new users arrive
/dischallenge - Disable challenges when new users arrive
/enchannel - Enable channels to post anonymously into the group
/dischannel - Disable channels from posting anonymously into the group

If you have any recommendations, reach out to @Cendyne
            ''')


@with_connection
def chat_member_handler(update: Update, c: CallbackContext) -> None:
    """New chat memebre handler"""
    logging.info("New Chat Member %s", update)

    if update.message and update.message.new_chat_members:
        chat_id = update.message.chat.id
        state = moddb.chat_state(chat_id)
        if not state.challenge_enabled:
            return
        logging.info("Challeng enabled!")
        c.bot.send_chat_action(
            chat_id=chat_id, action=telegram.ChatAction.TYPING)
        for chat_member in update.message.new_chat_members:
            @with_connection
            def callback(c: CallbackContext):
                c.bot.restrict_chat_member(chat_id, chat_member.id, ChatPermissions(
                    can_send_messages=False,
                    can_send_media_messages=False,
                    can_send_other_messages=False
                ))

                resp = update.message.reply_text("Hello, you need to talk with me before you can speak here. Please start with the button below",
                                          reply_markup=InlineKeyboardMarkup([
                                              [InlineKeyboardButton("Press this button to start", url="https://t.me/" + str(
                                                  c.bot.username) + "?start=" + str(chat_id))],
                                          ]))
                moddb.challenge(chat_id, chat_member.id, random_challenge(), time.time() + (state.challenge_expires_seconds or 86400), resp.message_id)
                
            c.job_queue.run_once(callback, 0)

    return

@with_connection
def challenge_cleared(c: CallbackContext, state: moddb.ChatState, user: User):
    """Challenge cleared by user, restore access to things"""
    message_id = moddb.find_challenge_message(state.challenge_chat_id, state.user_id)
    if message_id:
        try:
            c.bot.delete_message(state.challenge_chat_id, message_id)
        except:
            logging.error("Could not delete message")
            pass
    moddb.remove_challenge(state.challenge_chat_id, state.user_id)
    # Set all values to True to undo restrictions
    c.bot.restrict_chat_member(state.challenge_chat_id, state.user_id, ChatPermissions(
        can_send_messages=True,
        can_send_media_messages=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True,
        can_change_info=True,
        can_invite_users=True,
        can_pin_messages=True,
        can_send_polls=True
    ))
    if state.challenge_message_id:
        try:
            c.bot.delete_message(state.challenge_chat_id, state.challenge_message_id)
        except:
            logging.error("Could not delete message")
            pass
    if user.username:
        c.bot.send_message(state.challenge_chat_id, "@" + user.username + " passed the challenge")
    else:
        c.bot.send_message(state.challenge_chat_id, user.first_name + " passed the challenge")
    state.challenge_chat_id = None
    state.challenge_message_id = None
    moddb.save_chat_state(state)

@with_connection
def message_handler(update: Update, c: CallbackContext) -> None:
    """General message handler"""
    # print("Message handler!!!", update)
    logging.info("Incoming message %s", update)

    try:
        if update.message:
            message = update.message
            chat_id = message.chat_id
            chat_type = message.chat.type
            from_username = message.from_user.username
            from_firstname = message.from_user.first_name
            from_user_id = message.from_user.id
            sender_chat_id = None
            # logging.info("%s (%s) - %s / %s (%s)", chat_type, chat_id, from_username, from_firstname, from_user_id)
            channel_post = False
            official_post = False
            if from_username == "Channel_Bot":
                channel_post = True
            if message.sender_chat and message.sender_chat.id:
                sender_chat_id = message.sender_chat.id
            if from_username is None and from_firstname == "Telegram" and from_user_id == 777000:
                if message.is_automatic_forward:
                    official_post = True
                else:
                    # This may be a spoof
                    channel_post = True

            if chat_type == CHAT_GROUP or chat_type == CHAT_SUPERGROUP:
                state = moddb.chat_state(chat_id)
                changed = False
                # logging.info("This is a group")
                if official_post:
                    changed = moddb.permit_channel_posts_no_save(state, sender_chat_id) or changed
                elif channel_post and state.channel_post_disabled:
                    if sender_chat_id in state.permitted_channel_posts:
                        # message.reply_text("This is an officially linked channel")
                        pass
                    else:
                        if message.delete():
                            if sender_chat_id and state.auto_ban_sender_chats:
                                if not c.bot.ban_chat_sender_chat(chat_id, sender_chat_id):
                                    if not do_i_have_restrict_permissions(c, chat_id):
                                        message.reply_text(
                                            "I tried to ban a channel from posting here but I do not have permissions")
                        else:
                            if not do_i_have_delete_permissions(c, chat_id):
                                message.reply_text(
                                    "This is a channel post and I tried to delete it but I do not have permissions")
                            else:
                                logging.info(
                                    "Did another bot snipe this message from me?")
                        
                if changed:
                    logging.info("Adjusting chat state: %s", state)
                    moddb.save_chat_state(state)
            elif chat_type == CHAT_PRIVATE or chat_type == CHAT_SENDER:
                state = moddb.chat_state_with_user(chat_id, from_user_id)
                logging.info("This is a private chat")
                if state.challenge_message_id and state.challenge_chat_id:
                    if moddb.is_challenged(state.challenge_chat_id, from_user_id):
                        challenge = moddb.find_challenge(state.challenge_chat_id, from_user_id)
                        if challenge:
                            logging.info("User is undergoing a challenge %s", challenge)
                            text = re.sub(r'[^a-zA-Z0-9]', '', message.text).upper()
                            if text == challenge:
                                challenge_cleared(c, state, message.from_user)
                                message.reply_text("You got it!")
                            else:
                                message.reply_text(secrets.choice(["Nope", "Not quite right", "Try again", "Oops", "Nope, try again"]))
                        else:
                            # State is inconsistent
                            state.challenge_chat_id = None
                            state.challenge_message_id = None
                            moddb.save_chat_state(state)  
                    else:
                        # State is inconsistent
                        state.challenge_chat_id = None
                        state.challenge_message_id = None
                        moddb.save_chat_state(state) 
                else:
                    message.reply_text("Not sure why you're messaging me. Maybe try /help") 
            elif chat_type == CHAT_CHANNEL:
                # Nothing is done here
                pass
    except Exception as ex:
        # print("A problem I guess")
        # traceback.print_exception(*sys.exc_info())
        logging.exception("A problem I guess")

with_connection
def selftest(update: Update, c: CallbackContext) -> None:
    """Self test handler"""
    try:
        if update.message:
            message = update.message
            challenge = random_challenge()
            if message.text.startswith("/selftest "):
                challenge = re.sub(r'[^a-zA-Z0-9]', '', message.text[10:]).upper().upper()
            chat_type = message.chat.type
            if chat_type == CHAT_PRIVATE or (is_user_an_admin(c, update.message.chat_id, update.message.from_user) and (chat_type == CHAT_GROUP or chat_type == CHAT_SUPERGROUP)):
                sticker = captcha.makeSticker(challenge)
                if stickers.validSize(sticker):
                    try:
                        c.bot.send_document(chat_id=message.chat.id, document=open(sticker, "rb"))
                    except:
                        message.reply_text("Couldn't do it")
                stickers.deleteSticker(sticker)
    except Exception as ex:
        # print("A problem I guess")
        traceback.print_exception(*sys.exc_info())
        logging.exception("A problem I guess")

@with_connection
def inlinequery(update: Update, c: CallbackContext) -> None:
    """Handle the inline query."""
    query = update.inline_query.query
    keep = False

    if query == "":
        return

    return


@with_connection
def callbackhandler(update: Update, c: CallbackContext) -> None:
    """Handle the button callback"""
    logging.info("Callback query %s", update)
    query = update.callback_query

    if query.message and query.message.chat:
        query.answer()
        state = moddb.chat_state(query.message.chat.id)
        if state.challenge_chat_id:
            if moddb.is_challenged(state.challenge_chat_id, state.user_id):
                challenge = moddb.find_challenge(state.challenge_chat_id, state.user_id)
                sticker = captcha.makeSticker(challenge)
                if stickers.validSize(sticker):
                    sticker_file = None
                    try:
                        result = c.bot.send_document(chat_id=query.message.chat.id, document=open(sticker, "rb"))
                        state.challenge_message_id = result.message_id
                        moddb.save_chat_state(state)
                        
                        if result.sticker and result.sticker.file_id:
                           sticker_file = result.sticker.file_id
                    except:
                        query.message.edit_reply_markup(reply_markup=None)
                        query.message.edit_text("I had an error so you get a free ride")
                        challenge_cleared(c, state, query.from_user)
                    # Save this sticker for later access
                    if log_chan and sticker_file:
                         c.bot.send_document(log_chan, sticker_file)
                else:
                    # cry
                    query.message.edit_reply_markup(reply_markup=None)
                    query.message.edit_text("I had an error so you get a free ride")
                    challenge_cleared(c, state, query.from_user)
                stickers.deleteSticker(sticker)
        else:
            query.answer("Expired Challenge. Try leaving and rejoining the group", show_alert=True)
            query.message.edit_reply_markup(reply_markup=None)
            query.message.edit_text("Expired Challenge. Try leaving and rejoining the group")
    else:
        query.answer("Unsupported", show_alert=True)
    return

@with_connection
def cleanup(context: CallbackContext) -> None:
    """Handle cleanup of the database"""
    # job = context.job
    # logging.info("Cleanup called %s", job)
    return


@with_connection
def test() -> None:
    """Helper method to test the challenge functionality"""
    moddb.challenge(1, 2, "abc", time.time() + 1, 1)
    value = moddb.find_challenge(1, 2)
    logging.info("test: Found challenge? %s", value)
    expired_users = moddb.find_expried_challenges(1, time.time())
    logging.info("test: Found expried users %s", expired_users)
    if len(expired_users) > 0:
        logging.error(
            "there should be no expired users! Assuming a clean database.")
    time.sleep(2)
    expired_users = moddb.find_expried_challenges(1, time.time())
    logging.info("test: Found expried users %s", expired_users)
    for user_id in expired_users:
        moddb.remove_challenge(1, user_id)
    for user_id in moddb.find_all_challenges(1):
        logging.error(
            "test: Still found challenge, it should have been removed %s", user_id)


def main() -> None:
    """Main entrypoint"""
    moddb.init()

    # test()
    # return None

    # Create the Updater and pass it your bot's token.
    updater = Updater(token)

    bot = updater.bot
    bot.set_my_commands(commands=[
        BotCommand("/help", "Show Help")
    ], scope=BotCommandScopeAllPrivateChats())
    bot.set_my_commands(commands=[
        BotCommand("/help", "Show Help"),
        BotCommand("/enchallenge", "Enable Challenges"),
        BotCommand("/dischallenge", "Disable Challenges"),
        BotCommand("/enchannel", "Enable Channel Posts"),
        BotCommand("/dischannel", "Disable Channel Posts"),
        BotCommand("/enautobanchannel", "Enable Auto Ban Channel Posts"),
        BotCommand("/disautobanchannel", "Disable Auto Ban Channel Posts"),
    ], scope=BotCommandScopeAllChatAdministrators())

    logging.info("Bot %s %s", bot.id, bot.username)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher
    # job_queue = updater.job_queue

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("enchallenge", enable_challenge))
    dispatcher.add_handler(CommandHandler("dischallenge", disable_challenge))
    dispatcher.add_handler(CommandHandler("enchannel", enable_channel_posts))
    dispatcher.add_handler(CommandHandler("dischannel", disable_channel_posts))
    dispatcher.add_handler(CommandHandler("enautobanchannel", enable_auto_ban_channel_posts))
    dispatcher.add_handler(CommandHandler("disautobanchannel", disable_auto_ban_channel_posts))
    dispatcher.add_handler(CommandHandler("selftest", selftest))
    dispatcher.add_handler(CommandHandler("help", help_handler))

    # on non command i.e message - echo the message on Telegram
    dispatcher.add_handler(InlineQueryHandler(inlinequery))
    dispatcher.add_handler(MessageHandler(
        Filters.status_update.new_chat_members, chat_member_handler))
    dispatcher.add_handler(MessageHandler(Filters.all, message_handler))
    dispatcher.add_handler(CallbackQueryHandler(callbackhandler))

    # Start the Bot
    updater.start_polling()

    # todo change 60 to 1
    # job_queue.run_repeating(cleanup, 60)

    # Block until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
