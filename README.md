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
serializer = msgpickle.MsgPickle()
serializer.register(*msgpickle.cloud_function_serializer)
```

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


## License

This project is licensed under the MIT License.
