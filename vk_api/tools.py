# -*- coding: utf-8 -*-
"""
:authors: python273, aaxnet
:license: Apache License, Version 2.0, see LICENSE file
:copyright: (c) 2019 python273, 2024 aaxnet
"""

from __future__ import annotations
import typing as t

from .exceptions import ApiError, VkToolsException
from .execute import VkFunction


class VkTools:
    """Вспомогательные функции для VK API

    :param vk: Объект :class:`VkApi` или :class:`VkApiMethod`

    Пример::

        import vk_api
        from vk_api.tools import VkTools

        vk_session = vk_api.VkApi(token='...')
        vk = vk_session.get_api()
        tools = VkTools(vk_session)

        # Получить все посты стены
        all_posts = tools.get_all('wall.get', 100, {'owner_id': -1})
        print(f'Всего постов: {all_posts[\"count\"]}')
    """

    __slots__ = ('vk',)

    def __init__(self, vk):
        self.vk = vk

    def get_all_iter(
        self,
        method: str,
        max_count: int,
        values: t.Optional[dict] = None,
        key: str = 'items',
        limit: t.Optional[int] = None,
        stop_fn: t.Optional[t.Callable] = None,
        negative_offset: bool = False
    ) -> t.Iterator:
        """Получить все элементы постранично (итератор).

        Используйте этот метод если нужно обрабатывать данные по мере получения,
        без загрузки всего в память. За один запрос к execute получает до
        max_count * 25 элементов.

        :param method: Название метода API (например 'wall.get')
        :param max_count: Максимум элементов за один запрос к этому методу
        :param values: Дополнительные параметры запроса
        :param key: Ключ элементов в ответе (обычно 'items' или 'users')
        :param limit: Ограничение общего количества элементов
        :param stop_fn: Функция остановки — принимает список элементов,
            возвращает True если нужно остановиться
        :param negative_offset: True если offset должен быть отрицательным
        :yields: Элементы ответа

        Пример::

            tools = VkTools(vk_session)
            for post in tools.get_all_iter('wall.get', 100, {'owner_id': -1}):
                print(post['text'])
        """
        values = values.copy() if values else {}
        values['count'] = max_count

        offset = max_count if negative_offset else 0
        items_count = 0
        count = None

        while True:
            response = vk_get_all_items(
                self.vk, method, key, values, count, offset,
                offset_mul=-1 if negative_offset else 1
            )

            if 'execute_errors' in response:
                raise VkToolsException(
                    'Не удалось загрузить элементы: {}'.format(
                        response['execute_errors']
                    ),
                    response=response
                )

            response = response['response']
            items = response['items']
            items_count += len(items)

            for item in items:
                yield item

            if not response['more']:
                break

            if limit and items_count >= limit:
                break

            if stop_fn and stop_fn(items):
                break

            count = response['count']
            offset = response['offset']

    def get_all(
        self,
        method: str,
        max_count: int,
        values: t.Optional[dict] = None,
        key: str = 'items',
        limit: t.Optional[int] = None,
        stop_fn: t.Optional[t.Callable] = None,
        negative_offset: bool = False
    ) -> dict:
        """Получить все элементы в память.

        Загружает все элементы сразу. Используйте :meth:`get_all_iter`
        если не нужны все данные сразу (экономия памяти).

        :param method: Название метода API
        :param max_count: Максимум элементов за один запрос
        :param values: Параметры запроса
        :param key: Ключ элементов в ответе
        :param limit: Ограничение количества
        :param stop_fn: Функция остановки
        :param negative_offset: Отрицательный offset
        :return: Словарь {'count': N, key: [...]}

        Пример::

            result = tools.get_all('friends.get', 200, {'user_id': 1})
            print(f'Друзей: {result[\"count\"]}')
        """
        items = list(self.get_all_iter(
            method, max_count, values, key, limit, stop_fn, negative_offset
        ))
        return {'count': len(items), key: items}

    def get_all_slow_iter(
        self,
        method: str,
        max_count: int,
        values: t.Optional[dict] = None,
        key: str = 'items',
        limit: t.Optional[int] = None,
        stop_fn: t.Optional[t.Callable] = None,
        negative_offset: bool = False
    ) -> t.Iterator:
        """Получить все элементы без использования execute (итератор).

        Медленнее, чем :meth:`get_all_iter`, но не использует метод execute.
        Подходит для API-методов, не поддерживаемых через execute.

        :param method: Название метода API
        :param max_count: Максимум элементов за один запрос
        :param values: Параметры запроса
        :param key: Ключ элементов в ответе
        :param limit: Ограничение количества
        :param stop_fn: Функция остановки
        :param negative_offset: Отрицательный offset
        :yields: Элементы ответа
        """
        values = values.copy() if values else {}
        values['count'] = max_count

        offset_mul = -1 if negative_offset else 1
        offset = max_count if negative_offset else 0
        count = None
        items_count = 0

        while count is None or offset < count:
            values['offset'] = offset * offset_mul
            response = self.vk.method(method, values)

            new_count = response['count']
            count_diff = (new_count - count) if count is not None else 0

            if count_diff < 0:
                offset += count_diff
                count = new_count
                continue

            response_items = response[key]
            items = response_items[count_diff:]
            items_count += len(items)

            for item in items:
                yield item

            if len(response_items) < max_count - count_diff:
                break

            if limit and items_count >= limit:
                break

            if stop_fn and stop_fn(items):
                break

            offset += max_count
            count = new_count

    def get_all_slow(
        self,
        method: str,
        max_count: int,
        values: t.Optional[dict] = None,
        key: str = 'items',
        limit: t.Optional[int] = None,
        stop_fn: t.Optional[t.Callable] = None,
        negative_offset: bool = False
    ) -> dict:
        """Получить все элементы в память (без execute).

        :return: Словарь {'count': N, key: [...]}
        """
        items = list(self.get_all_slow_iter(
            method, max_count, values, key, limit, stop_fn, negative_offset
        ))
        return {'count': len(items), key: items}

    def get_all_with_count(
        self,
        method: str,
        max_count: int,
        values: t.Optional[dict] = None,
        key: str = 'items',
    ) -> t.Tuple[int, list]:
        """Удобная версия get_all, возвращающая кортеж (count, items)

        :return: (общее_количество, список_элементов)
        """
        result = self.get_all(method, max_count, values, key)
        return result['count'], result[key]


# VKScript функция для быстрого получения всех элементов через execute
vk_get_all_items = VkFunction(
    args=('method', 'key', 'values', 'count', 'offset', 'offset_mul'),
    clean_args=('method', 'key', 'offset', 'offset_mul'),
    return_raw=True,
    code='''
    var params = %(values)s,
        calls = 0,
        items = [],
        count = %(count)s,
        offset = %(offset)s,
        ri;

    while(calls < 25) {
        calls = calls + 1;

        params.offset = offset * %(offset_mul)s;
        var response = API.%(method)s(params),
            new_count = response.count,
            count_diff = (count == null ? 0 : new_count - count);
        if (!response) {
            return {"_error": 1};
        }

        if (count_diff < 0) {
            offset = offset + count_diff;
        } else {
            ri = response.%(key)s;
            items = items + ri.slice(count_diff);
            offset = offset + params.count + count_diff;
            if (ri.length < params.count) {
                calls = 99;
            }
        }

        count = new_count;

        if (count != null && offset >= count) {
            calls = 99;
        }
    };

    return {
        count: count,
        items: items,
        offset: offset,
        more: calls != 99
    };
''')
