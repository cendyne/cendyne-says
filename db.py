import sqlite3
import threading
import functools
import os

class ThreadDb(threading.local):
  con = None
  con: sqlite3.Connection
  cur = None
  cur: sqlite3.Cursor

localthreaddb = ThreadDb()

def create_connection() -> sqlite3.Connection:
  return sqlite3.connect(os.getenv("DB"))

def with_connection(func):
  @functools.wraps(func)
  def wrapper(*args, **kwargs):
    con = create_connection()
    # Preserve old connection and cursor
    oldcon = localthreaddb.con
    oldcur = localthreaddb.cur
    # Set current connection as the thread connection
    localthreaddb.con = con
    localthreaddb.cur = None
    try:
      result = func(*args, **kwargs)
      con.commit()
      return result
    except Exception as e:
      con.rollback()
      raise
    finally:
      con.close()
      # Restore old connection and cursor
      localthreaddb.con = oldcon
      localthreaddb.cur = oldcur
  return wrapper

def with_cursor(func):
  @functools.wraps(func)
  def wrapper(*args, **kwargs):
    con = localthreaddb.con
    cur = localthreaddb.cur
    
    if cur:
      # Rely on the upper execution to close the cursor and handle exceptions
      return func(*args, **kwargs)
    elif con:
      cur = con.cursor()
      localthreaddb.cur = cur
      try:
        return func(*args, **kwargs)
      except Exception as e:
        cur.rollback()
        raise
      finally:
        cur.close()
        # SQL in general can only have one cursor at a time.
        # Because we replaced it, it is not appropriate to restore it
        # as the cursro would not be valid
        localthreaddb.cur = None
    else:
      # Create a new connection and a new cursor
      con = create_connection()
      localthreaddb.con = con
      cur = con.cursor()
      localthreaddb.cur = con.cursor()
      try:
        result = func(*args, **kwargs)
        con.commit()
        return result
      except Exception as e:
        con.rollback()
        raise
      finally:
        cur.close()
        con.close()
        # Clear both as the connection was only used for this invocation
        localthreaddb.cur = None
        localthreaddb.con = None
  return wrapper
