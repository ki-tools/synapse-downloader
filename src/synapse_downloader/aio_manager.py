import asyncio
import aiohttp


class AioManager:
    AIOSESSION = None

    @classmethod
    def start(cls, func, **kwargs):
        asyncio.run(cls._start_async(func, **kwargs))

    @classmethod
    async def _start_async(cls, func, **kwargs):
        try:
            cls.AIOSESSION = aiohttp.ClientSession(raise_for_status=True)
            await func(**kwargs)
        finally:
            if cls.AIOSESSION:
                await cls.AIOSESSION.close()
