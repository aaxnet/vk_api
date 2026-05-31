# -*- coding: utf-8 -*-
"""
vk_api — Python клиент для VK API (ВКонтакте)

:authors: python273, aaxnet
:license: Apache License, Version 2.0, see LICENSE file
:copyright: (c) 2019 python273, 2024 aaxnet

Быстрый старт::

    import vk_api

    # Авторизация через токен (рекомендуется)
    vk_session = vk_api.VkApi(token='ваш_токен')
    vk = vk_session.get_api()

    # Авторизация через логин/пароль
    vk_session = vk_api.VkApi('+71234567890', 'пароль')
    vk_session.auth()
    vk = vk_session.get_api()

    # Авторизация для группы
    vk_session = vk_api.VkApiGroup(token='токен_группы')
    vk = vk_session.get_api()

    # Вызов методов API
    print(vk.users.get(user_ids='1'))
    print(vk.wall.post(message='Привет мир!'))
"""

from .enums import VkUserPermissions
from .exceptions import (
    VkApiError,
    AccessDenied,
    AuthError,
    LoginRequired,
    PasswordRequired,
    BadPassword,
    AccountBlocked,
    TwoFactorError,
    TokenExpiredError,
    SecurityCheck,
    ApiError,
    ApiHttpError,
    Captcha,
    VkAudioException,
    VkAudioUrlDecodeError,
    VkToolsException,
    VkRequestsPoolException,
    RateLimitError,
    NetworkError,
    ParseError,
)
from .keyboard import VkKeyboard, VkKeyboardColor, VkKeyboardButton
from .requests_pool import VkRequestsPool, vk_request_one_param_pool
from .tools import VkTools
from .upload import VkUpload
from .vk_api import VkApi, VkApiGroup, VkApiMethod

__author__ = 'python273, aaxnet'
__version__ = '12.0.0'
__email__ = 'vk_api@python273.pw'

__all__ = [
    # Основные классы
    'VkApi',
    'VkApiGroup',
    'VkApiMethod',

    # Инструменты
    'VkTools',
    'VkUpload',
    'VkRequestsPool',
    'vk_request_one_param_pool',

    # Клавиатура
    'VkKeyboard',
    'VkKeyboardColor',
    'VkKeyboardButton',

    # Перечисления
    'VkUserPermissions',

    # Исключения
    'VkApiError',
    'AccessDenied',
    'AuthError',
    'LoginRequired',
    'PasswordRequired',
    'BadPassword',
    'AccountBlocked',
    'TwoFactorError',
    'TokenExpiredError',
    'SecurityCheck',
    'ApiError',
    'ApiHttpError',
    'Captcha',
    'VkAudioException',
    'VkAudioUrlDecodeError',
    'VkToolsException',
    'VkRequestsPoolException',
    'RateLimitError',
    'NetworkError',
    'ParseError',
]
