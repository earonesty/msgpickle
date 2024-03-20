# msgpickle

`msgpickle` is a library that enhances `msgpack` for Python, providing extensive pickling mechanism, including lambda support.

## Description

Allows for the serialization and deserialization of complex Python objects using `msgpack`, with support for custom serialization methods for any object type, even those that cannot be modified directly.

## Installation


```
pip install msgpickle
```


## Usage

```python
import msgpickle

import datetime

# Example object
obj = datetime.datetime.now()

# serialize the object
serialized = msgpickle.dumps(obj)

# deserialize the object
deserialized = msgpickle.loads(serialized)

print(deserialized)
```

## Support lambdas, cloud-functions across server farms

Using the cloud_function_serializer, you can serilize lambdas, as long as the python version is the same.

```
serializer = msgpickle.MsgPickle(use_default=False)
serializer.register(*msgpickle.cloud_function_serializer)
```

Because `use_defaults` is false, that pickler won't serialize anything
except basic objects and lambdas

## Custom Serialization and Deserialization

```python

# Custom serialization function
def datetime_pack(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj

# Custom deserialization function
def datetime_unpack(obj):
    try:
        return datetime.fromisoformat(obj)
    except TypeError:
        return obj

# Register the custom functions for datetime
msgpickle.register('datetime.datetime', datetime_pack, datetime_unpack)
```

You may register "None" as either the pack or unpack function.   This will use the default instead for that class.

## Strict mode

Just like `msgpack`, you can specify "strict=True" on dump and/or load.   This will not use any "default handlers" for object, but will continue to use explicit registered handlers.

Disable, or rename object-oriented `from_pack` and `to_pack` to prevent a malicious payload from executing those functions.


```
pickler = MsgPickle(use_default=False, use_oo=None)
```

Easily create a truly safe pickler, even for complex objects.  Disabling the defaults and oo hooks is sufficient for security.   Strict mode, at that point, will just prevent msgpack from serializing tuples as lists.

## Custom object signatures

Normally, msgpickle pickles objects as a mapping with 3 keys:  ".", "#" and "d".   It then attempts to deserialize these using your registered handlers, etc.

However, you may want to customize the object signatures.   This can be done by overriding `pickler.CLASS` `pickler.MODULE` and `pickler.DATA`

## Compression signatures and enumeration

Normally, msgpickle pickles class and module information as strings.

This can be overridden by objects as a mapping with 3 keys:  ".", "#" and "d".   It then attempts to deserialize these using your registered handlers, etc.

However, you may want to customize the object signatures.   This can be done by overriding `pickler.CLASS` `pickler.MODULE` and `pickler.DATA` values.

Likewise, you may not want to serialize class names and module names.

You can enable enumeration using `pickler.use_enumeration([keys])`.   Without an explicit list of class paths, this will build an enumeration of all registered classes, and use that as your pickled values.   Needless to say, it's better to have an explicit list.   Changing this list or the order of the list will result in being unable to deserialize.


This will significantly compress the output.

## Advanced Usage

For more complex projects requiring different serialization/deserialization strategies, you can create instances of `MsgPickle` with custom serializers for specific types.

Here’s how to instantiate a `MsgPickle` object, localized to a module.

```python
from msgpickle import MsgPickle

msgpickle = MsgPickle()

msgpickle.register("my.class", packer, unpacker)

serialized_data = msgpickle.dumps(obj)
deserialized_data = msgpickle.loads(dat)

print(deserialized_data)
```

Alternately, you can create `to_pack()` and `from_pack()` functions in your class, which will be used instead.

## License

This project is licensed under the MIT License.
