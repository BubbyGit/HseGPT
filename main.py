from langchain.schema import HumanMessage, SystemMessage
from langchain.chat_models.gigachat import GigaChat
from kandinsky_api.kandinsky import Text2ImageAPI
from speech_api.speechAPI import text_to_speech
from yandex_api.yandex_gpt import yandex_gpt_completion
from PIL import Image
from io import BytesIO
import base64
import sqlite3
import telebot
from telebot import types
import json
import os

# Get the API from the file "APIKeys.json"
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "APIKeys.json"), "r") as file:
    api_keys = json.load(file)

API_TELEGRAM = api_keys.get("API_Telegram")
API_CHATGPT = api_keys.get("API_ChatGPT")
API_GIGACHAT = GigaChat(credentials=api_keys.get("API_GigaChat"), verify_ssl_certs=False)
API_KANDINSKY = (api_keys.get("API_Kandinsky")).split(':')
API_SPEECH = api_keys.get("API_Speech")
API_YANDEX = (api_keys.get("API_Yandex")).split(':')

bot = telebot.TeleBot(API_TELEGRAM)

user_states = {'DEFAULT': 0,
               'GIGACHAT': 1,
               'SETTINGS': 2,
               'KANDINSKY': 3,
               'Speech': 4,
               'Yandex': 5}


# Processing the '/start' command
@bot.message_handler(commands=['start'])
def send_welcome(message):
    """
    После отправки сообщения /start пишет приветcтвенное сообщение, если пользователь уже пользовался ботом, то устанавливает предыдущий характер бота, в ином случае характер='Ты помогаешь пользователю решить его проблемы'.
    
    Args:
        message (str): сообщение пользователя.
    Returns:
        str: Отправляет привественное сообщение пользователю.
    """
    sql_connect = sqlite3.connect("users.db")
    user_id = message.from_user.id

    cursor = sql_connect.cursor()
    cursor.execute('SELECT * FROM result WHERE ID = ?', (user_id,))
    existing_user = cursor.fetchone()

    if not existing_user:
        cursor.execute('INSERT INTO result (ID, Character_Giga) VALUES (?, ?)',
                       (user_id, 'Ты помогаешь пользователю решить его проблемы'))
        sql_connect.commit()

    with open('messages/ru-ru/welcome.txt', 'r', encoding='utf-8') as file:
        welcome_message = file.read()

    bot.reply_to(message, welcome_message)


# Processing the '/settings' command
@bot.message_handler(commands=['settings'])
def settings(message):
    """
    При отправке пользователем сообщения /settings, переводится в режим "SETTINGS" и отправляет сообщение с выбором характера бота.
    
    Args: 
        message (str): сообщение пользователя.
    Returns: 
        str: Отправляет сообщение с выбором характера бота.
    """
    user_states[message.from_user.id] = user_states['SETTINGS']
    with open('messages/ru-ru/character.txt', 'r', encoding='utf-8') as file:
        character_message = file.read()
    bot.send_message(message.chat.id, character_message)


@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == user_states['SETTINGS'])
def settings_set(message):
    """
    При нахождении в режиме 'SETTINGS' после установки характера пользователем отправляет сообщение 'Характер успешно установлен' и переводит в режим 'DEFAULT'.
    
    Args: 
        message (str): сообщение пользователя.
    Returns: 
        str: Отправляет сообщение об успешной установке характера.
    """
    user_id = message.from_user.id
    user_input = message.text

    sql_connect = sqlite3.connect("users.db")
    cursor = sql_connect.cursor()

    cursor.execute('UPDATE result SET Character_Giga = ? WHERE ID = ?', (user_input, user_id))
    sql_connect.commit()

    bot.send_message(message.chat.id, 'Характер успешно установлен')
    user_states[user_id] = user_states['DEFAULT']


# Processing the '/giga' command
@bot.message_handler(commands=['giga'])
def giga(message):
    """
    При отправке пользователем сообщения /giga отправляет сообщение 'Задавай мне вопросы' и переводит в режим  'GIGACHAT'.
    
    Args: 
        message (str): сообщение пользователя.
    Returns:
        str: Отправляет сообщение 'Задавай мне вопросы'.
    """
    user_states[message.from_user.id] = user_states['GIGACHAT']
    bot.send_message(message.chat.id, 'Задавай мне вопросы')


@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == user_states['GIGACHAT'])
def gigachat(message):
    """
    При нахождении в режиме 'GIGACHAT' при отправке пользователем сообщения "остановить бота" возвращает пользователя в главное меню, переводит в режим 'DEFAULT' и отправляет сообщение 'Вы вернулись в главное меню.', в ином случае обрабатывает запрос пользователя и отправляет ответ.
    
    Args: 
        message (str): сообщение пользователя.
    Returns:
        str: Возвращает в главное меню либо отвечает на запрос.
    """
    user_id = message.from_user.id
    user_input = message.text

    sql_connect = sqlite3.connect("users.db")
    cursor = sql_connect.cursor()
    cursor.execute('SELECT Character_Giga FROM result WHERE ID = ?', (user_id,))
    character_input = (cursor.fetchone())[0]

    messages = [SystemMessage(content=character_input)]
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    stop_button = types.KeyboardButton("Остановить бота")
    markup.add(stop_button)

    if user_input != 'Остановить бота':
        messages.append(HumanMessage(content=user_input))
        res = API_GIGACHAT(messages)
        messages.append(res)
        bot.send_message(message.chat.id, res.content, reply_markup=markup)
    else:
        sql_connect.close()
        bot.send_message(message.chat.id, 'Вы вернулись в главное меню.')
        user_states[user_id] = user_states['DEFAULT']


# Processing the '/img' command
@bot.message_handler(commands=['img'])
def kandinsky(message):
    """
    При отправке пользователем сообщения /img отправляет сообщение 'Напишите, что вы хотите сгенерировать.'.
    
    Args: 
        message (str): сообщение пользователя.
    Returns: 
        str: Отправляет сообщение 'Напишите, что вы хотите сгенерировать.'.
    """
    user_states[message.from_user.id] = user_states['KANDINSKY']
    bot.send_message(message.chat.id, 'Напишите, что вы хотите сгенерировать.')


@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == user_states['KANDINSKY'])
def kandinsky_img(message):
    """
    При нахождении в режиме 'KANDINSKY' при отправке пользователем сообщения 'Остановить бота' возвращает пользователя в главное меню, переводит в режим 'DEFAULT' и отправляет сообщение 'Вы вернулись в главное меню.', в ином случае гененирует картинку по запросу пользователя.
    
    Args: 
        message (str): сообщение пользователя.
    Returns: 
        str: Возвращает в главное меню либо генерирует картинку.
    """

    user_id = message.from_user.id
    user_input = message.text

    if user_input == 'Остановить бота':
        bot.send_message(message.chat.id, 'Вы вернулись в главное меню.')
        user_states[user_id] = user_states['DEFAULT']
    else:
        api_keys.get("API_Kandinsky")
        api = Text2ImageAPI('https://api-key.fusionbrain.ai/', API_KANDINSKY[0],
                            API_KANDINSKY[1])
        model_id = api.get_model()
        uuid = api.generate(user_input, model_id)
        images = api.check_generation(uuid)
        image_data_decoded = base64.b64decode(images[0])
        image = Image.open(BytesIO(image_data_decoded))
        bot.send_photo(message.chat.id, image)


# Processing the '/speech' command
@bot.message_handler(commands=['voice'])
def speech(message):
    """
    При отправке пользователем сообщения /speech переводит в режим 'Speech' и отправляет сообщение 'Напишите текст, который вы бы хотели озвучить. \n (❗️На данный момент поддерживается только языки: *Английский*)'.
    
    Args: 
        message (str): сообщение пользователя.
    Returns: 
        str: Отправляет сообщение 'Напишите текст, который вы бы хотели озвучить. \n (❗️На данный момент поддерживается только языки: *Английский*)'.
    """
    user_states[message.from_user.id] = user_states['Speech']
    bot.send_message(message.chat.id, 'Напишите текст, который вы бы хотели озвучить. \n'
                                      '(❗️На данный момент поддерживается только языки: *Английский*)')


@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == user_states['Speech'])
def voice_convert(message):
    """
    При нахождении в режиме 'Speech' при отправке пользователем сообщения 'Остановить бота' возрващает в главное меню, переводит в режим 'DEFAULT' и отправляет сообщение 'Вы вернулись в главное меню.', в ином случае преобразует текст, написанный пользователем на английском, в голосовое сообщение.
    
    Args: 
        message (str): сообщение пользователя.
    Returns:
        str: Возвращает пользователся в главное меню либо отправляет голосовое сообщение.
    """
    user_id = message.from_user.id
    user_input = message.text

    if user_input == 'Остановить бота':
        bot.send_message(message.chat.id, 'Вы вернулись в главное меню.')
        user_states[user_id] = user_states['DEFAULT']
    else:
        voice = text_to_speech(user_input, API_SPEECH)
        bot.send_voice(message.chat.id, voice)


# Processing the '/gptpro' command
@bot.message_handler(commands=['gptpro'])
def yandex(message):
    """
    При отправке пользователем сообщения /gptpro переводит пользователя в режим 'Yandex' и отправляет приветственное сообщение о gptpro.

    Args: 
        message (str): сообщение пользователя.
    Returns: 
        str: Отправляет приветственное сообщение о gptpro.
    """
    user_states[message.from_user.id] = user_states['Yandex']

    with open('messages/ru-ru/yandex_send.txt', 'r', encoding='utf-8') as file:
        welcome_message = file.read()

    bot.send_message(message.chat.id, welcome_message)


@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == user_states['Yandex'])
def yandex_gpt(message):
    """
    При нахождении в режиме 'Yandex' при отправке пользователем сообщения 'Остановить бота' возвращает пользователя в главное меню, переводит в режим 'DEFAULT' и отправляет сообщение 'Вы вернулись в главное меню.', в ином случае обрабатывает запрос пользователся и отправляет ответ.

    Args:
        message (str): сообщение пользователя.
    Returns:
        str: Возвращает пользователя в главное меню либо отвечает на запрос.
    """
    user_id = message.from_user.id
    user_input = message.text

    sql_connect = sqlite3.connect("users.db")
    cursor = sql_connect.cursor()
    cursor.execute('SELECT Character_Giga FROM result WHERE ID = ?', (user_id,))
    character_input = (cursor.fetchone())[0]
    sql_connect.close()

    print(user_input, character_input, API_YANDEX[0], API_YANDEX[1])

    if user_input == 'Остановить бота':
        bot.send_message(message.chat.id, 'Вы вернулись в главное меню.')
        user_states[user_id] = user_states['DEFAULT']
    else:
        bot.send_message(user_id, yandex_gpt_completion(user_input, character_input, API_YANDEX[0], API_YANDEX[1]))


bot.infinity_polling()
