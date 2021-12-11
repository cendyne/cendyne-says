from typing import Text

from db import localthreaddb, with_cursor, with_connection


@with_cursor
def isTombstoned(key: Text) -> bool:
    [results] = localthreaddb.cur.execute("select count(*) from says_tombstone where input = :key", {
        "key": key
    }).fetchone()
    return results > 0


@with_cursor
def tombstone(key: Text) -> bool:
    localthreaddb.cur.execute("insert into says_tombstone (input) values (:key) ", {
        "key": key
    })


@with_cursor
def cachedText(key: Text) -> bool:
    results = localthreaddb.cur.execute("select file_id from says_text_cache where input = :key", {
        "key": key
    }).fetchone()
    if results:
        return results[0]
    else:
        return None


@with_cursor
def cacheText(key: Text, file_id: Text) -> bool:
    localthreaddb.cur.execute("insert into says_text_cache(input, file_Id) values(:key, :file_id)", {
        "key": key,
        "file_id": file_id
    })


@with_connection
@with_cursor
def init():
    cur = localthreaddb.cur

    cur.execute("create table if not exists says_text_cache (input, file_id)")
    cur.execute(
        "create index if not exists says_text_cache_idx on says_text_cache (input)")

    cur.execute("create table if not exists says_tombstone (input)")
    cur.execute(
        "create index if not exists says_tombstone_idx on says_tombstone (input)")
