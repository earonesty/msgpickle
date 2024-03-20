import importlib
import inspect
import io
import types
from datetime import datetime
from typing import Any, Callable, Dict, cast, Optional, Iterable

import msgpack


class Unhandled:
    pass


def datetime_pack(obj: Any) -> Any:
    return obj.isoformat()


def datetime_unpack(obj: Any) -> Any:
    return datetime.fromisoformat(obj)


datetime_serializer = ("datetime.datetime", datetime_pack, datetime_unpack)


def callable_pack(obj: Any) -> Any:
    module = importlib.import_module(obj.__module__)
    if getattr(module, obj.__name__, None) is not obj:
        return Unhandled
    return [obj.__module__, obj.__name__]


def callable_unpack(obj: Any) -> Any:
    module_name, func_name = obj
    module = importlib.import_module(module_name)
    return getattr(module, func_name)


function_serializer = ("builtins.function", callable_pack, callable_unpack)
class_serializer = ("builtins.type", callable_pack, callable_unpack)

code_type_params = inspect.signature(types.CodeType).parameters


def cloud_func_pack(obj: Any) -> Any:
    code_obj = obj.__code__
    # this has a chance of working for future versions of Python
    xmap = {"codestring": "code", "constants": "consts"}
    code_arg_names = [
        "co_" + xmap.get(param.name, param.name) for param in code_type_params.values()
    ]

    def convert(value: Any) -> Any:
        if isinstance(value, tuple):
            return list(value)
        return value

    code_attributes = [convert(getattr(code_obj, attr)) for attr in code_arg_names]
    return code_attributes


def cloud_func_unpack(obj: Any) -> Any:
    def convert(value: Any) -> Any:
        if isinstance(value, list):
            return tuple(value)
        return value

    code_obj = types.CodeType(*[convert(v) for v in obj])
    return types.FunctionType(code_obj, globals(), code_obj.co_name)


cloud_function_serializer = ("builtins.function", cloud_func_pack, cloud_func_unpack)


class MsgPickle:
    CLASS = "."
    MODULE = "#"
    DATA = "d"

    def __init__(
        self,
        use_default: bool = True,
        use_oo: None | tuple[str, str] = ("from_pack", "to_pack"),
    ) -> None:
        self._name_map: dict[str, int] = {}
        self._num_map: dict[int, str] = {}
        self.loaders: Dict[str, Callable[[Any], Any]] = {}
        self.dumpers: Dict[str, Callable[[Any], Any]] = {}
        self.hooks: list[Callable[[Any, Any], Any]] = []
        self.handlers: list[Callable[[Any], Any]] = []

        self.__sig = sorted([self.CLASS, self.MODULE, self.DATA])

        if use_default:
            self.add_handler(self._default_obj_dump)
            self.add_hook(self._default_obj_load)
            self.register(*datetime_serializer)
            self.register(*function_serializer)

        self.use_oo = use_oo

    def use_enumeration(self, enum: Optional[Iterable[str]] = None) -> None:
        if enum is None:
            enum = list(self.dumpers.keys())
        self._name_map = {k: i for i, k in enumerate(enum)}
        self._num_map = {i: k for i, k in enumerate(enum)}

    def dumps(self, obj: Any, strict: bool = False) -> bytes:
        """Serialize an object to msgpack format, with custom handling for objects with to_pack method."""

        def _dump_obj(o: Any) -> Dict[str, Any]:
            cls_name: str | int = type(o).__name__
            mod_name = o.__class__.__module__
            full_class_name = f"{mod_name}.{cls_name}"
            if self._name_map:
                cls_name = self._name_map[full_class_name]
                mod_name = ""
            ret = {
                self.CLASS: cls_name,
                self.MODULE: mod_name,
            }
            data = Unhandled
            if serial := self.dumpers.get(full_class_name):
                data = serial(o)
            elif (
                self.use_oo
                and hasattr(o, self.use_oo[1])
                and callable(getattr(o, self.use_oo[1]))
            ):
                data = getattr(o, self.use_oo[1])()
            elif not strict:
                for handler in self.handlers:
                    data = handler(o)
                    if data is not Unhandled:
                        break
            if data is Unhandled:
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
                if self._num_map:
                    module_name, class_name = self._num_map[class_name].rsplit(".", 1)
                full_class_name = f"{module_name}.{class_name}"
                data = code[self.DATA]
                if loader := self.loaders.get(full_class_name):
                    return loader(data)
                try:
                    module = importlib.import_module(module_name)
                    cls = getattr(module, class_name)
                except (AttributeError, ImportError):
                    raise TypeError(
                        f"Object of type {full_class_name} is not deserializable"
                    )
                if (
                    self.use_oo
                    and hasattr(cls, self.use_oo[0])
                    and callable(getattr(cls, self.use_oo[0]))
                ):
                    return cls.from_pack(data)
                if strict:
                    raise TypeError(
                        f"Object of type {full_class_name} is not deserializable"
                    )
                ret = Unhandled
                for hook in self.hooks:
                    ret = hook(cls, data)
                    if ret is not Unhandled:
                        return ret
                if ret is Unhandled:
                    raise TypeError(
                        f"Object of type {full_class_name} is not deserializable"
                    )
            return code

        return msgpack.loads(packed, object_hook=object_hook)

    @staticmethod
    def _default_obj_dump(o: Any) -> Any:
        if isinstance(o, io.IOBase):
            return Unhandled

        data: Any
        if hasattr(o, "__dict__") and isinstance(o.__dict__, dict):
            data = o.__dict__
        elif isinstance(o, tuple):
            data = list(o)
        elif hasattr(o.__class__, "__slots__"):
            data = {slot: getattr(o, slot) for slot in o.__slots__}
        else:
            return Unhandled

        return data

    @staticmethod
    def _default_obj_load(cls: Any, data: Any) -> Any:
        if isinstance(data, list):
            return cls(*data)
        elif hasattr(cls, "__slots__"):
            inst = cls.__new__(cls, *data)
            for k, v in data.items():
                setattr(inst, k, v)
            return inst
        elif isinstance(data, dict):
            inst = cls.__new__(cls)
            inst.__dict__ = data
            return inst

        return Unhandled

    def register(
        self, name: str, pack: Callable[[Any], Any], unpack: Callable[[Any], Any]
    ) -> None:
        if pack is not None:
            self.dumpers[name] = pack
        if unpack is not None:
            self.loaders[name] = unpack

    def add_hook(self, hook: Callable[[Any, Any], Any]) -> None:
        self.hooks.append(hook)

    def add_handler(self, handler: Callable[[Any], Any]) -> None:
        self.handlers.append(handler)


_glob = MsgPickle()

dumps = _glob.dumps
loads = _glob.loads
register = _glob.register

__all__ = [
    "dumps",
    "loads",
    "register",
    "MsgPickle",
    "Unhandled",
    "datetime_serializer",
    "function_serializer",
    "cloud_function_serializer",
]
