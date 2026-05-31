# -*- coding: utf-8 -*-
"""
:authors: python273, aaxnet
:license: Apache License, Version 2.0, see LICENSE file
:copyright: (c) 2019 python273, 2024 aaxnet
"""

from __future__ import annotations
from __future__ import print_function

import logging
import random
import re
import typing as t
from functools import wraps
from http.cookiejar import Cookie

try:
    import simplejson as json
except ImportError:
    import json

logger = logging.getLogger('vk_api.utils')


def search_re(reg: re.Pattern, string: str) -> t.Optional[str]:
    """Поиск по регулярному выражению

    :param reg: скомпилированное регулярное выражение
    :param string: строка для поиска
    :return: первая группа или None
    """
    s = reg.search(string)
    if s:
        groups = s.groups()
        return groups[0] if groups else None
    return None


def clear_string(s: t.Optional[str]) -> t.Optional[str]:
    """Очистить строку от лишних символов

    :param s: строка
    :return: очищенная строка или None
    """
    if s:
        return s.strip().replace('&nbsp;', '')
    return None


def get_random_id() -> int:
    """Получить случайный int32 (signed)

    :return: случайное число
    """
    return random.getrandbits(31) * random.choice([-1, 1])


def code_from_number(
    prefix: str,
    postfix: str,
    number: str
) -> t.Optional[str]:
    """Извлечь средние цифры номера телефона для проверки безопасности

    :param prefix: префикс номера (начало)
    :param postfix: постфикс номера (конец)
    :param number: полный номер телефона
    :return: средняя часть номера или None
    """
    prefix_len = len(prefix)
    postfix_len = len(postfix)

    if number.startswith('+'):
        number = number[1:]

    if (prefix_len + postfix_len) >= len(number):
        return None

    if number[:prefix_len] != prefix:
        return None

    if number[-postfix_len:] != postfix:
        return None

    return number[prefix_len:-postfix_len]


def sjson_dumps(*args, **kwargs) -> str:
    """Сериализация в JSON без пробелов и без escape ascii

    :return: JSON строка
    """
    kwargs['ensure_ascii'] = False
    kwargs['separators'] = (',', ':')
    return json.dumps(*args, **kwargs)


def sjson_loads(s: str) -> t.Any:
    """Десериализация JSON с обработкой ошибок

    :param s: JSON строка
    :return: десериализованный объект
    """
    try:
        return json.loads(s)
    except (json.JSONDecodeError, ValueError) as e:
        logger.debug('Ошибка парсинга JSON: %s', e)
        raise


# Аргументы объекта Cookie
HTTP_COOKIE_ARGS = [
    'version', 'name', 'value',
    'port', 'port_specified',
    'domain', 'domain_specified',
    'domain_initial_dot',
    'path', 'path_specified',
    'secure', 'expires', 'discard', 'comment', 'comment_url', 'rest', 'rfc2109'
]


def cookie_to_dict(cookie: Cookie) -> dict:
    """Конвертировать Cookie объект в словарь

    :param cookie: объект Cookie
    :return: словарь с параметрами cookie
    """
    cookie_dict = {
        k: v for k, v in cookie.__dict__.items()
        if k in HTTP_COOKIE_ARGS
    }
    cookie_dict['rest'] = cookie._rest
    cookie_dict['expires'] = None
    return cookie_dict


def cookie_from_dict(d: dict) -> Cookie:
    """Создать Cookie объект из словаря

    :param d: словарь с параметрами cookie
    :return: объект Cookie
    """
    return Cookie(**d)


def cookies_to_list(cookies) -> list:
    """Конвертировать CookieJar в список словарей

    :param cookies: CookieJar объект
    :return: список словарей с параметрами cookie
    """
    return [cookie_to_dict(cookie) for cookie in cookies]


def set_cookies_from_list(cookie_jar, cookies: list) -> None:
    """Установить cookies из списка словарей

    :param cookie_jar: CookieJar объект
    :param cookies: список словарей с параметрами cookie
    """
    for cookie in cookies:
        try:
            cookie_jar.set_cookie(cookie_from_dict(cookie))
        except Exception as e:
            logger.debug('Ошибка установки cookie: %s', e)


def retry(
    max_retries: int = 3,
    exceptions: tuple = (Exception,),
    delay: float = 1.0
) -> t.Callable:
    """Декоратор для повторных попыток при исключениях

    :param max_retries: максимальное количество попыток
    :param exceptions: кортеж исключений для перехвата
    :param delay: задержка между попытками в секундах
    :return: декоратор
    """
    import time

    def decorator(func: t.Callable) -> t.Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt < max_retries - 1:
                        logger.warning(
                            'Попытка %d/%d не удалась: %s. Повтор через %.1f сек...',
                            attempt + 1, max_retries, e, delay
                        )
                        time.sleep(delay)
            raise last_exc
        return wrapper
    return decorator


def chunks(lst: list, n: int) -> t.Iterator[list]:
    """Разбить список на части по n элементов

    :param lst: список
    :param n: размер части
    :yields: части списка
    """
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def enable_debug_mode(vk_session, print_content: bool = False) -> None:
    """Включить режим отладки

    :param vk_session: объект VkApi
    :param print_content: печатать содержимое ответов
    """
    import sys
    import time
    import requests

    from . import __version__

    try:
        pypi_version = requests.get(
            'https://pypi.org/pypi/vk_api/json',
            timeout=5
        ).json()['info']['version']

        if __version__ != pypi_version:
            print('\n' + '=' * 50)
            print('⚠️  МОДУЛЬ НЕ ОБНОВЛЁН!')
            print('=' * 50)
            print(f'Установленная версия vk_api: {__version__}')
            print(f'Версия на PyPI: {pypi_version}')
            print('Запустите: pip install --upgrade vk_api')
            print('=' * 50 + '\n')
    except Exception:
        pass

    class DebugHTTPAdapter(requests.adapters.HTTPAdapter):
        def send(self, request, **kwargs):
            start = time.time()
            response = super().send(request, **kwargs)
            elapsed = time.time() - start

            body = request.body
            if body and len(str(body)) > 1024:
                body = str(body)[:1024] + '[ОБРЕЗАНО]'

            print(
                '[{:.3f}s] {} {} | Headers: {} | Body: {} | Status: {} | History: {}'.format(
                    elapsed,
                    request.method,
                    request.url,
                    dict(request.headers),
                    repr(body),
                    response.status_code,
                    response.history
                )
            )

            if print_content:
                try:
                    print('Response:', response.json())
                except Exception:
                    print('Response:', response.text[:500])

            return response

    vk_session.http.mount('http://', DebugHTTPAdapter())
    vk_session.http.mount('https://', DebugHTTPAdapter())

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        '[%(asctime)s] %(name)s %(levelname)s: %(message)s',
        datefmt='%H:%M:%S'
    ))

    vk_session.logger.setLevel(logging.DEBUG)
    vk_session.logger.addHandler(handler)


def truncate_string(s: str, max_len: int = 100) -> str:
    """Обрезать строку до максимальной длины

    :param s: строка
    :param max_len: максимальная длина
    :return: обрезанная строка
    """
    if len(s) > max_len:
        return s[:max_len - 3] + '...'
    return s
