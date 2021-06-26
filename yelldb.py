from typing import List, Text, Tuple
from db import localthreaddb, with_cursor, with_connection
import logging

@with_cursor
def isTombstoned(input: Text) -> bool:
  [results] = localthreaddb.cur.execute("select count(*) from yell_tombstone where input = :input", {
      "input": input
  }).fetchone()
  return results > 0

@with_cursor
def tombstone(input: Text) -> bool:
  localthreaddb.cur.execute("insert into yell_tombstone (input) values (:input) ", {
      "input": input
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
def cacheFile(input: Text, file_id: Text) -> bool:
  localthreaddb.cur.execute("insert into yell_cache(input_file_id, file_Id) values(:input, :file_id)", {
    "input": input,
    "file_id": file_id
  })

@with_cursor
def cachedText(input: Text) -> bool:
  results = localthreaddb.cur.execute("select file_id from yell_text_cache where input = :input", {
    "input": input
  }).fetchone()
  if results:
    return results[0]
  else:
    return None
  

@with_cursor
def cacheText(input: Text, file_id: Text) -> bool:
  localthreaddb.cur.execute("insert into yell_text_cache(input, file_Id) values(:input, :file_id)", {
    "input": input,
    "file_id": file_id
  })


@with_cursor
def findPending(id: Text) -> [Text, Text, int, int]:
 return localthreaddb.cur.execute("select name, file_id, chat_id, message_id from yell_pending where id = :id", {
   "id": args[1]
  }).fetchone()

@with_cursor
def countPending(name: Text, file_id: Text) -> int:
  [result] = localthreaddb.cur.execute("select count(*) from yell_pending where name = :name and file_id = :file_id", {
    "name": name,
    "file_id": file_id,
  }).fetchone()
  return result

@with_cursor
def deletePending(id: Text):
  localthreaddb.cur.execute("delete from yell_pending where id = :id", {"id": id})

@with_cursor
def learn(name: Text, file_id: Text):
  localthreaddb.cur.execute("insert into yell_learn (name, file_id) values (:name, :file_id)", {
    "name": name,
    "file_id": fileId
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
    logging.info("Searching for %s",name)
    return cursor.execute(sql, {"name": name})

@with_cursor
def submit(id: Text, name: Text, file_id: Text, chat_id: Text, message_id: Text):
  localthreaddb.cur.execute("insert into yell_pending(id, name, file_id, chat_id, message_id) values (:id, :name, :file_id, :chat_id, :message_id)", {
    "id": id,
    "name": name,
    "file_id": file_id,
    "chat_id": chat_id,
    "message_id": message_id,
  })

@with_connection
@with_cursor
def init():
  cur = localthreaddb.cur
  cur.execute("create table if not exists yell_cache (input_file_id, file_id)")
  cur.execute("create index if not exists yell_cache_idx on yell_cache (input_file_id)")

  cur.execute("create table if not exists yell_learn (name, file_id)")

  cur.execute("create table if not exists yell_pending (id, name, file_id, chat_id, message_id)")
  cur.execute("create index if not exists yell_pending_id on yell_pending (id)")
  
  cur.execute("create table if not exists yell_text_cache (input, file_id)")
  cur.execute("create index if not exists yell_text_cache_idx on yell_text_cache (input)")

  cur.execute("create table if not exists yell_tombstone (input)")
  cur.execute("create index if not exists yell_tombstone_idx on yell_tombstone (input)")
