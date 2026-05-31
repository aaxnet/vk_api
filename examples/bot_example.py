#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Пример бота ВКонтакте с использованием Bots LongPoll API, клавиатуры и команд.

Требования:
  - Токен сообщества (группы) с правами на сообщения
  - Включённый LongPoll в настройках группы

Замените 'bot_api_token' и GROUP_ID на реальные значения.
"""

import logging

import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

GROUP_ID = 123456789  # ID вашей группы


def get_main_keyboard() -> str:
    """Создать основную клавиатуру"""
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button('📋 Помощь', color=VkKeyboardColor.PRIMARY, payload={'cmd': 'help'})
    keyboard.add_button('🎲 Случайное число', payload={'cmd': 'random'})
    keyboard.add_line()
    keyboard.add_button('👋 Привет', color=VkKeyboardColor.POSITIVE, payload={'cmd': 'hello'})
    keyboard.add_button('❌ Скрыть клавиатуру', color=VkKeyboardColor.NEGATIVE, payload={'cmd': 'hide'})
    return keyboard.get_keyboard()


def get_inline_keyboard(user_id: int) -> str:
    """Создать inline-клавиатуру"""
    keyboard = VkKeyboard(inline=True)
    keyboard.add_callback_button(
        '👍 Лайк',
        color=VkKeyboardColor.POSITIVE,
        payload={'cmd': 'like', 'user': user_id}
    )
    keyboard.add_callback_button(
        '👎 Дизлайк',
        color=VkKeyboardColor.NEGATIVE,
        payload={'cmd': 'dislike', 'user': user_id}
    )
    keyboard.add_line()
    keyboard.add_openlink_button('🔗 VK', 'https://vk.com')
    return keyboard.get_keyboard()


class Bot:
    def __init__(self, token: str, group_id: int):
        self.vk_session = vk_api.VkApiGroup(token=token)
        self.vk = self.vk_session.get_api()
        self.longpoll = VkBotLongPoll(self.vk_session, group_id)
        logger.info('Бот запущен, группа: %s', group_id)

    def send_message(
        self,
        peer_id: int,
        message: str,
        keyboard: str = None,
        attachments: list = None
    ) -> None:
        """Отправить сообщение"""
        params = {
            'peer_id': peer_id,
            'message': message,
            'random_id': get_random_id(),
        }
        if keyboard:
            params['keyboard'] = keyboard
        if attachments:
            params['attachment'] = ','.join(attachments)

        self.vk.messages.send(**params)

    def handle_message(self, event) -> None:
        """Обработать входящее сообщение"""
        msg = event.message
        peer_id = msg.peer_id
        text = (msg.text or '').lower().strip()

        logger.info('Сообщение от %s: %s', peer_id, text)

        # Обработка команд
        if text in ('помощь', 'help', '/help', '📋 помощь'):
            self.send_message(
                peer_id,
                '📖 Доступные команды:\n'
                '  • привет / hello — приветствие\n'
                '  • случайное число — генератор числа\n'
                '  • клавиатура — показать клавиатуру\n'
                '  • помощь — эта справка',
                keyboard=get_main_keyboard()
            )

        elif text in ('привет', 'hello', '/start', '👋 привет'):
            # Получить имя пользователя
            try:
                users = self.vk.users.get(user_ids=str(event.obj.peer_id))
                name = users[0]['first_name'] if users else 'друг'
            except Exception:
                name = 'друг'

            self.send_message(
                peer_id,
                f'Привет, {name}! 👋\nЯ тестовый бот. Напиши "помощь" для списка команд.',
                keyboard=get_main_keyboard()
            )

        elif text in ('случайное число', '🎲 случайное число', 'random'):
            import random
            number = random.randint(1, 1000)
            self.send_message(
                peer_id,
                f'🎲 Ваше случайное число: **{number}**',
                keyboard=get_inline_keyboard(peer_id)
            )

        elif text in ('клавиатура',):
            self.send_message(
                peer_id,
                'Вот ваша клавиатура!',
                keyboard=get_main_keyboard()
            )

        elif text in ('скрыть', '❌ скрыть клавиатуру'):
            self.send_message(
                peer_id,
                'Клавиатура скрыта.',
                keyboard=VkKeyboard.get_empty_keyboard()
            )

        else:
            # Эхо-ответ
            self.send_message(
                peer_id,
                f'Вы написали: {msg.text}\n\nНапиши "помощь" для списка команд.'
            )

    def handle_callback(self, event) -> None:
        """Обработать нажатие Callback-кнопки"""
        import json
        payload = json.loads(event.obj.payload or '{}')
        cmd = payload.get('cmd')

        logger.info('Callback от %s: %s', event.obj.peer_id, payload)

        if cmd == 'like':
            answer = '👍 Спасибо за лайк!'
        elif cmd == 'dislike':
            answer = '👎 Жаль...'
        else:
            answer = f'Нажата кнопка: {cmd}'

        # Отправить ответ на callback (всплывающее уведомление)
        self.vk.messages.sendMessageEventAnswer(
            event_id=event.obj.event_id,
            user_id=event.obj.user_id,
            peer_id=event.obj.peer_id,
            event_data=json.dumps({
                'type': 'show_snackbar',
                'text': answer
            })
        )

    def run(self) -> None:
        """Запустить бота"""
        logger.info('Слушаю события...')

        for event in self.longpoll.listen():
            try:
                if event.type == VkBotEventType.MESSAGE_NEW:
                    self.handle_message(event)

                elif event.type == VkBotEventType.MESSAGE_EVENT:
                    self.handle_callback(event)

            except vk_api.ApiError as e:
                logger.error('Ошибка API: %s', e)
            except Exception as e:
                logger.exception('Неожиданная ошибка: %s', e)


if __name__ == '__main__':
    bot = Bot(token='bot_api_token', group_id=GROUP_ID)
    bot.run()
