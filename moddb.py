import pickle
import base64
import logging
from typing import List, Text, Tuple, Union, Set
from dataclasses import dataclass, field
from db import localthreaddb, with_cursor, with_connection

@with_cursor
def isChallenged(chat_id: int, user_id: int) -> bool:
    [results] = localthreaddb.cur.execute("select count(*) from mod_challenge where chat_id = :chat_id and user_id = :user_id", {
        "chat_id": chat_id,
        "user_id": user_id
    }).fetchone()
    return results > 0


@with_cursor
def challenge(chat_id: int, user_id: int, challenge: Text, expires: float, message_id: int) -> bool:
    logging.info("Creating challenge '%s' for user %s in chat %s re: %s", challenge, user_id, chat_id, message_id)
    localthreaddb.cur.execute("insert into mod_challenge (chat_id, user_id, challenge, expires, message_id) values (:chat_id, :user_id, :challenge, :expires, :message_id) ", {
        "chat_id": chat_id,
        "user_id": user_id,
        "challenge": challenge,
        "expires": expires,
        "message_id": message_id
    })

@with_cursor
def find_challenge(chat_id: int, user_id: int) -> Union[Text, None]:
    results = localthreaddb.cur.execute("select challenge from mod_challenge where chat_id = :chat_id and user_id = :user_id", {
        "chat_id": chat_id,
        "user_id": user_id
    }).fetchone()
    if results and len(results) > 0:
        logging.info("Found a challenge %s", results[0])
        return results[0]
    return None

@with_cursor
def find_challenge_message(chat_id: int, user_id: int) -> Union[int, None]:
    results = localthreaddb.cur.execute("select message_id from mod_challenge where chat_id = :chat_id and user_id = :user_id", {
        "chat_id": chat_id,
        "user_id": user_id
    }).fetchone()
    if results and len(results) > 0:
        logging.info("Found a message_id %s", results[0])
        return results[0]
    return None

@with_cursor
def remove_challenge(chat_id: int, user_id: int) -> bool:
    logging.info("Removing challenge for user %s in chat %s", user_id, chat_id)
    localthreaddb.cur.execute("delete from mod_challenge where chat_id = :chat_id and user_id = :user_id", {
        "chat_id": chat_id,
        "user_id": user_id
    })

@with_cursor
def find_expried_challenges(chat_id: int, expires: float) -> List[int]:
    results = localthreaddb.cur.execute("select user_id from mod_challenge where chat_id = :chat_id and expires < :expires", {
        "chat_id": chat_id,
        "expires": expires
    }).fetchall()
    expired = [result[0] for result in results]
    logging.info("Found expired challenges %s for chat %s", expired, chat_id)
    return expired

@with_cursor
def find_all_challenges(chat_id: int) -> List[int]:
    results = localthreaddb.cur.execute("select user_id from mod_challenge where chat_id = :chat_id", {
        "chat_id": chat_id
    }).fetchall()
    challenges = [result[0] for result in results]
    logging.info("Got all challenges %s for chat %s", challenges, chat_id)
    return challenges

@dataclass
class ChatState:
    # Shared between groups and direct message
    chat_id: int
    # Group only
    challenge_enabled: bool = False
    channel_post_disabled: bool = False
    permitted_channel_posts: Set[int] = field(default_factory=set)
    challenge_expires_seconds: float = 86400
    auto_ban_sender_chats: bool = False
    # Direct message only
    user_id: Union[int, None] = None
    challenge_chat_id: Union[int, None] = None
    challenge_message_id: Union[int, None] = None

@with_cursor
def chatState(chat_id: int) -> ChatState:
    result = localthreaddb.cur.execute("select state from mod_chat_state where chat_id = :chat_id", {
        "chat_id": chat_id
    }).fetchone()
    try:
        if result and len(result) > 0:
            state = pickle.loads(base64.standard_b64decode(result[0]))
            # Upgrade the state object since pickle will have the old version in
            if state.auto_ban_sender_chats is None:
                state.auto_ban_sender_chats = False
            # logging.info("Got chat state %s", state)
            return state
    except:
        logging.warn("Could not load chat state for id %d", chat_id)
        pass
    return ChatState(chat_id=chat_id)


@with_cursor
def saveChatState(state: ChatState):
    chat_id = state.chat_id
    logging.info("Saving chat state: %s", state)
    body = base64.standard_b64encode(pickle.dumps(state))
    [count] = localthreaddb.cur.execute("select count(*) from mod_chat_state where chat_id = :chat_id", {
        "chat_id": chat_id
    }).fetchone()
    if count and count > 0:
        localthreaddb.cur.execute("update mod_chat_state set state = :state where chat_id = :chat_id", {
            "chat_id": chat_id,
            "state": body
        })
    else:
        localthreaddb.cur.execute("insert into mod_chat_state(chat_id, state) values (:chat_id, :state)", {
            "chat_id": chat_id,
            "state": body
        })

def chatStateWithUser(chat_id: int, user_id: int) -> ChatState:
    state = chatState(chat_id)
    if state.user_id is None:
        state.user_id = user_id
        saveChatState(state)
    return state

def enableChallengeNoSave(state: ChatState) -> bool:
    if state.user_id is None and not state.challenge_enabled:
        state.challenge_enabled = True
        return True
    return False

def enableChallenge(chat_id: int) -> None:
    state = chatState(chat_id)
    if enableChallengeNoSave(state):
        saveChatState(state)

def disableChallengeNoSave(state: ChatState) -> bool:
    if state.user_id is None and state.challenge_enabled:
        state.challenge_enabled = False
        return True
    return False

def disableChallenge(chat_id: int) -> None:
    state = chatState(chat_id)
    if disableChallengeNoSave(state):
        saveChatState(state)
        for user_id in find_all_challenges(chat_id):
            remove_challenge(chat_id, user_id)

def enableChannelPostingNoSave(state: ChatState) -> bool:
    if state.user_id is None and state.channel_post_disabled:
        state.channel_post_disabled = False
        return True
    return False

def enableChannelPosting(chat_id: int) -> None:
    state = chatState(chat_id)
    if enableChannelPostingNoSave(state):
        saveChatState(state)

def disableChannelPostingNoSave(state: ChatState) -> bool:
    if state.user_id is None and not state.channel_post_disabled:
        state.channel_post_disabled = True
        return True
    return False

def disableChannelPosting(chat_id: int) -> None:
    state = chatState(chat_id)
    if disableChannelPostingNoSave(state):
        saveChatState(state)

def enableAutoBanChannelPostingNoSave(state: ChatState) -> bool:
    if state.user_id is None and not state.auto_ban_sender_chats:
        state.auto_ban_sender_chats = True
        return True
    return False

def enableAutoBanChannelPosting(chat_id: int) -> None:
    state = chatState(chat_id)
    if enableAutoBanChannelPostingNoSave(state):
        saveChatState(state)

def disableAutoBanChannelPostingNoSave(state: ChatState) -> bool:
    if state.user_id is None and state.auto_ban_sender_chats:
        state.auto_ban_sender_chats = False
        return True
    return False

def disableAutoBanChannelPosting(chat_id: int) -> None:
    state = chatState(chat_id)
    if disableAutoBanChannelPostingNoSave(state):
        saveChatState(state)

def permitChannelPostsNoSave(state: ChatState, channel_id: int) -> bool:
    if not channel_id in state.permitted_channel_posts:
        state.permitted_channel_posts.add(channel_id)
        return True
    return False

def permitChannelPosts(chat_id: int, channel_id: int) -> None:
    state = chatState(chat_id)
    if permitChannelPostsNoSave(state, channel_id):
        saveChatState(state)

def revokeChannelPostsNoSave(state: ChatState, channel_id: int) -> bool:
    if channel_id in state.permitted_channel_posts:
        state.permitted_channel_posts.remove(channel_id)
        return True
    return False

def revokeChannelPosts(chat_id: int, channel_id: int) -> None:
    state = chatState(chat_id)
    if revokeChannelPostsNoSave(state, channel_id):
        saveChatState(state)




@with_connection
@with_cursor
def init():
    cur = localthreaddb.cur
    # Mod challenge table
    cur.execute("create table if not exists mod_challenge (chat_id, user_id, challenge, expires, message_id)")
    cur.execute(
        "create index if not exists mod_challenge_chat_user on mod_challenge (chat_id, user_id)")
    cur.execute(
        "create index if not exists mod_challenge_user on mod_challenge (user_id)")
    cur.execute(
        "create index if not exists mod_challenge_expires on mod_challenge (expires)")
    # Mod chat table
    cur.execute("create table if not exists mod_chat_state (chat_id, state)")
    cur.execute(
        "create index if not exists mod_chat_state_chat_id on mod_chat_state (chat_id)")

    try:
        cur.execute("alter table mod_challenge add column message_id")
    except:
        pass
