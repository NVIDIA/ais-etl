#
# Copyright (c) 2021, NVIDIA CORPORATION. All rights reserved.
#


class BuildETL:
    def __init__(
        self, code, deps, comm_type, id="", runtime="python3"
    ) -> None:
        self.code = code
        self.dependencies = deps
        self.id = id
        self.runtime = runtime
        self.communication_type = comm_type

    def json(self):
        return self.__dict__


class Bck:
    def __init__(self, name, provider="ais", ns="") -> None:
        self.provider = provider
        self.name = name
        self.namespace = ns


class Bck2BckMsg:
    def __init__(self, id) -> None:
        self.id = id
        # TODO: add other params


class ActionMsg:
    def __init__(self, action, name, value) -> None:
        self.action = action
        self.name = name
        self.value = value

    def json(self):
        return _to_json(self)


def _to_json(value):
    result = {}
    for k in value.__dict__:
        val = value.__dict__[k]
        if hasattr(val, "__dict__"):
            val = _to_json(val)
        result[k] = val
    return result
