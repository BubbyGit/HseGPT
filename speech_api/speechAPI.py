import requests
import json
import time


def text_to_speech(text, api):
    """
    Получает на вход текст от пользователя и api из файла, отправляет запрос по указзаному url, при получении ответа от сервера отправляет ответ пользователю в виде голосового сообщения, в ином случае отправляет запрос ещё раз.

    Args: 
        text (str): Сообщение пользователя на английском языке.
        api (str): api из файла с api.
    Returns:
        (OGG): Отправляет голосовое сообщение.
    """
    url = "https://large-text-to-speech.p.rapidapi.com/tts"
    payload = {"text": text}

    headers = {
        'content-type': "application/json",
        'x-rapidapi-host': "large-text-to-speech.p.rapidapi.com",
        'x-rapidapi-key': api
    }

    response = requests.request("POST", url, data=json.dumps(payload), headers=headers)

    id = json.loads(response.text)['id']
    eta = json.loads(response.text)['eta']

    time.sleep(eta)

    response = requests.request("GET", url, headers=headers, params={'id': id})
    while "url" not in json.loads(response.text):
        response = requests.get(url, headers=headers, params={'id': id})
        time.sleep(5)

    if not "error" in json.loads(response.text):
        result_url = json.loads(response.text)['url']
        response = requests.get(result_url)
        return response.content
