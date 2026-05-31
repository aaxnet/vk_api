# -*- coding: utf-8 -*-
"""
:authors: python273, Helow19274, prostomarkeloff, aaxnet
:license: Apache License, Version 2.0, see LICENSE file
:copyright: (c) 2019 python273, 2024 aaxnet
"""

from __future__ import annotations
from enum import Enum
from typing import Optional, Union

from .utils import sjson_dumps


MAX_BUTTONS_ON_LINE = 5
MAX_DEFAULT_LINES = 10
MAX_INLINE_LINES = 6


class VkKeyboardColor(Enum):
    """Цвета кнопок клавиатуры"""

    #: Синяя (основное действие)
    PRIMARY = 'primary'

    #: Белая (вторичное действие)
    SECONDARY = 'secondary'

    #: Красная (опасное действие)
    NEGATIVE = 'negative'

    #: Зелёная (положительное действие)
    POSITIVE = 'positive'


class VkKeyboardButton(Enum):
    """Типы кнопок клавиатуры"""

    #: Кнопка с текстом
    TEXT = 'text'

    #: Кнопка с местоположением
    LOCATION = 'location'

    #: Кнопка с оплатой VKPay
    VKPAY = 'vkpay'

    #: Кнопка VK Mini Apps
    VKAPPS = 'open_app'

    #: Кнопка со ссылкой
    OPENLINK = 'open_link'

    #: Callback-кнопка
    CALLBACK = 'callback'


class VkKeyboard:
    """Конструктор клавиатуры для ботов ВКонтакте

    `Документация: https://dev.vk.com/ru/api/bots/development/keyboard`

    :param one_time: Скрыть клавиатуру после нажатия
    :type one_time: bool
    :param inline: Отображать клавиатуру внутри сообщения
    :type inline: bool

    Пример создания простой клавиатуры::

        from vk_api.keyboard import VkKeyboard, VkKeyboardColor

        keyboard = VkKeyboard(one_time=True)
        keyboard.add_button('Да', color=VkKeyboardColor.POSITIVE)
        keyboard.add_button('Нет', color=VkKeyboardColor.NEGATIVE)
        keyboard.add_line()
        keyboard.add_button('Отмена')

        vk.messages.send(
            peer_id=user_id,
            message='Вы уверены?',
            keyboard=keyboard.get_keyboard(),
            random_id=0
        )

    Пример inline-клавиатуры::

        keyboard = VkKeyboard(inline=True)
        keyboard.add_button('Кнопка 1', payload={'action': 'btn1'})
        keyboard.add_button('Кнопка 2', payload={'action': 'btn2'})
    """

    __slots__ = ('one_time', 'lines', 'keyboard', 'inline')

    def __init__(self, one_time: bool = False, inline: bool = False):
        self.one_time = one_time
        self.inline = inline
        self.lines = [[]]

        self.keyboard = {
            'one_time': self.one_time,
            'inline': self.inline,
            'buttons': self.lines,
        }

    def get_keyboard(self) -> str:
        """Получить JSON клавиатуры для отправки в API

        :return: JSON строка
        """
        return sjson_dumps(self.keyboard)

    @classmethod
    def get_empty_keyboard(cls) -> str:
        """Получить JSON пустой клавиатуры.

        Отправка пустой клавиатуры скрывает текущую у пользователя.

        :return: JSON строка пустой клавиатуры
        """
        keyboard = cls()
        keyboard.keyboard['buttons'] = []
        return keyboard.get_keyboard()

    def _check_line_capacity(self) -> None:
        """Проверить, есть ли место для кнопки в текущей строке"""
        if len(self.lines[-1]) >= MAX_BUTTONS_ON_LINE:
            raise ValueError(
                f'Максимум {MAX_BUTTONS_ON_LINE} кнопок в строке. '
                'Используйте add_line() для новой строки.'
            )

    def _check_empty_line(self) -> None:
        """Проверить, что строка пуста (для кнопок на всю ширину)"""
        if len(self.lines[-1]) != 0:
            raise ValueError(
                'Эта кнопка должна занимать всю ширину строки. '
                'Добавьте новую строку с add_line()'
            )

    def _encode_payload(self, payload) -> Optional[str]:
        """Закодировать payload в JSON строку"""
        if payload is None:
            return None
        if isinstance(payload, str):
            return payload
        return sjson_dumps(payload)

    def add_button(
        self,
        label: str,
        color: Union[VkKeyboardColor, str] = VkKeyboardColor.SECONDARY,
        payload=None
    ) -> 'VkKeyboard':
        """Добавить текстовую кнопку

        :param label: Текст кнопки (также отправляется при нажатии)
        :param color: Цвет кнопки
        :param payload: Дополнительные данные для Callback API
        :return: self (для цепочки вызовов)
        """
        self._check_line_capacity()

        color_value = color.value if isinstance(color, VkKeyboardColor) else color

        self.lines[-1].append({
            'color': color_value,
            'action': {
                'type': VkKeyboardButton.TEXT.value,
                'payload': self._encode_payload(payload),
                'label': label,
            },
        })
        return self

    def add_callback_button(
        self,
        label: str,
        color: Union[VkKeyboardColor, str] = VkKeyboardColor.SECONDARY,
        payload=None
    ) -> 'VkKeyboard':
        """Добавить callback-кнопку

        :param label: Текст кнопки
        :param color: Цвет кнопки
        :param payload: Данные события (dict, str или None)
        :return: self (для цепочки вызовов)
        """
        self._check_line_capacity()

        color_value = color.value if isinstance(color, VkKeyboardColor) else color

        self.lines[-1].append({
            'color': color_value,
            'action': {
                'type': VkKeyboardButton.CALLBACK.value,
                'payload': self._encode_payload(payload),
                'label': label,
            },
        })
        return self

    def add_location_button(self, payload=None) -> 'VkKeyboard':
        """Добавить кнопку геолокации

        Занимает всю ширину строки.

        :param payload: Дополнительные данные
        :return: self (для цепочки вызовов)
        """
        self._check_empty_line()

        self.lines[-1].append({
            'action': {
                'type': VkKeyboardButton.LOCATION.value,
                'payload': self._encode_payload(payload),
            },
        })
        return self

    def add_vkpay_button(self, hash: str, payload=None) -> 'VkKeyboard':
        """Добавить кнопку оплаты VKPay

        Занимает всю ширину строки.

        :param hash: Параметры платежа (amount=..&description=..&action=..&aid=..)
        :param payload: Дополнительные данные
        :return: self (для цепочки вызовов)
        """
        self._check_empty_line()

        self.lines[-1].append({
            'action': {
                'type': VkKeyboardButton.VKPAY.value,
                'payload': self._encode_payload(payload),
                'hash': hash,
            },
        })
        return self

    def add_vkapps_button(
        self,
        app_id: int,
        owner_id: int,
        label: str,
        hash: str,
        payload=None
    ) -> 'VkKeyboard':
        """Добавить кнопку VK Mini Apps

        Занимает всю ширину строки.

        :param app_id: ID приложения
        :param owner_id: ID сообщества (отрицательное)
        :param label: Название приложения на кнопке
        :param hash: Хэш для навигации внутри приложения
        :param payload: Дополнительные данные
        :return: self (для цепочки вызовов)
        """
        self._check_empty_line()

        self.lines[-1].append({
            'action': {
                'type': VkKeyboardButton.VKAPPS.value,
                'app_id': app_id,
                'owner_id': owner_id,
                'label': label,
                'payload': self._encode_payload(payload),
                'hash': hash,
            },
        })
        return self

    def add_openlink_button(
        self,
        label: str,
        link: str,
        payload=None
    ) -> 'VkKeyboard':
        """Добавить кнопку-ссылку

        :param label: Текст кнопки
        :param link: URL для открытия
        :param payload: Дополнительные данные
        :return: self (для цепочки вызовов)
        """
        self._check_line_capacity()

        self.lines[-1].append({
            'action': {
                'type': VkKeyboardButton.OPENLINK.value,
                'link': link,
                'label': label,
                'payload': self._encode_payload(payload),
            },
        })
        return self

    def add_line(self) -> 'VkKeyboard':
        """Добавить новую строку кнопок

        Лимиты:
        - Обычная клавиатура: до 10 строк
        - Inline-клавиатура: до 6 строк

        :return: self (для цепочки вызовов)
        """
        max_lines = MAX_INLINE_LINES if self.inline else MAX_DEFAULT_LINES
        if len(self.lines) >= max_lines:
            raise ValueError(
                f'Максимум {max_lines} строк для '
                f'{"inline" if self.inline else "обычной"} клавиатуры'
            )
        self.lines.append([])
        return self

    def __len__(self) -> int:
        return sum(len(line) for line in self.lines)

    def __repr__(self) -> str:
        button_count = len(self)
        return (
            f'<VkKeyboard inline={self.inline} '
            f'one_time={self.one_time} '
            f'buttons={button_count}>'
        )

    @classmethod
    def from_buttons(
        cls,
        buttons: list,
        one_time: bool = False,
        inline: bool = False
    ) -> 'VkKeyboard':
        """Быстро создать клавиатуру из списка кнопок

        :param buttons: список списков с параметрами кнопок
            Каждый подсписок — строка; каждый элемент — dict с ключами
            'label', 'color', 'payload' (опционально)
        :param one_time: Скрыть после нажатия
        :param inline: Inline-режим
        :return: VkKeyboard

        Пример::

            keyboard = VkKeyboard.from_buttons([
                [{'label': 'Кнопка 1', 'color': VkKeyboardColor.PRIMARY},
                 {'label': 'Кнопка 2'}],
                [{'label': 'Отмена', 'color': VkKeyboardColor.NEGATIVE}],
            ])
        """
        kb = cls(one_time=one_time, inline=inline)

        for i, row in enumerate(buttons):
            if i > 0:
                kb.add_line()
            for btn in row:
                kb.add_button(
                    label=btn['label'],
                    color=btn.get('color', VkKeyboardColor.SECONDARY),
                    payload=btn.get('payload')
                )

        return kb
