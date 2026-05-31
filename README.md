# vk_api

[![PyPI](https://img.shields.io/pypi/v/vk_api.svg)](https://pypi.org/project/vk_api/)
[![Python](https://img.shields.io/pypi/pyversions/vk_api.svg)](https://pypi.org/project/vk_api/)
[![License](https://img.shields.io/github/license/aaxnet/vk_api)](LICENSE)

**vk_api** — Python-модуль для работы с VK API (ВКонтакте).  
Форк [python273/vk_api](https://github.com/python273/vk_api) с обновлениями и улучшениями.

---

## Установка

```bash
pip install vk_api
```

Для работы с аудио:
```bash
pip install vk_api[vkaudio]
```

Для VK Streaming API:
```bash
pip install vk_api[vkstreaming]
```

---

## Быстрый старт

### Авторизация через токен (рекомендуется)

```python
import vk_api

vk_session = vk_api.VkApi(token='ваш_токен')
vk = vk_session.get_api()

# Вызов методов API
users = vk.users.get(user_ids='1', fields='city,photo_200')
print(users[0])

# Публикация поста
vk.wall.post(message='Привет мир!')
```

### Авторизация через логин и пароль

```python
import vk_api

vk_session = vk_api.VkApi('+71234567890', 'пароль')
vk_session.auth()
vk = vk_session.get_api()
```

### Токен группы (для ботов)

```python
import vk_api

vk_session = vk_api.VkApiGroup(token='токен_группы')
vk = vk_session.get_api()

# Группы могут делать 20 запросов/сек вместо 3
vk.messages.send(peer_id=123456, message='Привет!', random_id=0)
```

### Контекстный менеджер

```python
with vk_api.VkApi(token='...') as session:
    vk = session.get_api()
    print(vk.users.get(user_ids='1'))
# HTTP-сессия закрывается автоматически
```

---

## Ключевые возможности

### Вызов методов API

```python
# camelCase и snake_case — оба варианта работают
vk.wall.getById(posts='...')
vk.wall.get_by_id(posts='...')

# Списки автоматически преобразуются в строки
vk.users.get(user_ids=['1', '2', '3'])  # -> '1,2,3'

# Версия API настраивается
vk_session = vk_api.VkApi(token='...', api_version='5.199')
```

### Клавиатуры для ботов

```python
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

# Обычная клавиатура
keyboard = VkKeyboard(one_time=True)
keyboard.add_button('Да', color=VkKeyboardColor.POSITIVE)
keyboard.add_button('Нет', color=VkKeyboardColor.NEGATIVE)
keyboard.add_line()
keyboard.add_button('Назад')

vk.messages.send(
    peer_id=user_id,
    message='Вы уверены?',
    keyboard=keyboard.get_keyboard(),
    random_id=0
)

# Inline-клавиатура (внутри сообщения)
keyboard = VkKeyboard(inline=True)
keyboard.add_callback_button('Нажми!', payload={'action': 'click'})
keyboard.add_openlink_button('VK', 'https://vk.com')

# Быстрое создание клавиатуры из списка
keyboard = VkKeyboard.from_buttons([
    [{'label': 'Кнопка 1', 'color': VkKeyboardColor.PRIMARY},
     {'label': 'Кнопка 2'}],
    [{'label': 'Отмена', 'color': VkKeyboardColor.NEGATIVE}],
])

# Скрыть клавиатуру
vk.messages.send(peer_id=user_id, keyboard=VkKeyboard.get_empty_keyboard(), ...)
```

### Получение больших объёмов данных

```python
from vk_api.tools import VkTools

tools = VkTools(vk_session)

# Все посты стены (использует execute — быстро)
for post in tools.get_all_iter('wall.get', 100, {'owner_id': -1}):
    print(post['text'])

# Или загрузить всё в память
result = tools.get_all('friends.get', 200, {'user_id': 1})
print(f"Друзей: {result['count']}")

# Без execute (для методов, не поддерживающих его)
result = tools.get_all_slow('messages.getHistory', 200, {'peer_id': 123456})
```

### LongPoll для ботов

```python
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType

vk_session = vk_api.VkApiGroup(token='токен_группы')
longpoll = VkBotLongPoll(vk_session, group_id=123456)

for event in longpoll.listen():
    if event.type == VkBotEventType.MESSAGE_NEW:
        msg = event.message
        print(f'Сообщение: {msg.text}')

        vk.messages.send(
            peer_id=msg.peer_id,
            message=f'Вы написали: {msg.text}',
            random_id=0
        )
```

### LongPoll для пользователей

```python
from vk_api.longpoll import VkLongPoll, VkEventType

vk_session = vk_api.VkApi(token='...')
longpoll = VkLongPoll(vk_session)

for event in longpoll.listen():
    if event.type == VkEventType.MESSAGE_NEW and event.to_me:
        print(f'Новое сообщение: {event.text}')
```

### Загрузка файлов

```python
from vk_api.upload import VkUpload

upload = VkUpload(vk_session)

# Фото на стену
photo = upload.photo_wall('путь/к/фото.jpg')
print(photo)

# Фото в сообщение
photo = upload.photo_messages('фото.jpg')
attachment = 'photo{}_{}'.format(photo[0]['owner_id'], photo[0]['id'])
vk.messages.send(peer_id=user_id, attachment=attachment, random_id=0)

# Документ
doc = upload.document('файл.txt', title='Мой документ')

# Видео
video = upload.video('видео.mp4', name='Моё видео', is_private=False)
```

### Обработка ошибок

```python
from vk_api.exceptions import ApiError, Captcha, NetworkError

try:
    vk.messages.send(peer_id=123, message='Тест', random_id=0)
except Captcha as e:
    # Ввести капчу и повторить
    key = input(f'Введите текст с картинки ({e.get_url()}): ')
    e.try_again(key)
except ApiError as e:
    print(f'Ошибка API [{e.code}]: {e}')
    print(f'Описание: {e.description}')
    # Повторить запрос
    e.try_method()
except NetworkError as e:
    print(f'Ошибка сети: {e}')
```

### Двухфакторная аутентификация

```python
def auth_handler():
    code = input('Введите код 2FA: ')
    remember = True  # Запомнить устройство
    return code, remember

vk_session = vk_api.VkApi(
    '+71234567890', 'пароль',
    auth_handler=auth_handler
)
vk_session.auth()
```

### Отладка

```python
from vk_api.utils import enable_debug_mode

vk_session = vk_api.VkApi(token='...')
enable_debug_mode(vk_session, print_content=True)
```

### Пул запросов

```python
from vk_api.requests_pool import VkRequestsPool

with VkRequestsPool(vk_session) as pool:
    users_ids = pool.method('users.get', {'user_ids': '1'})
    wall = pool.method('wall.get', {'owner_id': '1', 'count': 5})

# После выхода из блока — запросы выполнены
print(users_ids.result)
print(wall.result)
```

---

## Параметры VkApi

| Параметр | Тип | По умолчанию | Описание |
|---|---|---|---|
| `login` | str | — | Логин (телефон/email) |
| `password` | str | — | Пароль |
| `token` | str | — | access_token |
| `auth_handler` | callable | — | Обработчик 2FA |
| `captcha_handler` | callable | — | Обработчик капчи |
| `api_version` | str | `'5.199'` | Версия API |
| `app_id` | int | `6222115` | ID приложения |
| `scope` | int/str | все права | Запрашиваемые права |
| `timeout` | float | `30` | Таймаут HTTP-запросов |
| `max_retries` | int | `3` | Попыток при ошибке |

---

## Ссылки

- [Документация](https://vk-api.readthedocs.io/)
- [Примеры](examples/)
- [Методы VK API](https://dev.vk.com/ru/reference/methods)
- [Оригинальный репозиторий](https://github.com/python273/vk_api)

---

## Лицензия

Apache License 2.0 — подробнее в файле [LICENSE](LICENSE).
