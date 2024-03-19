from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
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


def pack_datetime(dt):
    return dt.isoformat()


def unpack_datetime(dt_str):
    return datetime.fromisoformat(dt_str)


# Register the datetime serializer
msgpickle.register('datetime.datetime', pack_datetime, unpack_datetime)


@pytest.mark.parametrize("strict", [True, False])
def test_datetime_serialization(strict):
    original_datetime = datetime.now()
    serialized = msgpickle.dumps(original_datetime, strict=strict)
    deserialized_datetime = msgpickle.loads(serialized, strict=strict)
    assert deserialized_datetime == original_datetime


def test_non_serializable_function_raises():
    serializer = msgpickle.MsgPickle()

    with pytest.raises(TypeError) as exc_info:
        serializer.dumps(lambda  x: x)

    assert "Object of type" in str(exc_info.value) and "is not serializable" in str(exc_info.value)


class Slotted:
    __slots__ = ['attr']  # This prevents the class from having a __dict__

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
    ser = msgpack.dumps({msgpickle.MsgPickle.CLASS: 1, msgpickle.MsgPickle.MODULE: 2, msgpickle.MsgPickle.DATA: 3})
    with pytest.raises(TypeError):
        serializer.loads(ser)
    ser = msgpack.dumps(
        {msgpickle.MsgPickle.CLASS: "datetime", msgpickle.MsgPickle.MODULE: "datetime", msgpickle.MsgPickle.DATA: None})
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