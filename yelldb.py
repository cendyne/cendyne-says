import pickle
import base64
import logging
from typing import List, Text, Tuple, Union
from dataclasses import dataclass
from db import localthreaddb, with_cursor, with_connection


@with_cursor
def isTombstoned(key: Text) -> bool:
    [results] = localthreaddb.cur.execute("select count(*) from yell_tombstone where input = :key", {
        "key": key
    }).fetchone()
    return results > 0


@with_cursor
def tombstone(key: Text) -> bool:
    localthreaddb.cur.execute("insert into yell_tombstone (input) values (:key) ", {
        "key": key
    })


@with_cursor
def cachedFile(file_id: Text) -> bool:
    results = localthreaddb.cur.execute("select file_id from yell_cache where input_file_id = :file_id", {
        "file_id": file_id
    }).fetchone()
    if results:
        return results[0]
    else:
        return None


@with_cursor
def cacheFile(key: Text, file_id: Text) -> bool:
    localthreaddb.cur.execute("insert into yell_cache(input_file_id, file_Id) values(:key, :file_id)", {
        "key": key,
        "file_id": file_id
    })


@with_cursor
def cachedText(key: Text) -> bool:
    results = localthreaddb.cur.execute("select file_id from yell_text_cache where input = :key", {
        "key": key
    }).fetchone()
    if results:
        return results[0]
    else:
        return None


@with_cursor
def cacheText(key: Text, file_id: Text) -> bool:
    localthreaddb.cur.execute("insert into yell_text_cache(input, file_Id) values(:key, :file_id)", {
        "key": key,
        "file_id": file_id
    })


@with_cursor
def findPending(identity: Text) -> Tuple[Text, Text, int, int]:
    return localthreaddb.cur.execute("select name, file_id, chat_id, message_id from yell_pending where id = :identity", {
        "identity": identity
    }).fetchone()


@with_cursor
def findAllPending() -> List[Tuple[int, Text, Text]]:
    return localthreaddb.cur.execute("select id, name, file_id from yell_pending").fetchall()


@with_cursor
def countPending(name: Text, file_id: Text) -> int:
    [result] = localthreaddb.cur.execute("select count(*) from yell_pending where name = :name and file_id = :file_id", {
        "name": name,
        "file_id": file_id,
    }).fetchone()
    return result


@with_cursor
def deletePending(identity: Text):
    localthreaddb.cur.execute(
        "delete from yell_pending where id = :identity", {"identity": identity})


@with_cursor
def learn(name: Text, file_id: Text):
    localthreaddb.cur.execute("insert into yell_learn (name, file_id) values (:name, :file_id)", {
        "name": name,
        "file_id": file_id
    })


@with_cursor
def countLearned(name: Text, file_id: Text) -> int:
    [result] = localthreaddb.cur.execute("select count(*) from yell_learn where name = :name and file_id = :file_id", {
        "name": name,
        "file_id": file_id,
    }).fetchone()
    return result


@with_cursor
def findLearned(query: Text) -> List[Tuple[Text, Text]]:
    cursor = localthreaddb.cur
    sql = "select name, file_id from yell_learn where name like :name order by random()"
    name = "%"
    counter = 0
    for part in query.split():
        part = part.strip()
        if len(part) > 0:
            if counter > 0:
                name += "%"
            counter += 1
            name += part
    name += "%"
    if counter == 0:
        return cursor.execute("select name, file_id from yell_learn order by random()")
    else:
        logging.info("Searching for %s", name)
        return cursor.execute(sql, {"name": name})


@with_cursor
def submit(identity: Text, name: Text, file_id: Text, chat_id: Text, message_id: Text):
    localthreaddb.cur.execute("insert into yell_pending(id, name, file_id, chat_id, message_id) values (:identity, :name, :file_id, :chat_id, :message_id)", {
        "identity": identity,
        "name": name,
        "file_id": file_id,
        "chat_id": chat_id,
        "message_id": message_id,
    })


@dataclass
class ChatState:
    chat_id: int
    file_id: Union[int, None] = None
    input: Union[Text, None] = None
    message_id: Union[int, None] = None
    learning: bool = False


@with_cursor
def chatState(chat_id: int) -> ChatState:
    result = localthreaddb.cur.execute("select state from yell_chat_state where chat_id = :chat_id", {
        "chat_id": chat_id
    }).fetchone()
    if result and len(result) > 0:
        state = pickle.loads(base64.standard_b64decode(result[0]))
        logging.info("Got chat state %s", state)
        return state
    return ChatState(chat_id=chat_id)


@with_cursor
def saveChatState(state: ChatState):
    chat_id = state.chat_id
    logging.info("Saving chat state: %s", state)
    body = base64.standard_b64encode(pickle.dumps(state))
    [count] = localthreaddb.cur.execute("select count(*) from yell_chat_state where chat_id = :chat_id", {
        "chat_id": chat_id
    }).fetchone()
    if count and count > 0:
        localthreaddb.cur.execute("update yell_chat_state set state = :state where chat_id = :chat_id", {
            "chat_id": chat_id,
            "state": body
        })
    else:
        localthreaddb.cur.execute("insert into yell_chat_state(chat_id, state) values (:chat_id, :state)", {
            "chat_id": chat_id,
            "state": body
        })


@with_connection
@with_cursor
def init():
    cur = localthreaddb.cur
    cur.execute("create table if not exists yell_cache (input_file_id, file_id)")
    cur.execute(
        "create index if not exists yell_cache_idx on yell_cache (input_file_id)")

    cur.execute("create table if not exists yell_learn (name, file_id)")

    cur.execute(
        "create table if not exists yell_pending (id, name, file_id, chat_id, message_id)")
    cur.execute(
        "create index if not exists yell_pending_id on yell_pending (id)")

    cur.execute("create table if not exists yell_text_cache (input, file_id)")
    cur.execute(
        "create index if not exists yell_text_cache_idx on yell_text_cache (input)")

    cur.execute("create table if not exists yell_tombstone (input)")
    cur.execute(
        "create index if not exists yell_tombstone_idx on yell_tombstone (input)")

    cur.execute("create table if not exists yell_chat_state (chat_id, state)")
    cur.execute(
        "create index if not exists yell_chat_state_chat_id on yell_chat_state (chat_id)")
