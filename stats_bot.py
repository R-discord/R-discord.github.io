import discord
import json
import pandas as pd
from datetime import datetime
import asyncio
from collections import defaultdict
import os
# Discord 
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')
ALLOWED_ADMIN_ID = os.getenv('ALLOWED_ADMIN_ID')

class StatBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.user_stats = defaultdict(lambda: {
            'username': '',
            'generations': [],
            'total_uses': 0
        })

    async def setup_hook(self):
        self.bg_task = self.loop.create_task(self.collect_stats())

    async def collect_stats(self):
        await self.wait_until_ready()
        channel = self.get_channel(CHANNEL_ID)

        if not channel:
            print(f"无法找到频道 ID: {CHANNEL_ID}")
            await self.close()
            return

        print(f"开始收集 {channel.name} 频道的数据...")

        try:
            message_count = 0
            async for message in channel.history(limit=None):
                # 检查是否是 Allegro APP 的消息
                if (message.author.bot and
                        hasattr(message, 'interaction') and
                        message.interaction):

                    user = message.interaction.user
                    user_id = str(user.id)
                    prompt_content = ""

                    # 尝试从消息内容或嵌入信息中获取 prompt
                    if message.embeds:
                        for embed in message.embeds:
                            if embed.description:
                                prompt_content = embed.description
                    elif message.content:
                        prompt_content = message.content

                    self.user_stats[user_id]['username'] = user.name
                    self.user_stats[user_id]['generations'].append({
                        'prompt': prompt_content,
                        'timestamp': message.created_at.isoformat(),
                        'message_id': str(message.id)
                    })
                    self.user_stats[user_id]['total_uses'] += 1
                    message_count += 1

                    if message_count % 100 == 0:
                        print(f"已处理 {message_count} 条消息...")

            print("数据收集完成！")

            # 保存为JSON
            with open('stats.json', 'w', encoding='utf-8') as f:
                json.dump(self.user_stats, f, ensure_ascii=False, indent=2)

            # 生成Excel报告
            excel_data = []
            for user_id, stats in self.user_stats.items():
                for gen in stats['generations']:
                    excel_data.append({
                        'Username': stats['username'],
                        'User ID': user_id,
                        'Prompt': gen['prompt'],
                        'Timestamp': gen['timestamp'],
                        'Message ID': gen['message_id']
                    })

            df = pd.DataFrame(excel_data)
            df.to_excel('allegro_stats.xlsx', index=False)

            print("统计数据已保存到 stats.json 和 allegro_stats.xlsx")

            # 生成简单的统计摘要
            print("\n使用统计摘要:")
            print(f"总用户数: {len(self.user_stats)}")
            print(f"总生成次数: {message_count}")
            print("\n每个用户的使用次数:")
            for user_id, stats in self.user_stats.items():
                print(f"{stats['username']}: {stats['total_uses']} 次")

            await self.close()

        except Exception as e:
            print(f"发生错误: {e}")
            await self.close()

    async def on_ready(self):
        print(f'Bot已登录为 {self.user.name}')


client = StatBot()
client.run(TOKEN)
