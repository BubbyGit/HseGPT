import pytest
from unittest.mock import Mock, patch
import os
import sys

# Получаем путь к текущей директории (test)
current_dir = os.path.dirname(os.path.abspath(__file__))
# Добавляем путь к папке kandinsky_api
kandinsky_api_path = os.path.abspath(os.path.join(current_dir, '..', 'kandinsky_api'))
sys.path.append(kandinsky_api_path)
from kandinsky import Text2ImageAPI


# Создаем фикстуру, предоставляющую экземпляр Text2ImageAPI для тестов
@pytest.fixture
def text2image_api():
    API_URL = 'https://api-key.fusionbrain.ai/'
    API_KEY = '7C150216FF646DC9053927B910E6994B'
    SECRET_KEY = 'E4893BFD787F24D31D6D9E782360A28F'
    return Text2ImageAPI(API_URL, API_KEY, SECRET_KEY)

# Мокаем запрос к API для изоляции тестов от фактических HTTP-запросов
@patch('requests.post')
@patch('requests.get')
def test_generate_calls_api_correctly(mock_get, mock_post, text2image_api):
    # Замоканные данные ответа
    mock_get.return_value.json.return_value = {'status': 'DONE', 'images': ['image_url']}
    mock_post.return_value.json.return_value = {'uuid': '123'}

    # Вызываем метод generate
    request_id = text2image_api.generate('test prompt', 'model_id')

    # Проверяем, что запросы к API были выполнены с правильными параметрами
    mock_post.assert_called_once_with(
        'https://api-key.fusionbrain.ai/',
        headers={'X-Key': '7C150216FF646DC9053927B910E6994B', 'X-Secret': 'E4893BFD787F24D31D6D9E782360A28F'},
        files={'model_id': (None, 'model_id'), 'params': (None, '{"type": "GENERATE", "numImages": 1, "width": 1024, "height": 1024, "generateParams": {"query": "test prompt"}}', 'application/json')}
    )

    mock_get.assert_called_once_with(
        'https://api-key.fusionbrain.ai/',
        headers={'X-Key': '7C150216FF646DC9053927B910E6994B', 'X-Secret': 'E4893BFD787F24D31D6D9E782360A28F'}
    )

# Тест на проверку успешного завершения генерации изображения
@patch('requests.get')
def test_check_generation_returns_images_on_success(mock_get, text2image_api):
    # Замоканные данные ответа
    mock_get.return_value.json.return_value = {'status': 'DONE', 'images': ['image_url']}

    # Вызываем метод check_generation
    result = text2image_api.check_generation('123')

    # Проверяем, что результат содержит ожидаемые изображения
    assert result == ['image_url']

# Дополнительный тест на проверку повторных запросов при невыполненной генерации
@patch('requests.get', side_effect=[{'status': 'IN_PROGRESS'}, {'status': 'DONE', 'images': ['image_url']}])
def test_check_generation_retries_until_done(mock_get, text2image_api):
    # Вызываем метод check_generation с невыполненной генерацией
    result = text2image_api.check_generation('123', attempts=2, delay=0)

    # Проверяем, что результат содержит ожидаемые изображения
    assert result == ['image_url']

    # Проверяем, что было выполнено два запроса к API (первый неудачный, второй успешный)
    assert mock_get.call_count == 2

# Тест на проверку, что генерация завершается с ошибкой после нескольких неудачных попыток
@patch('requests.get', return_value={'status': 'IN_PROGRESS'})
def test_check_generation_returns_none_on_failure(mock_get, text2image_api):
    # Вызываем метод check_generation с неудачной генерацией
    result = text2image_api.check_generation('123', attempts=2, delay=0)

    # Проверяем, что результат равен None, так как генерация завершилась неудачей
    assert result is None

    # Проверяем, что было выполнено два запроса к API (два неудачных)
    assert mock_get.call_count == 2
    
# Тест для проверки успешного завершения генерации изображения
def test_check_generation_done(text2image_api):
     # Ожидаемые изображения
    expected_images = ['image1', 'image2']
    # Замоканный ответ
    mocked_response = {'status': 'DONE', 'images': expected_images}
     # Мокирование запроса к API
    with patch('requests.get', return_value=Mock(json=lambda: mocked_response)):
         # Вызываем метод check_generation
        images = text2image_api.check_generation('test_request_id')
         # Проверяем, что результат соответствует ожидаемым изображениям
        assert images == expected_images

# Тест для проверки повторных запросов при статусе PENDING и успешном завершении генерации
def test_check_generation_pending(text2image_api):
    # Замоканные ответы для двух запросов (PENDING и DONE)
    pending_response = {'status': 'PENDING'}
    done_response = {'status': 'DONE', 'images': ['image1', 'image2']}
    # Мокирование двух запросов к API
    with patch('requests.get', side_effect=[Mock(json=lambda: pending_response), Mock(json=lambda: done_response)]):
        # Вызываем метод check_generation
        images = text2image_api.check_generation('test_request_id')
         # Проверяем, что результат соответствует ожидаемым изображениям
        assert images == ['image1', 'image2']

# Тест для проверки, что генерация завершается с ошибкой при истечении времени ожидания
def test_check_generation_timeout(text2image_api):
     # Замоканный ответ со статусом PENDING
    timeout_response = {'status': 'PENDING'}
     # Мокирование запроса к API
    with patch('requests.get', return_value=Mock(json=lambda: timeout_response)):
         # Проверяем, что вызывается исключение TimeoutError
        with pytest.raises(TimeoutError):
            text2image_api.check_generation('test_request_id', attempts=1, delay=1)
