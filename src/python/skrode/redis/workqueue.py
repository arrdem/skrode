"""
A simple durable queue backed by Redis.
"""

import logging
from uuid import uuid4


class WorkItem(object):
  """
  Helper class to WorkQueue.

  Represents a unit of work to be done as returned by `WorkQueue.get`.

  The item's value is accessed either as a context manager `as` value, or via the `.value` member.

  When this type is used as a context manager, it automates enqueuing and dequeueing work items.

  .. code-block:: python

     while True:
       item = work_queue.get()
       if workitem is not None:
         with workitem as job:
           # ... process the item
         continue
       else:
         sleep(5)
  """

  def __init__(self, conn, src_worklist, abort_worklist, item_or_id, indirect=False, decoder=None):
    self._conn = conn
    self._src_worklist = src_worklist
    self._abort_worklist = abort_worklist
    self._indirect = indirect
    self._decoder = decoder
    self._item_or_id = item_or_id

  @property
  def value(self):
    if self._indirect:
      val = self._conn.get(self._item_or_id)
    else:
      val = self._item_or_id
    return self._decoder(val)

  def complete(self):
    """Remove all instances of this item from the worklist & delete it from the db."""

    self._conn.lrem(self._src_worklist, 0, self._item_or_id)
    if self._indirect:
      self._conn.delete(self._item_or_id)

  def abort(self):
    """Admit a failure to process this work item and put it back on the queue."""

    self._conn.lpush(self._abort_worklist, self._item_or_id)

  def __enter__(self):
    return self.value

  def __exit__(self, type, value, traceback):
    if type is None and value is None and traceback is None:
      # We processed the work item successfully as far as we can tell
      self.complete()
    else:
      self.abort()


class WorkQueue(object):
  """
  A helper type which represents a durable FIFO queue.

  Users may enqueue blobs, and recover :py:class:`WorkItem` instances which wrap blobs.

  When a WorkItem is removed from the queue, it becomes placed on a parallel "in flight" queue with
  the expectation that the user who removed it from the "waiting" queue will either delete it from
  the in flight queue when it is completed or return it to the waiting queue.

  WorkItems form a context manager which provides these semantics automatically. If an exception
  occurs in the context body, the WorkItem is considered to have failed and is returned to the
  pending queue, otherwise it is considered to have succeeded and is removed from the in flight
  queue.
  """

  def __init__(self, conn, key, inflight=None, indirect=False, decoder=None, encoder=None):
    self._conn = conn
    self._key = key
    self._inflight = inflight or key
    self._indirect = indirect
    self._encoder = encoder or (lambda x: x)
    self._decoder = decoder or (lambda x: x)

  def put(self, value):
    value = self._encoder(value)
    if self._indirect:
      item_id = uuid4()
      self._conn.set(item_id, value)
      self._conn.lpush(self._key, item_id)
    else:
      for _val in self._conn.lrange(self._key, 0, -1):
        if _val == value:
          logging.info("Skipping duplicate work item...")
          return
      self._conn.lpush(self._key, value)

  def get(self):
    item_or_id = self._conn.rpoplpush(self._key, self._inflight)
    self._conn
    if item_or_id is not None:
      return WorkItem(self._conn, self._inflight, self._key, item_or_id,
                      indirect=self._indirect,
                      decoder=self._decoder)

  def __len__(self):
    return self._conn.llen(self._key)
