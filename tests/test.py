RAPIDGATOR_TEST_LINK = "https://rapidgator.net/file/d71e1b914795643965155fed0bac8b19/Penetration.Testing.and.Ethical.Hacking.02.19.part5.rar.html"

from darkloader.darkloader import DarkLoader
import asyncio

async def main():
    darkloader = DarkLoader()
    await darkloader.download_url(RAPIDGATOR_TEST_LINK)


if __name__ == "__main__":
    asyncio.run(main())

