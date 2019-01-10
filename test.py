import logging, sys, asyncio, pprint

import pyblueiris as BI

from test_config import USER, PASS, PROTOCOL, HOST
from aiohttp import ClientSession

logging.basicConfig(
    level=logging.DEBUG,
    format='[%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

MY_LOGGER = logging.getLogger(__name__)


async def tests():
    async with ClientSession(raise_for_status=True) as sess:
        blue = BI.BlueIris(sess, USER, PASS, PROTOCOL, HOST, debug=True, logger=MY_LOGGER)
        await blue.async_setup_session()
        await blue.async_update_status()
        await blue.async_update_camlist()

        pprint.pprint(blue.attributes)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(tests())
