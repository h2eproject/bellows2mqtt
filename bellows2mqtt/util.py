from traceback import print_tb
import _thread
import os
import json
import enum
import logging

from zigpy.zdo.types import NodeDescriptor
from zigpy.device import Device
from zigpy.endpoint import Endpoint, Status as EndpointStatus
from zigpy.types.named import EUI64
from zigpy.zdo import ZDO

LOGGER = logging.getLogger(__name__)


def print_error(e):
    print_tb(e.__traceback__)


def exit_process():
    os._exit(1)


def select_keys(obj, keys):
    res = {}
    source_is_dict = isinstance(obj, dict)
    for key in keys:
        if source_is_dict:
            res[key] = obj[key]
        else:
            res[key] = getattr(obj, key)
    return res


def is_serializable(obj):
    if isinstance(obj, list):
        all_serializable = set([is_serializable(x) for x in obj])
        return False not in all_serializable
    elif isinstance(obj, dict):
        all_serializable = set([is_serializable(v) for _, v in obj])
        return False not in all_serializable
    else:
        return isinstance(obj, str) or isinstance(obj, int) or isinstance(obj, float) or obj is None


def serialize_object_as_dict(cls, keys):
    def serialize(self):
        return select_keys(self, keys)
    cls.to_json = serialize

def _default(self, obj):
    if isinstance(obj, ZDO):
        return 'ZDO'
    elif isinstance(obj, enum.Enum):
        return obj.name
    elif isinstance(obj, EUI64):
        return obj.__repr__()
    elif hasattr(obj, '__iter__') and not isinstance(obj, list) and not isinstance(obj, str):
        return list(obj)
    else:
        return getattr(obj.__class__, "to_json", _default.default)(obj)


_default.default = json.JSONEncoder().default
json.JSONEncoder.default = _default
serialize_object_as_dict(Device, [
    'ieee',
    'manufacturer',
    'manufacturer_id',
    'model',
    'skip_configuration',
    'relays',
    'node_desc',
    'endpoints'
])
serialize_object_as_dict(NodeDescriptor, [
    'byte1',
    'byte2',
    'mac_capability_flags',
    'manufacturer_code',
    'maximum_buffer_size',
    'maximum_incoming_transfer_size',
    'server_mask',
    'maximum_outgoing_transfer_size',
    'descriptor_capability_field',
    'allocate_address',
    'complex_descriptor_available',
    'is_alternate_pan_coordinator',
    'is_coordinator',
    'is_end_device',
    'is_full_function_device',
    'is_mains_powered',
    'is_receiver_on_when_idle',
    'is_router',
    'is_security_capable',
    'is_valid',
    'logical_type',
    'user_descriptor_available'
])
serialize_object_as_dict(Endpoint, [
    'device_type',
    'status',
    'profile_id',
    'endpoint_id',
    'manufacturer',
    'manufacturer_id',
    'member_of',
    'model',
    'unique_id',
    'in_clusters',
    'out_clusters'
])
