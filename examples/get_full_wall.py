#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Пример получения всех постов со стены пользователя или группы.
Использует метод execute для ускорения (25 запросов за одно обращение).
"""

import vk_api
from vk_api.tools import VkTools


def main():
    vk_session = vk_api.VkApi(token='ваш_токен')
    vk = vk_session.get_api()
    tools = VkTools(vk_session)

    owner_id = -1  # -1 = группа VK, положительное = пользователь

    print(f'Загружаю посты для owner_id={owner_id}...')

    # ─── Способ 1: загрузить всё в память (для небольших стен) ───────────
    result = tools.get_all('wall.get', 100, {'owner_id': owner_id})
    print(f'Всего постов: {result["count"]}')

    # ─── Способ 2: итератор (рекомендуется для больших стен) ─────────────
    print('\nПоследние 10 постов:')
    count = 0
    for post in tools.get_all_iter('wall.get', 100, {'owner_id': owner_id}):
        text = post.get('text', '').strip()
        date = post.get('date', 0)
        print(f"  [{post['id']}] {text[:80]}")
        count += 1
        if count >= 10:
            break

    # ─── Способ 3: медленный (без execute) — например для частных API ────
    print('\nМедленный способ (без execute):')
    slow_result = tools.get_all_slow('wall.get', 100, {'owner_id': owner_id}, limit=5)
    print(f'Получено: {slow_result["count"]} постов')


if __name__ == '__main__':
    main()
