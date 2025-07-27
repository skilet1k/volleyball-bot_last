#!/usr/bin/env python3
"""
Тест скрипт для проверки endpoints бота
"""
import asyncio
import aiohttp
import json
from datetime import datetime

async def test_endpoints():
    """Тестирует все endpoints бота"""
    base_url = "http://localhost:8000"  # Для локального тестирования
    # Для продакшена замените на: https://volleyball-bot-last.onrender.com
    
    endpoints = [
        "/",
        "/health", 
        "/status",
        "/ping",
        "/monitor"
    ]
    
    async with aiohttp.ClientSession() as session:
        print(f"Тестирование endpoints на {base_url}")
        print("=" * 50)
        
        for endpoint in endpoints:
            url = f"{base_url}{endpoint}"
            try:
                async with session.get(url, timeout=10) as response:
                    content = await response.text()
                    print(f"✅ {endpoint}: {response.status}")
                    
                    # Особая обработка JSON endpoints
                    if endpoint in ["/status"]:
                        try:
                            data = json.loads(content)
                            print(f"   📋 JSON: {data}")
                        except:
                            print(f"   📄 Text: {content[:100]}...")
                    else:
                        print(f"   📄 Content: {len(content)} chars")
                        
            except Exception as e:
                print(f"❌ {endpoint}: ERROR - {e}")
            
            print()

if __name__ == "__main__":
    print("🤖 Volleyball Bot - Endpoint Tester")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    asyncio.run(test_endpoints())
