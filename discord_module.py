import discord
import play
import asyncio
client = discord.Client()

KEY_PATH = 'key.txt'
CHANNEL_ID = None
SELF_ID = 376874563847454740 # stored so the bot doesn't read its own messages
GAME_CHANNEL = 656007036315631627
INPUT_GIVEN = False
INPUT_TEXT = ''
output_buffer = ''

def add_to_output(txt):
    global output_buffer
    output_buffer += '\n' + txt
    
async def send_output():
    output_buffer = ''
    await send_msg(output_buffer)
    output_buffer = ''
    

async def send_msg(msg_text):
    await GAME_CHANNEL.send(msg_text)

@client.event
async def on_ready():
    global GAME_CHANNEL
    GAME_CHANNEL = discord.utils.get(client.get_all_channels(), id=CHANNEL_ID)
    print('Online.')
    asyncio.ensure_future(play.play_aidungeon_2())


@client.event
async def on_message(message: discord.Message):
    global INPUT_GIVEN
    global INPUT_TEXT
    if message.author.id == SELF_ID:
        return
    if message.channel != GAME_CHANNEL:
        return
    # If no input is being processed, write the current input. Later,
    # The bot can read from INPUT_TEXT to replicate input() statements
    if not INPUT_GIVEN:
        INPUT_GIVEN = True
        INPUT_TEXT = message.content()

async def get_input(prompt=None):
    """Reads from INPUT_TEXT. Will wait until new input is given if none have."""
    """Sleep counter will increase the delay after 100 seconds to save memory"""
    if prompt is not None:
        add_to_output(prompt)
        await send_output()
    global INPUT_GIVEN
    global INPUT_TEXT
    sleep_counter = 0
    if INPUT_GIVEN:
        INPUT_GIVEN = False
        return INPUT_TEXT
    else:
        if sleep_counter < 100:
            asyncio.sleep(1)
            sleep_counter += 1
        else:
            asyncio.sleep(5)
            
async def start():
    with open(KEY_PATH, 'r') as f:
        key = f.read()
    client.run(key)