# -*- coding: utf-8 -*-
"""
:authors: python273, aaxnet
:license: Apache License, Version 2.0, see LICENSE file
:copyright: (c) 2019 python273, 2024 aaxnet
"""

from __future__ import annotations

import json
import logging
import random
import re
import threading
import time
import typing as t
import urllib.parse
from contextlib import contextmanager
from hashlib import md5

import requests

import jconfig
from .enums import VkUserPermissions
from .exceptions import (
    CAPTCHA_ERROR_CODE, CONFIRMATION_ERROR_CODE, HTTP_ERROR_CODE,
    NEED_VALIDATION_CODE, TOO_MANY_RPS_CODE, TWOFACTOR_CODE,
    AccountBlocked, ApiError, ApiHttpError, AuthError, BadPassword,
    Captcha, LoginRequired, NetworkError, ParseError, PasswordRequired,
    SecurityCheck, TwoFactorError
)
from .utils import (
    clear_string, code_from_number, cookies_to_list,
    search_re, set_cookies_from_list, get_random_id
)

# Регулярные выражения для парсинга страниц VK
RE_LOGIN_TO = re.compile(r'"to":"(.*?)"')
RE_LOGIN_IP_H = re.compile(r'name="ip_h" value="([a-z0-9]+)"')
RE_LOGIN_LG_H = re.compile(r'name="lg_h" value="([a-z0-9]+)"')
RE_LOGIN_LG_DOMAIN_H = re.compile(r'name="lg_domain_h" value="([a-z0-9]+)"')

RE_CAPTCHAID = re.compile(r"onLoginCaptcha\('(\d+)'")
RE_NUMBER_HASH = re.compile(r"al_page: '3', hash: '([a-z0-9]+)'")
RE_AUTH_HASH = re.compile(r"Authcheck\.init\('([a-z_0-9]+)'")
RE_TOKEN_URL = re.compile(r'location\.href = "(.*?)"\+addr;')
RE_AUTH_TOKEN_URL = re.compile(r'window\.init = ({.*?});')

RE_PHONE_PREFIX = re.compile(r'label ta_r">\+(.*?)<')
RE_PHONE_POSTFIX = re.compile(r'phone_postfix">.*?(\d+).*?<')

# Актуальный User-Agent
DEFAULT_USERAGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/120.0.0.0 Safari/537.36'
)

DEFAULT_USER_SCOPE = sum(VkUserPermissions)

# Актуальная версия API
DEFAULT_API_VERSION = '5.199'


def get_unknown_exc_str(s: str) -> str:
    return (
        f'Неизвестная ошибка ({s}). Пожалуйста, отправьте баг-репорт: '
        'https://github.com/aaxnet/vk_api/issues'
    )


class VkApi:
    """Python клиент для VK API

    :param login: Логин ВКонтакте (номер телефона или email)
    :type login: str

    :param password: Пароль ВКонтакте
    :type password: str

    :param token: access_token для авторизации без логина/пароля
    :type token: str

    :param auth_handler: Обработчик двухфакторной аутентификации.
        Должен возвращать (код, запомнить_устройство)
    :type auth_handler: callable

    :param captcha_handler: Обработчик капчи
    :type captcha_handler: callable

    :param config: Класс для хранения настроек
    :type config: jconfig.base.BaseConfig

    :param config_filename: Путь к файлу конфигурации
    :type config_filename: str

    :param api_version: Версия VK API (по умолчанию 5.199)
    :type api_version: str

    :param app_id: ID приложения
    :type app_id: int

    :param scope: Запрашиваемые права
    :type scope: int or str

    :param client_secret: Секретный ключ приложения
    :type client_secret: str

    :param session: Кастомная HTTP-сессия
    :type session: requests.Session

    :param timeout: Таймаут HTTP-запросов в секундах (по умолчанию 30)
    :type timeout: int or float

    :param max_retries: Максимальное количество попыток при ошибке сети
    :type max_retries: int

    Пример использования::

        import vk_api

        vk_session = vk_api.VkApi(token='ваш_токен')
        vk = vk_session.get_api()
        print(vk.users.get(user_ids='1'))
    """

    # Задержка между запросами (~3 запроса в секунду для пользователей)
    RPS_DELAY = 0.34

    def __init__(
        self,
        login: t.Optional[str] = None,
        password: t.Optional[str] = None,
        token: t.Optional[str] = None,
        auth_handler: t.Optional[t.Callable] = None,
        captcha_handler: t.Optional[t.Callable] = None,
        config=jconfig.Config,
        config_filename: str = 'vk_config.v2.json',
        api_version: str = DEFAULT_API_VERSION,
        app_id: int = 6222115,
        scope: t.Union[int, str] = DEFAULT_USER_SCOPE,
        client_secret: t.Optional[str] = None,
        session: t.Optional[requests.Session] = None,
        timeout: t.Union[int, float] = 30,
        max_retries: int = 3,
    ):
        self.login = login
        self.password = password

        self.token: t.Optional[dict] = {'access_token': token} if token else None

        self.api_version = api_version
        self.app_id = app_id
        self.scope = scope
        self.client_secret = client_secret
        self.timeout = timeout
        self.max_retries = max_retries

        self.storage = config(self.login, filename=config_filename)

        self.http = session or requests.Session()
        if not session:
            self.http.headers['User-Agent'] = DEFAULT_USERAGENT

        self.last_request = 0.0

        self.error_handlers: dict = {
            NEED_VALIDATION_CODE: self.need_validation_handler,
            CAPTCHA_ERROR_CODE: captcha_handler or self.captcha_handler,
            TOO_MANY_RPS_CODE: self.too_many_rps_handler,
            TWOFACTOR_CODE: auth_handler or self.auth_handler,
        }

        self.lock = threading.Lock()
        self.logger = logging.getLogger('vk_api')

    @property
    def _sid(self) -> t.Optional[str]:
        """Получить текущий session ID"""
        return (
            self.http.cookies.get('remixsid', domain='.vk.com') or
            self.http.cookies.get('remixsid6', domain='.vk.com') or
            self.http.cookies.get('remixsid', domain='.vk.ru') or
            self.http.cookies.get('remixsid6', domain='.vk.ru')
        )

    @property
    def access_token(self) -> t.Optional[str]:
        """Получить текущий access_token"""
        if self.token:
            return self.token.get('access_token')
        return None

    def auth(self, reauth: bool = False, token_only: bool = False) -> None:
        """Аутентификация

        :param reauth: Принудительная повторная авторизация
        :param token_only: Получить только access_token (без cookies)

        При token_only=True:
          - Если токен валиден — авторизация сразу завершается
          - Если нет, но есть cookies — получает токен через API
          - Если нет cookies, но есть пароль — полная авторизация

        При token_only=False (по умолчанию):
          - Сначала проверяет cookies
          - Если невалидны — авторизуется через login/password
        """
        if not self.login:
            raise LoginRequired('Для аутентификации необходим логин')

        self.logger.info('Аутентификация для: %s', self.login)

        set_cookies_from_list(
            self.http.cookies,
            self.storage.setdefault('cookies', [])
        )

        self.token = (
            self.storage
            .setdefault('token', {})
            .setdefault('app' + str(self.app_id), {})
            .get('scope_' + str(self.scope))
        )

        if token_only:
            self._auth_token(reauth=reauth)
        else:
            self._auth_cookies(reauth=reauth)

    def _auth_cookies(self, reauth: bool = False) -> None:
        if reauth:
            self.logger.info('Принудительная авторизация')
            self.storage.clear_section()
            self._vk_login()
            self._api_login()
            return

        if not self.check_sid():
            self.logger.info('remixsid недействителен: %s', self._sid)
            self._vk_login()
        else:
            self._pass_security_check()

        if not self._check_token():
            self.logger.info('access_token недействителен: %s', self.token)
            self._api_login()
        else:
            self.logger.info('access_token действителен')

    def _auth_token(self, reauth: bool = False) -> None:
        if not reauth and self._check_token():
            self.logger.info('access_token из конфига действителен')
            return

        if reauth:
            self.logger.info('Принудительное получение токена')

        if self.check_sid():
            self._pass_security_check()
            self._api_login()
        elif self.password:
            self._vk_login()
            self._api_login()

    def _vk_login(
        self,
        captcha_sid: t.Optional[t.Union[int, str]] = None,
        captcha_key: t.Optional[str] = None
    ) -> None:
        """Авторизация ВКонтакте (получение cookies remixsid)"""

        self.logger.info('Вход в аккаунт...')

        if not self.password:
            raise PasswordRequired('Для входа необходим пароль')

        self.http.cookies.clear()

        try:
            response = self.http.get('https://vk.com/login', timeout=self.timeout)
        except requests.RequestException as e:
            raise NetworkError(f'Ошибка подключения к VK: {e}') from e

        # Обработка 429
        if response.url.startswith('https://vk.com/429.html?'):
            hash429_md5 = md5(self.http.cookies['hash429'].encode('ascii')).hexdigest()
            self.http.cookies.pop('hash429')
            response = self.http.get(
                f'{response.url}&key={hash429_md5}',
                timeout=self.timeout
            )

        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://vk.com/',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://vk.com',
        }

        values = {
            'act': 'login',
            'role': 'al_frame',
            'expire': '',
            'to': search_re(RE_LOGIN_TO, response.text) or '',
            'recaptcha': '',
            'captcha_sid': captcha_sid or '',
            'captcha_key': captcha_key or '',
            '_origin': 'https://vk.com',
            'utf8': '1',
            'ip_h': search_re(RE_LOGIN_IP_H, response.text) or '',
            'lg_h': search_re(RE_LOGIN_LG_H, response.text) or '',
            'lg_domain_h': search_re(RE_LOGIN_LG_DOMAIN_H, response.text) or '',
            'ul': '',
            'email': self.login,
            'pass': self.password,
        }

        if captcha_sid and captcha_key:
            self.logger.info('Использую капчу: %s: %s', captcha_sid, captcha_key)

        try:
            response = self.http.post(
                'https://login.vk.com/?act=login',
                data=values,
                headers=headers,
                timeout=self.timeout
            )
        except requests.RequestException as e:
            raise NetworkError(f'Ошибка при авторизации: {e}') from e

        if 'onLoginCaptcha(' in response.text:
            self.logger.info('Требуется капча')
            captcha_sid = search_re(RE_CAPTCHAID, response.text)
            captcha = Captcha(self, captcha_sid, self._vk_login)
            return self.error_handlers[CAPTCHA_ERROR_CODE](captcha)

        if 'onLoginReCaptcha(' in response.text:
            self.logger.info('Требуется reCaptcha')
            captcha_sid = str(random.random())[2:16]
            captcha = Captcha(self, captcha_sid, self._vk_login)
            return self.error_handlers[CAPTCHA_ERROR_CODE](captcha)

        if 'onLoginFailed(4' in response.text:
            raise BadPassword('Неверный пароль')

        if 'act=authcheck' in response.text:
            self.logger.info('Требуется двухфакторная аутентификация')
            response = self.http.get(
                'https://vk.com/login?act=authcheck',
                timeout=self.timeout
            )
            self._pass_twofactor(response)

        if self._sid:
            self.logger.info('Получен remixsid')
            self.storage.cookies = cookies_to_list(self.http.cookies)
            self.storage.save()
        else:
            raise AuthError(get_unknown_exc_str('AUTH; нет sid'))

        response = self._pass_security_check(response)

        if 'act=blocked' in response.url:
            raise AccountBlocked('Аккаунт заблокирован')

    def _pass_twofactor(
        self,
        auth_response,
        captcha_sid: t.Optional[str] = None,
        captcha_key: t.Optional[str] = None
    ):
        """Двухфакторная аутентификация"""

        auth_hash = search_re(RE_AUTH_HASH, auth_response.text)

        if not auth_hash:
            raise TwoFactorError(get_unknown_exc_str('2FA; нет хэша'))

        code, remember_device = self.error_handlers[TWOFACTOR_CODE]()

        values: dict = {
            'al': '1',
            'code': code,
            'hash': auth_hash,
            'remember': int(remember_device),
        }

        if captcha_sid and captcha_key:
            self.logger.info('Использую капчу: %s: %s', captcha_sid, captcha_key)
            values['captcha_sid'] = captcha_sid
            values['captcha_key'] = captcha_key

        response = self.http.post(
            'https://vk.com/al_login.php?act=a_authcheck_code',
            values,
            timeout=self.timeout
        )
        data = json.loads(response.text.lstrip('<!--'))
        status = data['payload'][0]

        if status == '4':  # OK
            path = json.loads(data['payload'][1][0])
            return self.http.get(path, timeout=self.timeout)

        elif status in [0, '8']:  # Неверный код
            self.logger.warning('Неверный код 2FA, повторная попытка...')
            return self._pass_twofactor(auth_response)

        elif status == '2':
            if data['payload'][1][1] != 2:
                self.logger.info('Требуется капча для 2FA')
                captcha_sid = data['payload'][1][0][1:-1]
                captcha = Captcha(
                    self, captcha_sid, self._pass_twofactor, (auth_response,)
                )
                return self.error_handlers[CAPTCHA_ERROR_CODE](captcha)
            raise TwoFactorError('Требуется reCaptcha')

        raise TwoFactorError(get_unknown_exc_str('2FA; неизвестный статус'))

    def _pass_security_check(self, response=None):
        """Пройти проверку безопасности (запрос номера телефона)"""

        self.logger.info('Проверка на запрос безопасности...')

        if response is None:
            response = self.http.get(
                'https://vk.com/settings',
                timeout=self.timeout
            )

        if 'security_check' not in response.url:
            self.logger.info('Проверка безопасности не требуется')
            return response

        phone_prefix = clear_string(search_re(RE_PHONE_PREFIX, response.text))
        phone_postfix = clear_string(search_re(RE_PHONE_POSTFIX, response.text))

        code = None
        if self.login and phone_prefix and phone_postfix:
            code = code_from_number(phone_prefix, phone_postfix, self.login)

        if code:
            number_hash = search_re(RE_NUMBER_HASH, response.text)

            values = {
                'act': 'security_check',
                'al': '1',
                'al_page': '3',
                'code': code,
                'hash': number_hash,
                'to': '',
            }

            response = self.http.post(
                'https://vk.com/login.php',
                values,
                timeout=self.timeout
            )

            if response.text.split('<!>')[4] == '4':
                return response

        if phone_prefix and phone_postfix:
            raise SecurityCheck(phone_prefix, phone_postfix)

        raise SecurityCheck(response=response)

    def check_sid(self) -> bool:
        """Проверить валидность cookies remixsid

        :return: True если cookies валидны
        """
        self.logger.info('Проверка remixsid...')

        if not self._sid:
            self.logger.info('Нет remixsid')
            return False

        feed_url = 'https://vk.com/feed.php'
        try:
            response = self.http.get(feed_url, timeout=self.timeout)
        except requests.RequestException:
            return False

        if response.url != feed_url:
            self.logger.info('remixsid недействителен')
            return False

        self.logger.info('remixsid действителен')
        return True

    def _api_login(self) -> None:
        """Получение access_token через Desktop-приложение"""

        if not self._sid:
            raise AuthError('Ошибка API авторизации (нет remixsid)')

        if not self.http.cookies.get('p', domain='.login.vk.com'):
            raise AuthError('Ошибка API авторизации (нет login cookies)')

        response = self.http.get(
            'https://oauth.vk.com/authorize',
            params={
                'client_id': self.app_id,
                'scope': self.scope,
                'response_type': 'token',
            },
            timeout=self.timeout
        )

        if 'act=blocked' in response.url:
            raise AccountBlocked('Аккаунт заблокирован')

        if 'access_token' not in response.url:
            url = search_re(RE_TOKEN_URL, response.text)

            if url:
                response = self.http.get(url, timeout=self.timeout)
            elif 'redirect_uri' in response.url:
                response = self.http.get(response.url, timeout=self.timeout)
                auth_json = json.loads(search_re(RE_AUTH_TOKEN_URL, response.text))
                return_auth_hash = auth_json['data']['hash']['return_auth']

                response = self.http.post(
                    'https://login.vk.com/?act=connect_internal',
                    {
                        'uuid': '',
                        'service_group': '',
                        'return_auth_hash': return_auth_hash,
                        'version': 1,
                        'app_id': self.app_id,
                    },
                    headers={'Origin': 'https://id.vk.com'},
                    timeout=self.timeout
                )
                connect_data = response.json()

                if connect_data['type'] != 'okay':
                    raise AuthError('Неизвестная ошибка API авторизации')

                auth_token = connect_data['data']['access_token']

                response = self.http.post(
                    'https://api.vk.com/method/auth.getOauthToken',
                    {
                        'hash': return_auth_hash,
                        'app_id': self.app_id,
                        'client_id': self.app_id,
                        'scope': self.scope,
                        'access_token': auth_token,
                        'is_seamless_auth': 1,
                        'v': '5.207',
                    },
                    timeout=self.timeout
                )

                self.token = response.json()['response']
                self._save_token()
                self.logger.info('Токен успешно получен')
                return

        if 'access_token' in response.url:
            parsed_url = urllib.parse.urlparse(response.url)
            parsed_query = urllib.parse.parse_qs(parsed_url.query)

            if 'authorize_url' in parsed_query:
                url = parsed_query['authorize_url'][0]
                if url.startswith('https%3A'):
                    url = urllib.parse.unquote(url)
                parsed_url = urllib.parse.urlparse(url)

            parsed_query = urllib.parse.parse_qs(parsed_url.fragment)
            token = {k: v[0] for k, v in parsed_query.items()}

            if not isinstance(token.get('access_token'), str):
                raise AuthError(get_unknown_exc_str('API AUTH; нет access_token'))

            self.token = token
            self._save_token()
            self.logger.info('Токен успешно получен')

        elif 'oauth.vk.com/error' in response.url:
            error_data = response.json()
            error_text = error_data.get('error_description')

            if error_text and '@vk.com' in error_text:
                error_text = error_data.get('error')

            raise AuthError(f'Ошибка API авторизации: {error_text}')

        else:
            raise AuthError('Неизвестная ошибка API авторизации')

    def _save_token(self) -> None:
        """Сохранить токен в конфиг"""
        (
            self.storage
            .setdefault('token', {})
            .setdefault('app' + str(self.app_id), {})
        )['scope_' + str(self.scope)] = self.token
        self.storage.save()

    def server_auth(self) -> None:
        """Серверная авторизация (Client Credentials Flow)"""
        values = {
            'client_id': self.app_id,
            'client_secret': self.client_secret,
            'v': self.api_version,
            'grant_type': 'client_credentials',
        }

        response = self.http.post(
            'https://oauth.vk.com/access_token',
            values,
            timeout=self.timeout
        ).json()

        if 'error' in response:
            raise AuthError(response['error_description'])

        self.token = response

    def code_auth(self, code: str, redirect_url: str) -> dict:
        """Получить access_token из кода авторизации

        :param code: код авторизации
        :param redirect_url: redirect URI
        :return: данные токена
        """
        values = {
            'client_id': self.app_id,
            'client_secret': self.client_secret,
            'v': self.api_version,
            'redirect_uri': redirect_url,
            'code': code,
        }

        response = self.http.post(
            'https://oauth.vk.com/access_token',
            values,
            timeout=self.timeout
        ).json()

        if 'error' in response:
            raise AuthError(response['error_description'])

        self.token = response
        return response

    def _check_token(self) -> bool:
        """Проверить валидность access_token"""
        if self.token:
            try:
                self.method('stats.trackVisitor')
                return True
            except ApiError:
                return False
        return False

    def captcha_handler(self, captcha: Captcha):
        """Обработчик капчи по умолчанию — поднимает исключение

        :param captcha: объект Captcha
        """
        raise captcha

    def need_validation_handler(self, error):
        """Обработчик проверки безопасности при запросе API"""
        pass

    def http_handler(self, error: ApiHttpError):
        """Обработчик HTTP ошибок"""
        pass

    def too_many_rps_handler(self, error: ApiError):
        """Обработчик ошибки 'Слишком много запросов'.
        Ждёт 0.5 секунды и повторяет запрос.
        """
        self.logger.warning('Слишком много запросов! Пауза 0.5 сек...')
        time.sleep(0.5)
        return error.try_method()

    def auth_handler(self) -> tuple:
        """Обработчик двухфакторной аутентификации по умолчанию"""
        raise AuthError('Не установлен обработчик двухфакторной аутентификации')

    def get_api(self) -> 'VkApiMethod':
        """Получить объект для вызова методов API

        :return: VkApiMethod

        Пример::

            vk = vk_session.get_api()
            vk.wall.post(message='Привет мир!')
            vk.users.get(user_ids=['durov', 'id1'])
        """
        return VkApiMethod(self)

    def method(
        self,
        method: str,
        values: t.Optional[dict] = None,
        captcha_sid: t.Optional[t.Union[int, str]] = None,
        captcha_key: t.Optional[str] = None,
        raw: bool = False
    ) -> t.Any:
        """Вызов метода VK API

        :param method: название метода (например 'wall.post')
        :param values: параметры запроса
        :param captcha_sid: ID капчи
        :param captcha_key: ответ на капчу
        :param raw: при False возвращает response['response'],
                    при True возвращает полный ответ (нужно для execute)
        :return: ответ API

        :raises ApiError: при ошибке API
        :raises ApiHttpError: при HTTP ошибке
        :raises NetworkError: при ошибке соединения
        """
        values = values.copy() if values else {}

        if 'v' not in values:
            values['v'] = self.api_version

        if self.token:
            values['access_token'] = self.token['access_token']

        if captcha_sid and captcha_key:
            values['captcha_sid'] = captcha_sid
            values['captcha_key'] = captcha_key

        with self.lock:
            # Ограничение частоты запросов
            delay = self.RPS_DELAY - (time.time() - self.last_request)
            if delay > 0:
                time.sleep(delay)

            try:
                response = self.http.post(
                    'https://api.vk.com/method/' + method,
                    values,
                    headers={'Cookie': ''},
                    timeout=self.timeout
                )
            except requests.RequestException as e:
                raise NetworkError(f'Ошибка сети при вызове {method}: {e}') from e

            self.last_request = time.time()

        if not response.ok:
            error = ApiHttpError(self, method, values, raw, response)
            result = self.http_handler(error)
            if result is not None:
                return result
            raise error

        try:
            response = response.json()
        except Exception as e:
            raise ParseError(f'Ошибка парсинга ответа API: {e}') from e

        if 'error' in response:
            error = ApiError(self, method, values, raw, response['error'])

            if error.code in self.error_handlers:
                if error.code == CAPTCHA_ERROR_CODE:
                    error = Captcha(
                        self,
                        error.error['captcha_sid'],
                        self.method,
                        (method,),
                        {'values': values, 'raw': raw},
                        error.error['captcha_img']
                    )

                result = self.error_handlers[error.code](error)
                if result is not None:
                    return result

            raise error

        return response if raw else response['response']

    @contextmanager
    def no_rps_limit(self):
        """Контекстный менеджер для временного отключения RPS лимита.

        Использование::

            with vk_session.no_rps_limit():
                # быстрые запросы без задержки
                result = vk.users.get(user_ids='1')
        """
        old_delay = self.RPS_DELAY
        self.RPS_DELAY = 0
        try:
            yield self
        finally:
            self.RPS_DELAY = old_delay

    def __repr__(self) -> str:
        return '<VkApi login={} token={}>'.format(
            self.login,
            bool(self.token)
        )

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.http.close()


class VkApiGroup(VkApi):
    """Авторизация с токеном группы.

    Увеличивает допустимую частоту запросов с 3 до 20 в секунду.

    Пример::

        vk_session = vk_api.VkApiGroup(token='токен_группы')
        vk = vk_session.get_api()
        vk.messages.send(peer_id=123456, message='Привет!', random_id=0)
    """
    # 20 запросов в секунду для групп
    RPS_DELAY = 1 / 20.0


class VkApiMethod:
    """Прокси-объект для вызова методов API

    Позволяет обращаться к методам через точечную нотацию:

    >>> vk = VkApiMethod(vk_session)
    >>> vk.wall.post(message='Привет!')
    >>> vk.users.get(user_ids='1')
    >>> vk.wall.getById(posts='...')  # camelCase
    >>> vk.wall.get_by_id(posts='...')  # snake_case тоже работает

    Списки автоматически преобразуются в строки через запятую:

    >>> vk.users.get(user_ids=['1', '2', '3'])  # -> '1,2,3'
    """

    __slots__ = ('_vk', '_method')

    def __init__(self, vk: t.Union[VkApi, 'VkApiMethod'], method: t.Optional[str] = None):
        self._vk = vk
        self._method = method

    def __getattr__(self, method: str) -> 'VkApiMethod':
        # Конвертация snake_case в camelCase
        if '_' in method:
            parts = method.split('_')
            method = parts[0] + ''.join(p.title() for p in parts[1:])

        return VkApiMethod(
            self._vk,
            (self._method + '.' if self._method else '') + method
        )

    def __call__(self, **kwargs) -> t.Any:
        # Конвертация списков в строки
        for k, v in kwargs.items():
            if isinstance(v, (list, tuple)):
                kwargs[k] = ','.join(str(x) for x in v)

        return self._vk.method(self._method, kwargs)

    def __repr__(self) -> str:
        return '<VkApiMethod method={}>'.format(self._method)
