# This file is part of NeuraSelf-UwU.
# Copyright (c) 2025-Present Routo
#
# NeuraSelf-UwU is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# You should have received a copy of the GNU General Public License
# along with NeuraSelf-UwU. If not, see <https://www.gnu.org/licenses/>.

import asyncio
import time
import random
import aiohttp
import core.state as state
from discord.ext import commands

class LevelQuotes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active = True
        self.quote_cache = []
        self.task = None
        
        pass

    async def fetch_quote(self):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://favqs.com/api/qotd", timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        quote_obj = data.get('quote', {})
                        return quote_obj.get('body', '')
        except:
            pass
        return None

    async def get_quote(self, min_len, max_len):
        for quote in self.quote_cache:
            if min_len <= len(quote) <= max_len:
                self.quote_cache.remove(quote)
                return quote
        
        for _ in range(5):
            quote = await self.fetch_quote()
            if quote and min_len <= len(quote) <= max_len:
                return quote
            elif quote:
                self.quote_cache.append(quote)
        
        return "owo " * random.randint(3, 8)

    async def trigger_action_async(self):
        cfg = self.bot.config.get('automation', {}).get('level_grind', {})
        use_quotes = cfg.get('use_quotes', True)
        min_len = cfg.get('min_length', 10)
        max_len = cfg.get('max_length', 50)
        
        if use_quotes:
            message = await self.get_quote(min_len, max_len)
            self.bot.stats['level_quotes_sent'] = self.bot.stats.get('level_quotes_sent', 0) + 1
        else:
            message = "owo " * random.randint(2, 5)
            self.bot.stats['level_quotes_sent'] = self.bot.stats.get('level_quotes_sent', 0) + 1
            
        return message, random.uniform(40, 80)

    def trigger_action(self):
        async def fetch_and_set():
            msg, delay = await self.trigger_action_async()
            self.bot.cmd_states['level_quotes']['content'] = msg
            self.bot.cmd_states['level_quotes']['delay'] = delay
            
        asyncio.create_task(fetch_and_set())

async def setup(bot):
    cog = LevelQuotes(bot)
    await bot.add_cog(cog)
    
    cfg = bot.config.get('automation', {}).get('level_grind', {})
    if cfg.get('enabled', False):
        bot.log("SYS", "Level Quotes module configured.")
        await bot.neura_register_command("level_quotes", "owo level", priority=4, delay=random.uniform(40, 80), initial_offset=20)
        
        cog.trigger_action()