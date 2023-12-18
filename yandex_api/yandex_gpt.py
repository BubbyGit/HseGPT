import requests


def yandex_gpt_completion(user_text, character, api, userkey):
    """
     Получает на вход текст от пользователя, заданный характер,api и userkey из файла и  отправляет запрос по указзаному url, после получения ответа от сервера отправляет ответ на запрос пользователя, в случае, если сообщение пользователя содержит запрещенные слова отправляет сообщение 'Ваше сообщение содержить запрещенные слова, я не люблю на такое отвечать'.

     Args:
        user_text (str): Сообщение пользователя.
        character (str): Заданный ранее характер.
        api (str): api из файла с api.
        user_key (str): ключ из файла с api.
    Returns:
        (str): Ответ на запрос пользователя либо сообщение 'Ваше сообщение содержить запрещенные слова, я не люблю на такое отвечать'.
    """
    prompt = {
        "modelUri": f"gpt://{userkey}/yandexgpt-lite",
        "completionOptions": {
            "stream": False,
            "temperature": 0.6,
            "maxTokens": "2000"
        },
        "messages": [
            {
                "role": "system",
                "text": character
            },
            {
                "role": "user",
                "text": user_text
            },
        ]
    }

    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {api}"
    }

    response = requests.post(url, headers=headers, json=prompt)
    result = response.json()

    if 'result' in result and 'alternatives' in result['result'] and len(result['result']['alternatives']) > 0:
        return result['result']['alternatives'][0]['message']['text']
    else:
        return 'Ваше сообщение содержить запрещенные слова, я не люблю на такое отвечать'
