# -*- coding: utf-8 -*-
"""
:authors: python273, aaxnet
:license: Apache License, Version 2.0, see LICENSE file
:copyright: (c) 2019 python273, 2024 aaxnet
"""

from __future__ import annotations
import typing as t

# Коды ошибок
TWOFACTOR_CODE = -2
HTTP_ERROR_CODE = -1
TOO_MANY_RPS_CODE = 6
CAPTCHA_ERROR_CODE = 14
NEED_VALIDATION_CODE = 17
CONFIRMATION_ERROR_CODE = 1110

# Расшифровка кодов ошибок VK API
VK_ERROR_CODES: dict[int, str] = {
    1: 'Произошла неизвестная ошибка',
    2: 'Приложение отключено',
    3: 'Передан неизвестный метод',
    4: 'Неверная подпись',
    5: 'Авторизация пользователя не прошла',
    6: 'Слишком много запросов в секунду',
    7: 'Нет прав для выполнения этого действия',
    8: 'Неверный запрос',
    9: 'Слишком много однотипных действий',
    10: 'Произошла внутренняя ошибка сервера',
    14: 'Требуется ввод кода с картинки (Captcha)',
    15: 'Доступ запрещён',
    17: 'Требуется проверка пользователя',
    18: 'Страница удалена или заблокирована',
    100: 'Один из необходимых параметров был не передан или неверен',
    101: 'Неверный API ID приложения',
    113: 'Неверный идентификатор пользователя',
    150: 'Неверный timestamp',
    200: 'Доступ к альбому запрещён',
    201: 'Доступ к аудио запрещён',
    203: 'Доступ к группе запрещён',
    300: 'Альбом переполнен',
    500: 'Действие запрещено, у пользователя нет прав на данное действие',
    600: 'Нет прав на рекламный кабинет',
    603: 'Произошла ошибка при работе с рекламным кабинетом',
}


class VkApiError(Exception):
    """Базовый класс для ошибок vk_api"""
    pass


class AccessDenied(VkApiError):
    """Доступ запрещён"""
    pass


class AuthError(VkApiError):
    """Ошибка аутентификации"""
    pass


class LoginRequired(AuthError):
    """Требуется логин"""
    pass


class PasswordRequired(AuthError):
    """Требуется пароль"""
    pass


class BadPassword(AuthError):
    """Неверный пароль"""
    pass


class AccountBlocked(AuthError):
    """Аккаунт заблокирован"""
    pass


class TwoFactorError(AuthError):
    """Ошибка двухфакторной аутентификации"""
    pass


class TokenExpiredError(AuthError):
    """Токен истёк"""
    pass


class SecurityCheck(AuthError):
    """Требуется проверка безопасности"""

    def __init__(
        self,
        phone_prefix: t.Optional[str] = None,
        phone_postfix: t.Optional[str] = None,
        response=None
    ):
        super().__init__()
        self.phone_prefix = phone_prefix
        self.phone_postfix = phone_postfix
        self.response = response

    def __str__(self) -> str:
        if self.phone_prefix and self.phone_postfix:
            return (
                'Требуется проверка безопасности. '
                'Введите номер: +{} ... {}'.format(
                    self.phone_prefix, self.phone_postfix
                )
            )
        return (
            'Требуется проверка безопасности. '
            'Не удалось определить префикс и постфикс номера. '
            'Пожалуйста, отправьте баг-репорт (response в self.response)'
        )


class ApiError(VkApiError):
    """Ошибка VK API"""

    def __init__(self, vk, method: str, values: dict, raw: bool, error: dict):
        super().__init__()
        self.vk = vk
        self.method = method
        self.values = values
        self.raw = raw
        self.code: int = error['error_code']
        self.error = error
        self.description = VK_ERROR_CODES.get(self.code, 'Неизвестная ошибка')

    def try_method(self):
        """Отправить запрос заново"""
        return self.vk.method(self.method, self.values, raw=self.raw)

    def __str__(self) -> str:
        return '[{}] {} | {}'.format(
            self.error['error_code'],
            self.error['error_msg'],
            self.description
        )

    def __repr__(self) -> str:
        return '<ApiError code={} method={}>'.format(self.code, self.method)


class ApiHttpError(VkApiError):
    """Ошибка HTTP при запросе к API"""

    def __init__(self, vk, method: str, values: dict, raw: bool, response):
        super().__init__()
        self.vk = vk
        self.method = method
        self.values = values
        self.raw = raw
        self.response = response

    def try_method(self):
        """Отправить запрос заново"""
        return self.vk.method(self.method, self.values, raw=self.raw)

    def __str__(self) -> str:
        return 'HTTP ошибка {}: {}'.format(
            self.response.status_code,
            self.response.reason
        )

    def __repr__(self) -> str:
        return '<ApiHttpError status={}>'.format(self.response.status_code)


class Captcha(VkApiError):
    """Требуется ввод капчи"""

    def __init__(
        self,
        vk,
        captcha_sid: t.Union[int, str],
        func: t.Callable,
        args: t.Optional[tuple] = None,
        kwargs: t.Optional[dict] = None,
        url: t.Optional[str] = None
    ):
        super().__init__()
        self.vk = vk
        self.sid = captcha_sid
        self.func = func
        self.args = args or ()
        self.kwargs = kwargs or {}

        self.code = CAPTCHA_ERROR_CODE

        self.key: t.Optional[str] = None
        self.url = url
        self.image: t.Optional[bytes] = None

    def get_url(self) -> str:
        """Получить ссылку на изображение капчи"""
        if not self.url:
            self.url = 'https://api.vk.com/captcha.php?sid={}'.format(self.sid)
        return self.url

    def get_image(self) -> bytes:
        """Получить изображение капчи (jpg)"""
        if not self.image:
            self.image = self.vk.http.get(self.get_url()).content
        return self.image

    def try_again(self, key: t.Optional[str] = None):
        """Отправить запрос заново с ответом капчи

        :param key: ответ капчи
        """
        if key:
            self.key = key
            self.kwargs.update({
                'captcha_sid': self.sid,
                'captcha_key': self.key
            })

        return self.func(*self.args, **self.kwargs)

    def __str__(self) -> str:
        return 'Требуется капча. URL: {}'.format(self.get_url())

    def __repr__(self) -> str:
        return '<Captcha sid={}>'.format(self.sid)


class VkAudioException(Exception):
    """Ошибка при работе с аудио"""
    pass


class VkAudioUrlDecodeError(VkAudioException):
    """Ошибка декодирования URL аудио"""
    pass


class VkToolsException(VkApiError):
    """Ошибка вспомогательных инструментов"""

    def __init__(self, *args, response=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.response = response


class VkRequestsPoolException(Exception):
    """Ошибка пула запросов"""

    def __init__(self, error, *args, **kwargs):
        self.error = error
        super().__init__(*args, **kwargs)


class RateLimitError(VkApiError):
    """Превышен лимит запросов"""
    pass


class NetworkError(VkApiError):
    """Ошибка сети"""
    pass


class ParseError(VkApiError):
    """Ошибка парсинга ответа"""
    pass
