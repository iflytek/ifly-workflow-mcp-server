from . import server
import asyncio


def main():
    asyncio.run(server.main())


__all__ = ['main', 'server']
