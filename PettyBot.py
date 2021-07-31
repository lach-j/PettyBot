import os
import json
from dotenv import load_dotenv

from lxml import html
import requests

import discord
from discord.ext import commands

from datetime import datetime, timedelta
import random

import asyncio

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
DATE_FORMAT = "%Y/%m/%d, %H:%M:%S"

bot = commands.Bot(command_prefix='!')


@bot.event
async def on_ready():
    print(f"{bot.user.name}#{bot.user.discriminator} is ready")
    print("\n")
    for channel in bot.get_all_channels():
        if type(channel) == discord.channel.TextChannel:
            # if channel.name == "bot-stuff":
            await channel.send("hi")


async def check_schedule() -> None:
    ''' Checks \'resources/schedule.json\' for messages needing to be sent. '''
    await bot.wait_until_ready()
    while not bot.is_closed():
        with open('resources/schedule.json', "rt") as f:
            data = json.load(f)
            f.close()

        if data:
            print(f'({len(data)}) messages are scheduled')
            if datetime.strptime(data[0]["date"], DATE_FORMAT) < datetime.now():
                await run_msg(data[0])
                del(data[0])
                with open('resources/schedule.json', "wt") as f:
                    f.write(json.dumps(data))
                    f.close()

        await asyncio.sleep(1)

bot.loop.create_task(check_schedule())


async def run_msg(job: dict) -> None:
    '''
    Dispatches scheduled messages

    Args:

        job : `dict`
        Job dictionary with keys:

        ``"channel_id"``
            id of channel to be sent to (`int`).
        ``"author"``
            id of the user sending the message (`int`).
        ``"msg"``
            contents of message to be sent (`str`).
    '''
    channel = bot.get_channel(job["channel_id"])
    user = await bot.fetch_user(job["author"])
    await channel.send(user.mention + " " + job["msg"])


def insert_in_order(obj: dict, arr: list) -> list:
    '''
    Insert by date order

    Args:

        obj : `dict`
        Dictionary with containing ``"date"`` key (`datetime`).

        obj : `list`
        List of `obj` objects.
    '''

    if not arr:
        arr = []
    i = 0
    for sch in arr:
        arr_date = datetime.strptime(sch["date"], DATE_FORMAT)
        obj_date = datetime.strptime(obj["date"], DATE_FORMAT)
        if arr_date > obj_date:
            arr.insert(i, obj)
            return arr
        i += 1
    arr.append(obj)
    return arr


@bot.command(name='courseinfo', help='Get information about a UON course')
async def c_info(ctx, *argv):
    if (len(argv) != 1):
        await ctx.send(content="!courseinfo requires one argument")
        return
    code = argv[0].upper()
    url = 'https://www.newcastle.edu.au/course/' + code

    page = requests.get(url)
    dom = html.fromstring(page.content)

    print("Retrieving data from " + url + '...')

    info = dom.xpath(
        '//meta[starts-with(@name, "uon-course")]/@*[name()="name" or name()="content"]')

    requisite = dom.xpath('//h3[@id="requisite"]')

    data = dict()

    if requisite:
        requisite = requisite[0]
        p = requisite.getnext()
        req = ""
        while p.tag == 'p':
            paragraph = p.text
            req = req + paragraph + '\n'
            p = p.getnext()
        data["uon-course-requisites"] = [req]

    while len(info) > 0:
        key = info.pop(0)

        if data.get(key):
            data[key].append(info.pop(0))
        else:
            data[key] = [info.pop(0)]

    print(data)

    if not data.get("uon-course-code"):
        response = f'> The course `{code}` could not be found!'
        await ctx.send(content=response)
        return

    embed = discord.Embed(
        color=3908956,
        title=f'{data["uon-course-name"][0]} - {code}',
        url=url,
        description=data["uon-course-description"][0],
        timestamp=datetime.utcnow()
    )

    # meta tag mapping to titles
    titles = {
        "uon-course-assumed-knowledge": 'Assumed Knowledge',
        "uon-course-availability-location": 'Location',
        "uon-course-availability-term": 'Availability',
        "uon-course-faculty": 'Faculty',
        "uon-course-level": 'Level',
        "uon-course-units": 'Units',
        "uon-course-school": 'School',
        "uon-course-requisites": 'Requisites'
    }

    for key in data:
        if data.get(key) and key in titles:
            if len(data[key][0].strip()) > 0:
                embed.add_field(
                    name=titles[key],
                    value=''.join(str(val)+'\n' for val in data[key]),
                    inline=False
                )
    embed.set_footer(text='Retrieved at ')
    await ctx.send(embed=embed)


@bot.command(name='schedule')
async def schedule(ctx, *argv: str) -> None:
    duration_obj = datetime.strptime(argv[0], '%H:%M:%S')
    timefromnow = datetime.now() + timedelta(
        hours=duration_obj.hour, minutes=duration_obj.minute, seconds=duration_obj.second)

    with open('resources/schedule.json', "rt") as f:
        data = json.load(f)
        f.close()

    obj = {
        "date": timefromnow.strftime(DATE_FORMAT),
        "author": ctx.message.author.id,
        "msg": argv[1],
        "channel_id": ctx.channel.id
        }
    data = insert_in_order(obj, data)
    await ctx.message.delete()
    with open('resources/schedule.json', "wt") as f:
        f.write(json.dumps(data))
        f.close()


@bot.command(name='docs')
async def docs(ctx):
    await ctx.send("https://discordpy.readthedocs.io/en/stable/")


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    with open('resources/movies.json', "rt") as f:
        movies = json.load(f)
        f.close()

    movie = random.choice(movies)
    title = f'{movie["title"]} ({movie["year"]})'
    print(title)
    # Do something

    activityvar = discord.Activity(name=title+' 🍿', type=discord.activity.ActivityType.watching)
    await bot.change_presence(activity=activityvar)
    print("status changed")
    await bot.process_commands(message)


bot.run(TOKEN)
