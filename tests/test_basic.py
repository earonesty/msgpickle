import threading
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, time
from typing import NamedTuple

import msgpack
import pytest

import msgpickle


class CustomClass:
    def __init__(self, attr1=None, attr2=None):
        self.attr1 = attr1
        self.attr2 = attr2

    def to_pack(self):
        return self.__dict__

    @classmethod
    def from_pack(cls, data):
        return cls(**data)

    def __repr__(self):
        return f"CustomClass(attr1={self.attr1}, attr2={self.attr2})"


@dataclass
class ExampleDataClass:
    field1: int
    field2: str


class ExampleNamedTuple(NamedTuple):
    field1: int
    field2: str


def test_CustomClass_serialization():
    obj = CustomClass(attr1="test1", attr2="test2")
    serialized = msgpickle.dumps(obj)
    deserialized = msgpickle.loads(serialized)
    assert deserialized.attr1 == obj.attr1 and deserialized.attr2 == obj.attr2


def test_ExampleDataClass_serialization():
    obj = ExampleDataClass(field1=123, field2="abc")
    serialized = msgpickle.dumps(obj)
    deserialized = msgpickle.loads(serialized)
    assert deserialized.field1 == obj.field1 and deserialized.field2 == obj.field2


def test_ExampleNamedTuple_serialization():
    obj = ExampleNamedTuple(field1=456, field2="def")
    serialized = msgpickle.dumps(obj)
    deserialized = msgpickle.loads(serialized)
    assert deserialized.field1 == obj.field1 and deserialized.field2 == obj.field2


def test_namedtuple_must_be_strict_serialization():
    obj = ExampleNamedTuple(field1=456, field2="def")
    with pytest.raises(TypeError):
        msgpickle.dumps(obj, strict=True)
    serialized = msgpickle.dumps(obj)
    with pytest.raises(TypeError):
        msgpickle.loads(serialized, strict=True)


def pack_time(dt):
    return dt.isoformat()


def unpack_time(dt_str):
    return time.fromisoformat(dt_str)


# Register the datetime serializer
msgpickle.register("datetime.time", pack_time, unpack_time)


@pytest.mark.parametrize("strict", [True, False])
def test_time_serialization(strict):
    original_time = time(1, 2)
    serialized = msgpickle.dumps(original_time, strict=strict)
    deserialized_time = msgpickle.loads(serialized, strict=strict)
    assert deserialized_time == original_time


def test_partial_registration():
    serializer = msgpickle.MsgPickle()
    original_time = time(1, 2)
    with pytest.raises(TypeError):
        serializer.dumps(original_time)

    serializer.register("datetime.time", pack_time, None)
    serialized = serializer.dumps(original_time)
    with pytest.raises(TypeError):
        deserialized_time = serializer.loads(serialized)
    serializer.register("datetime.time", None, unpack_time)
    deserialized_time = serializer.loads(serialized)
    assert deserialized_time == original_time


@pytest.mark.parametrize("strict", [True, False])
def test_datetime_serialization(strict):
    original_datetime = datetime.now()
    serialized = msgpickle.dumps(original_datetime, strict=strict)
    deserialized_datetime = msgpickle.loads(serialized, strict=strict)
    assert deserialized_datetime == original_datetime


def func1():
    return 1


@pytest.mark.parametrize("strict", [True, False])
def test_function_serialization(strict):
    serialized = msgpickle.dumps(func1, strict=strict)
    deserialized_func = msgpickle.loads(serialized, strict=strict)
    assert deserialized_func() == 1


def test_non_serializable_function_raises():
    serializer = msgpickle.MsgPickle()

    with pytest.raises(TypeError) as exc_info:
        serializer.dumps(lambda x: x)

    assert "Object of type" in str(exc_info.value) and "is not serializable" in str(
        exc_info.value
    )


def test_cloud_functions():
    serializer = msgpickle.MsgPickle(use_default=False)
    serializer.register(*msgpickle.cloud_function_serializer)
    res = serializer.dumps(lambda x: 4)
    ok = serializer.loads(res)
    assert ok(4) == 4


def test_non_serializable_stuff(tmp_path):
    serializer = msgpickle.MsgPickle()

    with open(tmp_path / "x", "w") as of:
        with pytest.raises(TypeError):
            serializer.dumps(of)

    with pytest.raises(TypeError):
        serializer.dumps(threading.Thread())

    with pytest.raises(TypeError):
        serializer.dumps(threading.Lock())


class Slotted:
    __slots__ = ["attr"]  # This prevents the class from having a __dict__

    def __init__(self, attr):
        self.attr = attr


def test_slotted():
    serializer = msgpickle.MsgPickle()
    obj = Slotted(123)
    ser = serializer.dumps(obj)
    deser = serializer.loads(ser)
    assert deser.attr == obj.attr


def test_bad_loader():
    serializer = msgpickle.MsgPickle()
    ser = msgpack.dumps(
        {
            msgpickle.MsgPickle.CLASS: 1,
            msgpickle.MsgPickle.MODULE: 2,
            msgpickle.MsgPickle.DATA: 3,
        }
    )
    with pytest.raises(TypeError):
        serializer.loads(ser)
    ser = msgpack.dumps(
        {
            msgpickle.MsgPickle.CLASS: "datetime",
            msgpickle.MsgPickle.MODULE: "datetime",
            msgpickle.MsgPickle.DATA: None,
        }
    )
    with pytest.raises(TypeError):
        serializer.loads(ser)


def test_bad_obj():
    class BadClass:
        pass

    b = BadClass()

    # don't serialize classes that don't have a normalish __dict__
    b.__dict__ = defaultdict()

    with pytest.raises(TypeError):
        msgpickle.dumps(b)
