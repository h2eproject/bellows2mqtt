import sys
import argparse
import logging
import asyncio
import signal

from bellows2mqtt.BellowsToMQTT import BellowsToMQTT
from bellows2mqtt.util import print_error, exit_process

LOGGER = logging.getLogger(__name__)


async def amain():
    try:
        parser = argparse.ArgumentParser(description='Bridge Zigbee to MQTT')
        parser.add_argument('-u', '--mqtt-uri', type=str, help='A connection URI for the MQTT broker',
                            default='mqtt://localhost', dest='mqtt_uri')
        parser.add_argument('-d', '--device', type=str,
                            help='The path to the Zigbee dongle\'s serial device', default='/dev/ttyUSB1')
        parser.add_argument('-s', '--db-path', type=str,
                            help='The path to the Zigbee database', default='zigbee.db', dest='db_path')
        parser.add_argument('-l', '--log-level', type=str,
                            help='Logging level', default='WARN', dest='log')
        args = parser.parse_args()
        numeric_level = getattr(logging, args.log.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError('Invalid log level: %s' % args.log)
        logging.basicConfig(level=numeric_level)
        LOGGER.info('MQTT broker: %s', args.mqtt_uri)
        LOGGER.info('Zigbee device: %s', args.device)
        async with BellowsToMQTT(args.mqtt_uri, args.device, args.db_path) as b2m:
            await b2m.connect()
    except KeyboardInterrupt:
        exit_process()
    except Exception as e:
        LOGGER.error('Uncaught exception: %s', e)
        print_error(e)
        exit_process()


def main():
    asyncio.run(amain())


if __name__ == "__main__":
    main()
