import sys
from contextlib import AsyncExitStack
import asyncio
import logging
import json
from urllib.parse import urlparse
import time

import asyncio_mqtt as mqtt

from bellows.zigbee.application import ControllerApplication
from zigpy.device import Device
from zigpy.endpoint import Endpoint
from zigpy.config import CONF_DEVICE, CONF_DEVICE_PATH, CONF_DATABASE

from bellows2mqtt.util import print_error, exit_process, select_keys

LOGGER = logging.getLogger(__name__)


class BellowsToMQTT(AsyncExitStack):
    def __init__(self, mqtt_uri="mqtt://localhost", zigbee_device="/dev/ttyUSB1", db_path="zigbee.db"):
        AsyncExitStack.__init__(self)
        LOGGER.debug(
            'Creating BellowsToMQTT instance (mqtt_uri=%s, zigbee_device=%s)', mqtt_uri, zigbee_device)
        self.mqtt_uri = mqtt_uri
        self.zigbee_device = zigbee_device
        self.db_path = db_path
        self.tasks = set()

    async def __aexit__(self, *args):
        await asyncio.gather(*self.tasks)
        self.tasks = set()
        return await AsyncExitStack.__aexit__(self, *args)

    async def connect(self):
        mqtt_uri_parsed = urlparse(self.mqtt_uri)
        assert mqtt_uri_parsed.scheme == 'mqtt'
        port = mqtt_uri_parsed.port or 1883
        LOGGER.info('Connecting to MQTT (host=%s, port=%s, username=%s, password=%s)',
                    mqtt_uri_parsed.hostname, port, mqtt_uri_parsed.username, mqtt_uri_parsed.password)
        self.mq_client = mq = mqtt.Client(hostname=mqtt_uri_parsed.hostname, port=port,
                                          username=mqtt_uri_parsed.username, password=mqtt_uri_parsed.password)
        LOGGER.debug('Entering MQTT async context')
        await self.enter_async_context(mq)

        LOGGER.debug('Subscribing to MQTT topics')
        msg_manager = mq.filtered_messages('zigbee/#')
        messages = await self.enter_async_context(msg_manager)
        task = asyncio.create_task(self.handle_mq_messages(messages))
        self.tasks.add(task)

        await mq.subscribe('zigbee/#')

        LOGGER.info('Starting Zigbee (device=%s, db=%s)',
                    self.zigbee_device, self.db_path)
        self.application = app = await ControllerApplication.new(ControllerApplication.SCHEMA({
            CONF_DATABASE: self.db_path,
            CONF_DEVICE: {
                CONF_DEVICE_PATH: self.zigbee_device
            }
        }), auto_form=True, start_radio=False)
        LOGGER.debug('Adding Zigbee listener')
        self.application.add_listener(self)
        LOGGER.debug('Starting Zigbee')
        await app.startup(False)
        LOGGER.info('Zigbee started')
        await self.pub_defaults()
        await asyncio.get_running_loop().create_future()
    
    async def pub_defaults(self):
        await self.publish('zigbee/devices', self.application.devices.values())
        await self.publish('zigbee/permitting', { 'status': False })

    async def handle_mq_messages(self, messages):
        try:
            async for message in messages:
                await self.handle_mq_message(message)
        except KeyboardInterrupt:
            exit_process()
        except Exception as e:
            LOGGER.error('Error in message queue: %s', e)
            print_error(e)
        finally:
            LOGGER.warn('Message loop ended; quitting')
            exit_process()
                
    
    async def handle_mq_message(self, message):
        try:
            topic = message.topic
            try:
                payload = json.loads(message.payload)
            except json.decoder.JSONDecodeError:
                LOGGER.error('[sub %s]: payload %s is not valid JSON', topic, message.payload)
                return
            LOGGER.info('[sub %s]: %s', topic, payload)
            handler = self.default_message_handler
            if topic == "zigbee/permit":
                handler = self.handle_permit_message
            self.tasks.add(asyncio.create_task(handler(payload)))
        except KeyboardInterrupt:
            exit_process()
        except Exception as e:
            LOGGER.error('[sub %s]: Error processing message: %s', message.topic, e)
            print_error(e)

    async def default_message_handler(self, payload):
        pass
    
    async def handle_permit_message(self, payload):
        duration = 60
        if isinstance(payload, int):
            duration = payload

        LOGGER.info('Permitting devices to join for %d seconds', duration)
        await self.publish('zigbee/permitting', {
            "status": True,
            "until": time.time() + duration
        })
        await self.application.permit(duration)
        await asyncio.sleep(duration)
        await self.publish('zigbee/permitting', {
            "status": False
        })
        LOGGER.info('No longer permitting devices to join')

    async def publish(self, topic, message):
        json_msg = json.dumps(message)
        LOGGER.info("[pub %s]: %s", topic, json_msg)
        await self.mq_client.publish(topic, json_msg, qos=1, retain=True)

    def device_joined(self, device: Device):
        if not device.initializing:
            device.schedule_initialize()
        asyncio.create_task(self.device_joined_pub(device))

    async def device_joined_pub(self, device):
        await self.publish('zigbee/device-joined', {
            "device": device
        })

    def device_initialized(self, device: Device):
        asyncio.create_task(self.device_initialized_pub(device))

    async def device_initialized_pub(self, device):
        await self.publish('zigbee/device-initialized', {
            "device": device
        })
        await self.publish('zigbee/devices', self.application.devices.values())

    def device_left(self, device):
        asyncio.create_task(self.device_left_pub(device))
    
    async def device_left_pub(self, device):
        await self.publish('zigbee/device-left', {
            "device": device
        })
        await self.publish('zigbee/devices', self.application.devices.values())

    def attribute_updated(self, device, cluster, attribute_id, value):
        asyncio.create_task(self.attribute_updated_pub(
            device, cluster, attribute_id, value))

    async def attribute_updated_pub(self, device, cluster, attribute_id, value):
        await self.publish('zigbee/attribute-updated', {
            "device": device,
            "cluster": cluster,
            "attribute_id": attribute_id,
            "value": value
        })
