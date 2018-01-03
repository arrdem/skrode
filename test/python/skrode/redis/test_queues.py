from json import dumps, loads
from threading import Thread, Event

from skrode.redis.workqueue import Producer, Consumer

from redis import StrictRedis
from pytest import fixture

@fixture
def conn():
  rds = StrictRedis("localhost", db=15)
  rds.flushdb()
  return rds


def test_produce_consume(conn):
  source = Producer(conn, "test_key", encoder=dumps)
  sink0 = Consumer(conn, "test_key", "test_key_consumer_0", decoder=loads)
  sink1 = Consumer(conn, "test_key", "test_key_consumer_1", decoder=loads)

  for i in range(1, 100):
    source.put(i)
    assert len(source) == i
    with sink0.next() as next_value0:
      with sink1.next() as next_value1:
        assert i == next_value0 == next_value1

  assert len(sink0) == len(sink1) == 0
  assert len(source) == len(range(1, 100))
