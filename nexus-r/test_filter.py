import httpx
import asyncio

async def test():
    async with httpx.AsyncClient() as c:
        res = await c.get('https://openrouter.ai/api/v1/models')
        data = res.json().get('data', [])
        for item in data:
            pricing = item.get('pricing', {})
            try:
                p = float(pricing.get('prompt') or 0)
                c_ = float(pricing.get('completion') or 0)
            except:
                p = -1
                c_ = -1
            if p == 0.0 and c_ == 0.0:
                print(f"FREE MODEL: {item['id']}")
                return

asyncio.run(test())
