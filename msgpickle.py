from datetime import datetime

import msgpack
import importlib
from typing import Any, Callable, Dict, Tuple, cast


class MsgPickle:
    CLASS = "."
    MODULE = "#"
    DATA = "d"

    def __init__(self) -> None:
        self.serializers: Dict[str, Tuple[Callable[[Any], Any], Callable[[Any], Any]]] = {}
        self.__sig = sorted([self.CLASS, self.MODULE, self.DATA])

    def dumps(self, obj: Any, strict: bool = False) -> bytes:
        """Serialize an object to msgpack format, with custom handling for objects with to_pack method."""

        def _dump_obj(o: Any) -> Dict[str, Any]:
            full_class_name = f"{o.__class__.__module__}.{o.__class__.__name__}"
            ret = {
                self.CLASS: type(o).__name__,
                self.MODULE: o.__class__.__module__,
            }
            if full_class_name in self.serializers and (serial := self.serializers[full_class_name]):
                pack, _ = serial
            else:
                pack = None
            if pack is not None:
                data = pack(o)
            elif hasattr(o, 'to_pack') and callable(o.to_pack):
                data = o.to_pack()
            elif not strict and ret[self.MODULE] not in ["builtins"]:
                data = self._default_obj_dump(o)
            else:
                raise TypeError(f"Object of type {full_class_name} is not serializable")
            ret[self.DATA] = data
            return ret

        return cast(bytes, msgpack.dumps(obj, default=_dump_obj, strict_types=True))

    def loads(self, packed: bytes, strict: bool = False) -> Any:
        """Deserialize a msgpack format object, with custom handling for objects with from_pack method."""

        def object_hook(code: Any) -> Any:
            if isinstance(code, dict) and sorted(code.keys()) == self.__sig:
                module_name = code[self.MODULE]
                class_name = code[self.CLASS]
                data = code[self.DATA]
                full_class_name = f"{module_name}.{class_name}"
                if full_class_name in self.serializers:
                    _, unpack = self.serializers[full_class_name]
                    if unpack is not None:
                        return unpack(data)
                try:
                    module = importlib.import_module(module_name)
                    cls = getattr(module, class_name)
                except (AttributeError, ImportError):
                    raise TypeError(f"Object of type {full_class_name} is not deserializable")
                if hasattr(cls, 'from_pack') and callable(cls.from_pack):
                    return cls.from_pack(data)
                if strict:
                    raise TypeError(f"Object of type {full_class_name} is not deserializable")
                return self._default_obj_load(cls, data)

            return code

        return msgpack.loads(packed, object_hook=object_hook)

    @staticmethod
    def _default_obj_dump(o: Any) -> Any:
        data: Any
        if hasattr(o, '__dict__') and isinstance(o.__dict__, dict):
            data = o.__dict__
        elif isinstance(o, tuple):
            data = list(o)
        elif hasattr(o, '__slots__'):
            data = {slot: getattr(o, slot) for slot in o.__slots__}
        else:
            raise TypeError(f"Object of type {type(o)} is not serializable")
        return data

    @staticmethod
    def _default_obj_load(cls: Any, data: Any) -> Any:
        if isinstance(data, list):
            return cls(*data)
        elif hasattr(cls, '__slots__'):
            inst = cls.__new__(cls, *data)
            for k, v in data.items():
                setattr(inst, k, v)
            return inst
        elif isinstance(data, dict):
            inst = cls.__new__(cls)
            inst.__dict__ = data
            return inst
        else:
            raise TypeError(f"Object of type {cls.__module__}.{cls.__name__} is not deserializable")

    def register(self, name: str, pack: Callable[[Any], Any], unpack: Callable[[Any], Any]) -> None:
        self.serializers[name] = (pack, unpack)


_glob = MsgPickle()

dumps = _glob.dumps
loads = _glob.loads
register = _glob.register


def datetime_pack(obj):
    return obj.isoformat()


def datetime_unpack(obj):
    return datetime.fromisoformat(obj)


register('datetime.datetime', datetime_pack, datetime_unpack)
