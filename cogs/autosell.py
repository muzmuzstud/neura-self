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

import discord
from discord.ext import commands
import time
import asyncio
import core.state as state

class AutoSell(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_sell_time = 0
        self.is_selling = False
        self.loop = asyncio.create_task(self.run_loop())

    async def run_loop(self):
        await self.bot.wait_until_ready()
        while True:
            cfg = self.bot.config.get('commands', {}).get('autosell', {})
            if not self.bot.paused and cfg.get('enabled', False):
                now = time.time()
                cooldown = cfg.get('cooldown', 1200)
                
                if now - self.last_sell_time > cooldown:
                    sell_type = cfg.get('type', 'all')
                    await self.bot.neura_enqueue(f"sell {sell_type}", priority=2)
                    self.last_sell_time = now
                    self.bot.log("SYS", f"Periodic AutoSell triggered ({sell_type}).")
                
                elif now % 600 < 60: 
                    current_cash = state.account_stats.get(self.bot.user_id, {}).get('current_cash')
                    if current_cash is None:
                        await self.bot.neura_enqueue("cash", priority=1)
                    else:
                        min_cash = cfg.get('min_cash_trigger', 0)
                        if current_cash < min_cash and now - self.last_sell_time > 300:
                            sell_type = cfg.get('type', 'all')
                            await self.bot.neura_enqueue(f"sell {sell_type}", priority=2)
                            self.last_sell_time = now
                            self.bot.log("SYS", f"Low funds emergency! Triggered AutoSell ({sell_type}).")

            await asyncio.sleep(60)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id != int(self.bot.owo_bot_id): return
        if self.bot.owo_user is None:
            self.bot.owo_user = message.author
        if message.channel.id != self.bot.channel_id: return
        content = message.content.lower()
        
        if "sold" in content and "for a total of" in content:
            if not self.bot.is_message_for_me(message): return
            self.bot.log("SUCCESS", f"AutoSell confirmed: {message.content.split('sold')[-1].strip()}")
            self.last_sell_time = time.time()
            await self.bot.neura_enqueue("cash", priority=1)
            return

        if not self.bot.is_message_for_me(message, role="header"): return
        cfg = self.bot.config.get('commands', {}).get('autosell', {})
        if not cfg.get('enabled', False): return
        
        if "don't have enough cowoncy" in content or "not enough cowoncy" in content:
            if time.time() - self.last_sell_time > 300:
                self.is_selling = True
                await self.bot.neura_enqueue(f"sell {cfg.get('type', 'all')}", priority=2)
                self.last_sell_time = time.time()
                self.bot.log("SYS", "Low funds detected. Triggered AutoSell.")

async def setup(bot):
    await bot.add_cog(AutoSell(bot))