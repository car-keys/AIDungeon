#!/usr/bin/env python3
import os
import sys
import time
import discord_module as dm

from generator.gpt2.gpt2_generator import *
from story import grammars
from story.story_manager import *
from story.utils import *
from playsound import playsound


os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

async def get_num_options(num):
    while True:
        choice = input("Enter the number of your choice.")
        try:
            result = int(choice)
            if result >= 0 and result < num:
                return result
            else:
                await dm.send_msg("Error invalid choice.")
        except ValueError:
            await dm.send_msg("Error invalid choice. ")

async def splash():
    dm.add_to_output("0) New Game\n1) Load Game\n")
    await dm.send_output()
    choice = await get_num_options(2)

    if choice == 1:
        return "load"
    else:
        return "new"


async def select_game():
    with open(YAML_FILE, "r") as stream:
        data = yaml.safe_load(stream)

    dm.add_to_output("Pick a setting.")
    settings = data["settings"].keys()
    for i, setting in enumerate(settings):
        print_str = str(i) + ") " + setting
        if setting == "fantasy":
            print_str += " (recommended)"

        await dm.send_msg(print_str)
    dm.add_to_output(str(len(settings)) + ") custom")
    choice = await get_num_options(len(settings) + 1)

    if choice == len(settings):

        context = ""
        await dm.send_msg(
            "\nEnter a prompt that describes who you are and what are your goals.\nThe AI will " +
            "always remember this prompt and will use it for context.\nEX: 'Your name is John Doe. You are a knight in " +
            "the kingdom of Larion. You were sent by the king to track down and slay an evil dragon.'"
        )
        context = await get_input()
        if len(context) > 0 and not context.endswith(" "):
            context = context + " "

        await dm.send_msg(
            "\nNow enter a prompt that describes the start of your story. This will give the AI " +
            "a starting point (The AI will eventually forget this prompt).\nEX: '" +
            "You are hunting the evil dragon who has been " + 
            "terrorizing the kingdom. You enter the forest searching for the dragon and see' "
        )
        prompt = await get_input("Starting Prompt:")
        return context, prompt

    setting_key = list(settings)[choice]

    dm.add_to_output("\nPick a character")
    characters = data["settings"][setting_key]["characters"]
    for i, character in enumerate(characters):
        dm.add_to_output(str(i) + ") " + character)
    character_key = list(characters)[await get_num_options(len(characters))]

    name = await get_input("What is your name?")
    setting_description = data["settings"][setting_key]["description"]
    character = data["settings"][setting_key]["characters"][character_key]

    name_token = "<NAME>"
    if character_key == "noble" or character_key == "knight":
        context = grammars.generate(setting_key, character_key, "context") + "\n\n"
        context = context.replace(name_token, name)
        prompt = grammars.generate(setting_key, character_key, "prompt")
        prompt = prompt.replace(name_token, name)
    else:
        context = (
            "You are "
            + name
            + ", a "
            + character_key
            + " "
            + setting_description
            + "You have a "
            + character["item1"]
            + " and a "
            + character["item2"]
            + ". "
        )
        prompt_num = np.random.randint(0, len(character["prompts"]))
        prompt = character["prompts"][prompt_num]

    return context, prompt


def instructions():
    text = "\nAI Dungeon 2 Instructions:"
    text += '\n Enter actions starting with a verb ex. "go to the tavern" or "attack the orc"'
    text += '\n'
    text += '\n To speak enter \'say "(thing you want to say)"\''
    text += '\n or just "(thing you want to say)"'
    text += '\n'
    text += '\n If you want something to happen or be done by someone else, enter '
    text += '\n \'!(thing you want to happen)'
    text += '\n ex. "!A dragon swoops down and eats Sir Theo."'
    text += '\n'
    text += "\nThe following commands can be entered for any action: "
    text += '\n  "/revert"         Reverts the last action allowing you to pick a different action.'
    text += '\n  "/retry"          Reverts the last action and tries again with the same action.'
    text += '\n  "/quit"           Quits the game and saves'
    text += '\n  "/restart"        Starts a new game and saves your current one'
    text += '\n  "/cloud"          Turns on cloud saving when you use the "save" command'
    text += '\n  "/save"           Makes a new save of your game and gives you the save ID'
    text += '\n  "/load"           Asks for a save ID and loads the game if the ID is valid'
    text += '\n  "/print"          Prints a transcript of your adventure'
    text += '\n  "/help"           Prints these instructions again'
    text += '\n  "/showstats"      Prints the current game settings'
    text += '\n  "/censor off/on"  Turn censoring off or on.'
    text += '\n  "/ping off/on"    Turn playing a ping sound when the AI responds off or on.'
    text += '\n                   (not compatible with Colab)'
    text += '\n  "/infto ##"       Set a timeout for the AI to respond.'
    text += '\n  "/temp #.#"       Changes the AI\'s temperature'
    text += '\n                   (higher temperature = less focused). Default is 0.4.'
    text += '\n  "/topk ##"        Changes the AI\'s top_k'
    text += '\n                   (higher top_k = bigger memorized vocabulary). Default is 80.'
    text += '\n  "/remember XXX"   Commit something important to the AI\'s memory for that session.'
    return text


async def play_aidungeon_2():

    #console_print(
    #    "AI Dungeon 2 will save and use your actions and game to continually improve AI Dungeon."
    #    + " If you would like to disable this enter '/nosaving' as an action. This will also turn off the "
    #    + "ability to save games."
    #)

    upload_story = True
    ping = False

    dm.add_to_output("\nInitializing AI Dungeon! (This might take a few minutes)\n")
    await dm.send_output()
    generator = GPT2Generator()
    story_manager = UnconstrainedStoryManager(generator)

    with open("opening.txt", "r", encoding="utf-8") as file:
        starter = file.read()
    dm.add_to_output(starter)
    while True:
        if story_manager.story != None:
            del story_manager.story

        while story_manager.story is None: 
            splash_choice = await splash()

            if splash_choice == "new":
                context, prompt = await select_game()
                change_config = await get_input("Would you like to enter a new temp and top_k now? (default: 0.4, 80) (y/N)")
                if change_config.lower() == "y":
                    story_manager.generator.change_temp(float(await get_input("Enter a new temp (default 0.4)") or 0.4))
                    story_manager.generator.change_topk(int(await get_input("Enter a new top_k (default 80)") or 80))
                    dm.add_to_output("Please wait while the AI model is regenerated...")
                    await dm.send_output()
                    story_manager.generator.gen_output()
                await dm.send_msg(instructions() + "\n\nGenerating story...")
                story_manager.generator.generate_num = 120
                story_manager.start_new_story(
                    prompt, context=context, upload_story=upload_story
                )
                await dm.send_msg(str(story_manager.story))
                story_manager.generator.generate_num = story_manager.generator.default_gen_num

            else:
                load_ID = await get_input("What is the ID of the saved game? (prefix with gs:// if it is a cloud save)")
                if load_ID.startswith("gs://"):
                    result = story_manager.load_new_story(load_ID[5:], True)
                    story_manager.story.cloud = True
                else:
                    result = story_manager.load_new_story(load_ID)
                dm.add_to_output("\nLoading Game...\n")
                dm.add_to_output(result)
                await dm.send_output()

        while True:
            sys.stdin.flush()
            action = await get_input().strip()
            if len(action) > 0 and action[0] == "/":
                split = action[1:].split(" ") # removes preceding slash
                command = split[0].lower()
                args = split[1:]
                if command == "restart":
                    rating = await get_input("Please rate the story quality from 1-10: ")
                    rating_float = float(rating)
                    story_manager.story.rating = rating_float
                    break

                elif command == "quit":
                    rating = await get_input("Please rate the story quality from 1-10: ")
                    rating_float = float(rating)
                    story_manager.story.rating = rating_float
                    exit()

                elif command == "nosaving":
                    upload_story = False
                    story_manager.story.upload_story = False
                    await dm.send_msg("Saving turned off.")

                elif command == "cloud":
                    story_manager.story.cloud = True
                    await dm.send_msg("Cloud saving turned on.")

                elif command == "help":
                    await dm.send_msg(instructions())

                elif command == "showstats":
                    text =    "nosaving is set to:    " + str(not upload_story) 
                    text += "\nping is set to:        " + str(ping) 
                    text += "\ncensor is set to:      " + str(generator.censor) 
                    text += "\ntemperature is set to: " + str(story_manager.generator.temp) 
                    text += "\ntop_k is set to:       " + str(story_manager.generator.top_k) 
                    await dm.send_msg(text) 

                elif command == "censor":
                    if args[0] == "off":
                        if not generator.censor:
                            await dm.send_msg("Censor is already disabled.")
                        else:
                            generator.censor = False
                            await dm.send_msg("Censor is now disabled.")

                    elif args[0] == "on":
                        if generator.censor:
                            await dm.send_msg("Censor is already enabled.")
                        else:
                            generator.censor = True
                            await dm.send_msg("Censor is now enabled.")
                    else:
                        await dm.send_msg(f"Invalid argument: {args[0]}")
                               
                elif command == "ping":
                    if args[0] == "off":
                        if not ping:
                            await dm.send_msg("Ping is already disabled.")
                        else:
                            ping = False
                            await dm.send_msg("Ping is now disabled.")

                    elif args[0] == "on":
                        if ping:
                            await dm.send_msg("Ping is already enabled.")
                        else:
                            ping = True
                            await dm.send_msg("Ping is now enabled.")
                    else:
                        await dm.send_msg(f"Invalid argument: {args[0]}")

                elif command == "load":
                    if len(args) == 0:
                        load_ID = await get_input("What is the ID of the saved game? (prefix with gs:// if it is a cloud save) ")
                    else:
                        load_ID = args[0]
                    if load_ID.startswith("gs://"):
                        story_manager.story.cloud = True
                        result = story_manager.story.load_from_storage(load_ID[5:])
                    else:
                        result = story_manager.story.load_from_storage(load_ID)
                    await dm.send_msg("\nLoading Game...\n\n" + result)

                elif command == "save":
                    if upload_story:
                        id = story_manager.story.save_to_storage()
                        await dm.send_msg(f"Game saved.\nTo load the game, type 'load' and enter the following ID: {id}")
                    else:
                        await dm.send_msg("Saving has been turned off. Cannot save.")

                elif command == "load":
                    if len(args) == 0:
                        load_ID = await get_input("What is the ID of the saved game?")
                    else:
                        load_ID = args[0]
                    result = story_manager.story.load_from_storage(load_ID)
                    await dm.send_msg("\nLoading Game...\n" + result)

                elif command == "print":
                    line_break = await get_input("Format output with extra newline? (y/n)\n> ") 
                    if line_break == "y": 
                        await dm.send_msg(str(story_manager.story)) 
                    else: 
                        await dm.send_msg(str(story_manager.story)) 

                elif command == "revert":
                    if len(story_manager.story.actions) is 0:
                        await dm.send_msg("You can't go back any farther. ")
                        continue

                    story_manager.story.actions = story_manager.story.actions[:-1]
                    story_manager.story.results = story_manager.story.results[:-1]
                    dm.add_to_output("Last action reverted. ")
                    if len(story_manager.story.results) > 0:
                        dm.add_to_output(story_manager.story.results[-1])
                    else:
                        dm.add_to_output(story_manager.story.story_start)
                    await dm.send_output()
                    continue
                
                elif command == "infto":

                    if len(args) != 1:
                        await dm.send_msg("Failed to set timeout. Example usage: infto 30")
                    else:
                        try:
                            story_manager.inference_timeout = int(args[0])
                            await dm.send_msg("Set timeout to {}".format(story_manager.inference_timeout))
                        except:
                            await dm.send_msg("Failed to set timeout. Example usage: infto 30")
                            continue
                    
                elif command == "temp":
                
                    if len(args) != 1:
                        await dm.send_msg("Failed to set temperature. Example usage: temp 0.4")
                    else:
                        try:
                            await dm.send_msg("Regenerating model, please wait...")
                            story_manager.generator.change_temp(float(args[0]))
                            story_manager.generator.gen_output()
                            await dm.send_msg("Set temp to {}".format(story_manager.generator.temp))
                        except:
                            await dm.send_msg("Failed to set temperature. Example usage: temp 0.4")
                            continue
                
                elif command == "topk":
                
                    if len(args) != 1:
                        await dm.send_msg("Failed to set top_k. Example usage: topk 80")
                    else:
                        try:
                            await dm.send_msg("Regenerating model, please wait...")
                            story_manager.generator.change_topk(int(args[0]))
                            story_manager.generator.gen_output()
                            await dm.send_msg("Set top_k to {}".format(story_manager.generator.top_k))
                        except:
                            await dm.send_msg("Failed to set top_k. Example usage: topk 80")
                            continue
                
                elif command == 'remember':

                    try:
                        story_manager.story.context += "You know " + " ".join(args[0:]) + ". "
                        await dm.send_msg("You make sure to remember {}.".format(" ".join(action.split(" ")[1:])))
                    except:
                        await dm.send_msg("Failed to add to memory. Example usage: remember that Sir Theo is a knight")
                    
                elif command == 'retry':

                    if len(story_manager.story.actions) is 0:
                        await dm.send_msg("There is nothing to retry.")
                        continue

                    last_action = story_manager.story.actions.pop()
                    last_result = story_manager.story.results.pop()

                    try:
                        try:
                            story_manager.act_with_timeout(last_action)
                            await dm.send_msg(last_action + '\n' + story_manager.story.results[-1])
                        except FunctionTimedOut:
                            await dm.send_msg("That input caused the model to hang (timeout is {}, use infto ## command to change)".format(story_manager.inference_timeout))
                    except NameError:
                        pass
                    if ping:
                        playsound('ping.mp3')

                    continue
                else:
                    await dm.send_msg(f"Unknown command: {command}")

            else:
                if action == "":
                    action = "\n> \n"
                    
                elif action[0] == '!':
                    action = "\n> \n" + action[1:].replace("\\n", "\n") + "\n"

                elif action[0] != '"':
                    action = action.strip()
                    if not action.lower().startswith("you ") and not action.lower().startswith("i "):
                        action = "You " + action
                        
                    action = action[0].lower() + action[1:]

                    if action[-1] not in [".", "?", "!"]:
                        action = action + "."

                    action = first_to_second_person(action)

                    action = "\n> " + action + "\n"

                if "say" in action or "ask" in action or "\"" in action:
                    story_manager.generator.generate_num = 120
                    
                try:
                    result = "\n" + story_manager.act_with_timeout(action)
                except FunctionTimedOut:
                    await dm.send_msg(f"That input caused the model to hang (timeout is {story_manager.inference_timeout}, use infto ## command to change)")
                    if ping:
                        playsound('ping.mp3')
                    continue
                if len(story_manager.story.results) >= 2:
                    similarity = get_similarity(
                        story_manager.story.results[-1], story_manager.story.results[-2]
                    )
                    if similarity > 0.9:
                        story_manager.story.actions = story_manager.story.actions[:-1]
                        story_manager.story.results = story_manager.story.results[:-1]
                        await dm.send_msg(
                            "Woops that action caused the model to start looping. Try a different action to prevent that."
                        )
                        if ping:
                            playsound('ping.mp3')
                        continue

                if player_won(result):
                    await dm.send_msg(result + "\n CONGRATS YOU WIN")
                    break
                elif player_died(result):
                    await dm.send_msg(
                        result + 
                        "YOU DIED. GAME OVER\n" + 
                        "\nOptions:" + 
                        "0) Start a new game\n" + 
                        "1) \"I'm not dead yet!\" (If you didn't actually die)\n"+
                        "Which do you choose?"
                    )
                    choice = await get_num_options(2)
                    if choice == 0:
                        break
                    else:
                        await dm.send_msg("Sorry about that...where were we?\n\n"+result)

                else:
                    await dm.send_msg(result)
                if ping:
                    playsound('ping.mp3')
                story_manager.generator.generate_num = story_manager.generator.default_gen_num


if __name__ == "__main__":
    # play_aidungeon_2()
    # We need to run play_aidungeon_2() only after starting up, so in "on_ready"
    dm.start()
