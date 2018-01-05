"""
A simple durable queue backed by Redis.
"""

from redis import WatchError


class _AppendSeq(object):
  """Helper class.

  Redis lists have unfortunate performance characteristics - while they claim to provide atomic
  access and some scanning semantics along with constant time push or pop to either side, none of
  these properties are critical for the semantic needs of Skrode as a service.

  Skrode needs atomic append, and constant time access to indexed sequence elements.

  This is implemented by using a single key to track the length of the list, and storing each
  element of the list in its own key.

  Deletion of elements from the list is not supported.
  """

  def __init__(self, conn, key, suffix="/"):
    self._conn = conn
    self._key = key
    self._suffix = suffix

  def __idx_key__(self, idx):
    return "%s%s%016x" % (self._key, self._suffix, idx)

  def __len__(self):
    """Returns the length of the list.

    FIXME: does int support big (64bi) values? It should...
    """
    return int(self._conn.get(self._key) or "0")

  def __getitem__(self, idx):
    assert isinstance(idx, int)

    with self._conn.pipeline() as tx:
      while True:
        try:
          tx.watch(self._key)
          tx.watch(self.__idx_key__(idx))

          max_idx = int(tx.get(self._key) or "0")

          tx.multi()

          if max_idx > idx:
            tx.get(self.__idx_key__(idx))
            return tx.execute()[0]

          break

        except WatchError:
          continue

        finally:
          tx.reset()

    raise IndexError()

  def push(self, val):
    """
    Atomically pushes the given value to the end of the list.
    """

    with self._conn.pipeline() as tx:
      while True:
        try:
          tx.watch(self._key)
          next_idx = int(self._conn.get(self._key) or "0")
          tx.multi()
          self._conn.set(self.__idx_key__(next_idx), val)
          # FIXME (arrdem 2018-01-03):
          #   Could this be incr?
          self._conn.set(self._key, next_idx + 1)
          tx.execute()
          return next_idx

        except WatchError:
          continue

        finally:
          tx.reset()


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

  def __init__(self, conn, key, list, idx, decoder=None):
    self._conn = conn
    self._key = key
    self._list = list
    self._idx = idx
    self._decoder = decoder or (lambda x: x)

  @property
  def value(self):
    return self._decoder(self._list[self._idx])

  def complete(self):
    """FIXME: this is a no-op for now."""
    pass

  def abort(self):
    """Admit a failure to process this work item and put it back on the queue."""

    self._conn.set(self._key, self._idx)

  def __enter__(self):
    return self.value

  def __exit__(self, type, value, traceback):
    if type is None and value is None and traceback is None:
      # We processed the work item successfully as far as we can tell
      self.complete()
    else:
      self.abort()


class Producer(object):
  """A helper type which represents a writer to a durable FIFO queue.

  Users may enqueue blobs.

  A `WorkQueueConsumer` may be used to separately recover :py:class:`WorkItem` instances which wrap
  blobs.

  The queue is backed by a `BigList`
  """

  def __init__(self, conn, key, encoder=None):
    self._conn = conn
    self._list = _AppendSeq(conn, key)
    self._encoder = encoder or (lambda x: x)

  def __len__(self):
    return len(self._list)

  def put(self, value):
    value = self._encoder(value)
    return self._list.push(value)


class Consumer(object):
  """A helper type which represents a consumer over a durable FIFO queue.

  Iterates over enqueued blobs as WorkItems, maintaining a durable index of the last WorkItem which
  was acknowledged as completed. Maintains a persistent cursor in the backing Redis store tracking
  the index of the last successfully consumed work item. If a work item fails to process, the cursor
  is RESET to the index of the failed item. This leads to at least once processing of all records,
  unless sufficient error handling is provided on the client side.

  """

  def __init__(self, conn, key, consumer_id, decoder=None):
    self._conn = conn
    self._list = _AppendSeq(conn, key)
    self._key = consumer_id
    self._decoder = decoder

  def __iter__(self):
    return self

  def __len__(self):
    with self._conn.pipeline() as tx:
      while True:
        try:
          tx.watch(self._key)
          tx.watch(self._list._key)

          max_idx = int(tx.get(self._list._key) or "0")
          cur_idx = int(tx.get(self._key) or "0")

          return cur_idx - max_idx

        except WatchError:
          continue

        finally:
          tx.reset()

  def next(self):
    # FIXME (arrdem 2018-01-02):
    #   when to throw StopIterationException?

    with self._conn.pipeline() as tx:
      while True:
        try:
          tx.watch(self._list._key)
          tx.watch(self._key)

          max_idx = int(tx.get(self._list._key) or "0")
          cur_idx = int(tx.get(self._key) or "0")

          if max_idx == cur_idx:
            raise StopIteration

          else:
            tx.multi()
            tx.incr(self._key)
            tx.execute()
            return WorkItem(self._conn, self._key, self._list, cur_idx,
                            decoder=self._decoder)

        except WatchError:
          continue

        finally:
          tx.reset()


class WorkQueue(object):
  """A compatibility shim back to the old API.

  Provides `.put` and `.get`, using an implicit single shared consumer ID across all connected
  clients.
  """

  def __init__(self, conn, key, inflight=None, indirect=False, decoder=None, encoder=None):
    self._conn = conn
    self._producer = Producer(conn, key, encoder=encoder)
    self._consumer = Consumer(conn, key, "%s/implicit_consumer" % (key,), decoder=decoder)

  def __len__(self):
    return len(self._consumer)

  def put(self, val):
    return self._producer.put(val)

  def get(self):
    try:
      return self._consumer.next()
    except StopIteration:
      return None
