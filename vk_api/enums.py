# -*- coding: utf-8 -*-
"""
:authors: python273, aaxnet
:license: Apache License, Version 2.0, see LICENSE file
:copyright: (c) 2019 python273, 2024 aaxnet
"""

from __future__ import annotations
from enum import IntFlag, auto


class VkUserPermissions(IntFlag):
    """Права доступа пользователя VK API

    `Подробнее: https://dev.vk.com/ru/reference/access-rights`

    Пример использования::

        from vk_api import VkUserPermissions

        # Запросить только нужные права
        scope = VkUserPermissions.MESSAGES | VkUserPermissions.WALL
        vk_session = VkApi(..., scope=scope)

        # Все права (по умолчанию)
        scope = sum(VkUserPermissions)
    """

    #: Уведомления о пользователе
    NOTIFY = 1

    #: Доступ к друзьям
    FRIENDS = 2

    #: Доступ к фотографиям
    PHOTOS = 4

    #: Доступ к аудио
    AUDIO = 8

    #: Доступ к видео
    VIDEO = 16

    #: Доступ к историям
    STORIES = 64

    #: Доступ к страницам
    PAGES = 128

    #: Добавление ссылки на сайт в профиль
    MENU = 256

    #: Управление статусом
    STATUS = 1024

    #: Доступ к заметкам
    NOTES = 2048

    #: Доступ к расширенным методам работы с сообщениями
    MESSAGES = 4096

    #: Доступ к обычным и расширенным методам работы со стеной
    WALL = 8192

    #: Доступ к рекламному кабинету
    ADS = 32768

    #: Доступ к API в любое время (offline)
    OFFLINE = 65536

    #: Доступ к документам
    DOCS = 131072

    #: Доступ к группам пользователя
    GROUPS = 262144

    #: Доступ к оповещениям (уведомлениям) о ответах
    NOTIFICATIONS = 524288

    #: Доступ к статистике
    STATS = 1048576

    #: Доступ к email
    EMAIL = 4194304

    #: Доступ к управлению
    MANAGE = 8388608

    @classmethod
    def get_by_name(cls, name: str) -> 'VkUserPermissions':
        """Получить право по имени

        :param name: название права
        :return: VkUserPermissions
        :raises KeyError: если право не найдено
        """
        return cls[name.upper()]

    @classmethod
    def all_names(cls) -> list:
        """Получить список всех названий прав"""
        return [p.name for p in cls]

    def __str__(self) -> str:
        return str(self.value)
