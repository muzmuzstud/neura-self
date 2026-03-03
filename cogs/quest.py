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
import re
import time
import core.state as state

class Quest:
    def __init__(self, bot):
        self.bot = bot
        self.active = True
        self.task = None

    def trigger_action(self):
        cfg = self.bot.config.get('commands', {}).get('quest', {})
        ih = cfg.get('interval_h', 6)
        
        self.bot.cmd_states['quest']['delay'] = ih * 3600

    async def on_message(self, message):
        core_config = self.bot.config.get('core', {})
        monitor_id = str(core_config.get('monitor_bot_id', '408785106942164992'))
        
        if str(message.author.id) != monitor_id:
            return
        if self.bot.owo_user is None:
            self.bot.owo_user = message.author
        if message.channel.id != self.bot.channel_id:
            return

        full_text = self.bot.get_full_content(message)

        if "quest log" in full_text or "checklist" in full_text:
            is_for_me = self.bot.is_message_for_me(message, role="header")
            
            if not is_for_me:
                return
            
            self._parse_quests(full_text)

    def _parse_quests(self, text):
        progress_pattern = r'progress:\s*\[(\d+)/(\d+)\]'
        timer_pattern = r'next quest in:\s*(\d+h \d+m \d+s)'
        
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        new_quest_data = []
        
        st = self.bot.stats
        old_quests = st.get('quest_data', [])
        
        sync_count = 0

        for i, line in enumerate(lines):
            match = re.search(progress_pattern, line)
            if match:
                current = int(match.group(1))
                total = int(match.group(2))
                
                desc = "Unknown Quest"
                for j in range(i-1, max(-1, i-4), -1):

                    raw_line = lines[j]

                    if any(x in raw_line.lower() for x in ["progress:", "quest log", "belong to", "next quest"]):
                        continue
                    desc_part = raw_line
                    if "reward:" in raw_line.lower():
                        parts = re.split(r'reward:', raw_line, flags=re.IGNORECASE)
                        desc_part = parts[0]

                    clean_desc = desc_part.replace(':blank:', '').replace('‣', '').replace('*', '').strip()
                    clean_desc = re.sub(r'^\d+[\)\.]\s*', '', clean_desc) 
                    clean_desc = re.sub(r'<[^>]*>', '', clean_desc)
                    clean_desc = clean_desc.replace('`', '').strip() 
                    
                    if clean_desc and len(clean_desc) > 3:
                        desc = clean_desc
                        break
                
                quest_item = {
                    'description': desc,
                    'current': current,
                    'total': total,
                    'completed': current >= total
                }
                new_quest_data.append(quest_item)
                
                if quest_item['completed']:
                    was_completed = any(q['description'] == desc and q.get('completed') for q in old_quests)
                    if not was_completed:
                        self.bot.log("SUCCESS", f"QUEST COMPLETED: {desc}")

        timer_match = re.search(timer_pattern, text)
        next_timer = timer_match.group(1).upper() if timer_match else None
        
        st['quest_data'] = new_quest_data
        st['next_quest_timer'] = next_timer
        
        if new_quest_data:
            self.bot.log("SYS", f"Dashboard synced: {len(new_quest_data)} quests tracked.")
            if any(q['description'] == "Unknown Quest" for q in new_quest_data):
                self.bot.log("DEBUG", "Some quests could not be named. Structure might be unusual.")
        elif "quest log" in text:
            self.bot.log("DEBUG", "Regex failure: Found 'Quest Log' but couldn't parse progress lines.")

async def setup(bot):
    cog = Quest(bot)
    bot.add_listener(cog.on_message, 'on_message')
    
    cfg = bot.config.get('commands', {}).get('quest', {})
    if cfg.get('enabled', True):
        bot.log("SYS", "Quest Module configured.")
        ih = cfg.get('interval_h', 6)
        await bot.neura_register_command("quest", "quest", priority=4, delay=ih * 3600, initial_offset=10)

        old_execute = cog.trigger_action
        old_execute()
        
        async def quest_dispatch(content):
            cog.trigger_action()