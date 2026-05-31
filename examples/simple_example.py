#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Простой пример использования vk_api

Заменить 'ваш_токен' на реальный токен из настроек приложения VK.
Получить токен: https://vkhost.github.io/
"""

import vk_api
from vk_api.exceptions import ApiError, AuthError


def main():
    # ─── Способ 1: через access_token (рекомендуется) ─────────────────────
    vk_session = vk_api.VkApi(token='ваш_токен')
    vk = vk_session.get_api()

    # Получить информацию о пользователе
    users = vk.users.get(user_ids='1', fields='photo_200,city')
    user = users[0]
    print(f"Имя: {user['first_name']} {user['last_name']}")
    city = user.get('city', {}).get('title', 'не указан')
    print(f"Город: {city}")

    # Получить 5 последних постов стены
    wall = vk.wall.get(owner_id=1, count=5)
    print(f"\nПоследние посты ({wall['count']} всего):")
    for post in wall['items']:
        text = post.get('text', '').strip()
        print(f"  [{post['id']}] {text[:80]}...")

    # Поиск пользователей
    search_result = vk.users.search(q='Иван', count=3)
    print(f"\nРезультаты поиска:")
    for u in search_result['items']:
        print(f"  {u['first_name']} {u['last_name']} (id{u['id']})")


    # ─── Способ 2: через логин/пароль ────────────────────────────────────
    # vk_session = vk_api.VkApi('+71234567890', 'пароль')
    # vk_session.auth()
    # vk = vk_session.get_api()


    # ─── Способ 3: токен группы ───────────────────────────────────────────
    # vk_session = vk_api.VkApiGroup(token='токен_группы')
    # vk = vk_session.get_api()


    # ─── Пример обработки ошибок ─────────────────────────────────────────
    try:
        result = vk.wall.post(
            owner_id=123456789,
            message='Тестовый пост'
        )
        print(f"\nПост опубликован: id{result['post_id']}")
    except ApiError as e:
        print(f"\nОшибка API [{e.code}]: {e}")
    except AuthError as e:
        print(f"\nОшибка авторизации: {e}")


    # ─── Контекстный менеджер ────────────────────────────────────────────
    with vk_api.VkApi(token='ваш_токен') as session:
        api = session.get_api()
        print("\nРаботаем в контекстном менеджере")
        # http-сессия закроется автоматически


if __name__ == '__main__':
    main()
