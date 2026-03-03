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
import aiohttp
import time
import json
import re

class WebSolver:
    def __init__(self, bot):
        self.bot = bot
        cfg = self.bot.config.get('security', {}).get('captcha_solver', {})
        self.api_key = cfg.get('api_key', '')
        self.enabled = cfg.get('enabled', True)
        self.site_key = "a6a1d5ce-612d-472d-8e37-7601408fbc09"
        self.auth_url = "https://discord.com/api/v9/oauth2/authorize?client_id=408785106942164992&response_type=code&redirect_uri=https://owobot.com/api/auth/discord/redirect&scope=identify guilds"

    async def get_balance(self):
        if not self.api_key: return 0
        url = "https://api.yescaptcha.com/getBalance"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json={"clientKey": self.api_key}, timeout=10) as resp:
                    data = await resp.json()
                    return int(data.get("balance", 0)) if data.get("errorId") == 0 else 0
        except: return 0

    async def solve_hcaptcha(self, retries=3):
        """solves hcaptcha using yescaptcha api and returns the token"""
        create_url = "https://api.yescaptcha.com/createTask"
        result_url = "https://api.yescaptcha.com/getTaskResult"
        
        payload = {
            "clientKey": self.api_key,
            "task": {
                "type": "HCaptchaTaskProxyless",
                "websiteKey": self.site_key,
                "websiteURL": "https://owobot.com",
            },
            "softID": 94493,
        }

        async with aiohttp.ClientSession() as session:
            for attempt in range(retries):
                try:
                    self.bot.log("SYS", f"Creating YesCaptcha task (Attempt {attempt+1})...")
                    async with session.post(create_url, json=payload) as resp:
                        data = await resp.json()
                    
                    if data.get("errorId") != 0:
                        self.bot.log("ERROR", f"YesCaptcha Error: {data.get('errorDescription')}")
                        continue

                    task_id = data.get("taskId")
                    for _ in range(30): 
                        await asyncio.sleep(3)
                        async with session.post(result_url, json={"clientKey": self.api_key, "taskId": task_id}) as res_resp:
                            res = await res_resp.json()
                        
                        if res.get("status") == "ready":
                            return res["solution"]["gRecaptchaResponse"]
                        if res.get("errorId") != 0: break
                except Exception as e:
                    self.bot.log("ERROR", f"Solver task failed: {e}")
            return None

    async def auto_verify(self, tries=3):
        if not self.api_key:
            self.bot.log("ERROR", "YesCaptcha API key missing in settings.")
            return False

        balance = await self.get_balance()
        if balance < 30:
            self.bot.log("ERROR", f"YesCaptcha balance too low: {balance}")
            return False

        headers = {
            "Authorization": self.bot.token,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x44) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            try:
                auth_payload = {
                    "authorize": True,
                    "permissions": "0",
                    "integration_type": 0,
                    "location_context": {"guild_id": "10000", "channel_id": "10000", "channel_type": 10000}
                }
                async with session.post(self.auth_url, json=auth_payload) as resp:
                    if resp.status != 200: return False
                    auth_data = await resp.json()
                    redirect_url = auth_data.get("location")

                if redirect_url:
                    async with session.get(redirect_url) as r: pass


                solution = await self.solve_hcaptcha(tries)
                if not solution: return False

                verify_url = "https://owobot.com/api/captcha/verify"
                verify_payload = {"token": solution}
                async with session.post(verify_url, json=verify_payload, headers={"Referer": "https://owobot.com/captcha", "Origin": "https://owobot.com"}) as v_resp:
                    return v_resp.status == 200
            except Exception as e:
                self.bot.log("ERROR", f"Auto-verification failed: {e}")
                return False

def setup_web_solver(bot):
    return WebSolver(bot)
