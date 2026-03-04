# ICanRun — Платформа для триатлонных тренировок

Веб-приложение для спортсменов-любителей и профессионалов, занимающихся бегом, плаванием, велоспортом, силовыми тренировками и триатлоном. Платформа позволяет планировать тренировки, анализировать результаты и автоматически строить планы подготовки по методологии Джо Фрила.

---

## Стек технологий

### Backend
- **Python 3.11** + **FastAPI 0.115** — асинхронный REST API
- **SQLAlchemy 2.0** (async) + **aiosqlite** — ORM и база данных SQLite
- **Alembic** — управление миграциями схемы БД
- **Pydantic v2** — валидация данных и схемы запросов/ответов
- **python-jose** + **passlib/bcrypt** — JWT-аутентификация и хеширование паролей
- **yookassa** — SDK для приёма платежей (ЮКасса)
- **garminconnect** — интеграция с Garmin Connect
- **pytest** + **pytest-asyncio** — тесты (129 тестов)

### Frontend
- **Next.js 14** (App Router) + **TypeScript**
- **Tailwind CSS** + **Radix UI** — стилизация и компоненты
- **TanStack React Query v5** — серверное состояние и кеширование
- **Zustand v5** — клиентское состояние (auth, calendar)
- **Recharts** — графики (страница результатов)
- **dnd-kit** — drag-and-drop тренировок в календаре
- **React Hook Form** + **Zod** — формы и валидация
- **Vitest** + **Testing Library** — тесты компонентов

### Инфраструктура
- **Docker** + **Docker Compose** — контейнеризация и деплой
- База данных: **SQLite** (файл, монтируется как volume)
- Для высоконагруженного production можно мигрировать на PostgreSQL (см. комментарий в `docker-compose.yml`)

---

## Функционал приложения

### Тренировочный календарь (главная страница)
- Месячный вид с навигацией по месяцам
- Карточки тренировок: иконка вида спорта, тип тренировки, продолжительность
- Drag-and-drop: перетаскивание тренировок на другой день
- Отметка о выполнении тренировки (чекбокс на карточке)
- Добавление тренировок, соревнований и пропусков через модальные окна
- Панель статистики по видам спорта за месяц

### Виды спорта
- Бег, плавание, велосипед, силовые тренировки, триатлон

### Типы тренировок (по Фрилу)
- Восстановительная, длинная, интервальная, пороговая

### Соревнования
- Бег: 5 км, 10 км, полумарафон, марафон
- Плавание и велосипед (произвольная дистанция)
- Триатлон: Супер-Спринт, Спринт, Олимпийский, Half-Iron, Iron
- Приоритет: ключевое / второстепенное
- Запись фактического результата гонки

### Тренировочный план (методология Джо Фрила)
- Автоматическая генерация плана под целевое соревнование или на 6 месяцев поддержки формы
- Фазы: Base (>16 недель) → Build (8–16 недель) → Peak (<8 недель) → Taper (2–3 недели до старта)
- 4-недельные циклы: 3 недели нагрузки + 1 неделя восстановления (65% объёма)
- Настраиваемые предпочтительные дни недели и максимальные часы в неделю
- Удаление плана с сохранением прошлых выполненных тренировок

### Страница результатов (аналитика)
- Столбчатый график по дням месяца: выполненные vs запланированные тренировки
- Фильтрация по виду спорта
- Сводная статистика: всего часов, количество тренировок, процент выполнения

### Подписки
| Тариф | Тренировки | Интеграции | Планы |
|-------|-----------|------------|-------|
| Trial (30 дней, бесплатно) | Да | Да | Да |
| Basic (платный) | Да | Да | Нет |
| Pro (платный) | Да | Да | Да |

Новые пользователи автоматически получают Trial на 30 дней.

### Интеграции
- **Garmin Connect** — импорт тренировок из Garmin-устройств
- **ЮКасса (YooKassa)** — приём платежей за подписку

### Администрирование
- Управление пользователями: роли, статус активности
- Управление подпиской пользователей
- Настройки приложения: включение/отключение Google OAuth
- Дефолтный администратор создаётся при старте приложения

---

## Развёртывание на удалённом сервере (Docker Compose)

### Требования
- Docker 24+ и Docker Compose v2
- Открытые порты: **3000** (frontend), **8000** (backend API)

### Шаг 1. Клонировать репозиторий

```bash
git clone <repo-url> /opt/icanrun
cd /opt/icanrun
```

### Шаг 2. Создать файл переменных окружения для backend

```bash
cp backend/.env.example backend/.env
```

Отредактировать `backend/.env` — обязательно задать:

```env
SECRET_KEY=<случайная-строка-минимум-32-символа>
GARMIN_ENCRYPTION_KEY=<случайная-строка-32-байта>
```

Для генерации ключей:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### Шаг 3. Настроить URL API во frontend (опционально)

По умолчанию frontend обращается к backend по имени сервиса Docker (`http://backend:8000`).
Если backend доступен по внешнему домену — задать в `docker-compose.yml`:

```yaml
frontend:
  environment:
    - NEXT_PUBLIC_API_URL=https://api.yourdomain.com
```

### Шаг 4. Запустить

```bash
docker compose up -d --build
```

Frontend будет доступен на `http://<IP-сервера>:3000`.
API — на `http://<IP-сервера>:8000`.
Swagger UI — `http://<IP-сервера>:8000/docs`.

### Шаг 5. Проверить статус

```bash
docker compose ps
docker compose logs backend --tail=50
docker compose logs frontend --tail=50
```

### Данные и хранилище

SQLite-база хранится в `./backend/data/icanrun.db` на хосте (монтируется как volume).
При обновлении приложения данные сохраняются:

```bash
# Обновление без потери данных
git pull
docker compose up -d --build
```

### Nginx (рекомендуется для production)

Пример конфигурации reverse-proxy:

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## API эндпоинты

Все эндпоинты доступны по префиксу `/api/v1/`.
Интерактивная документация: `http://localhost:8000/docs`

### Аутентификация (`/auth`)

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/auth/register` | Регистрация нового пользователя (выдаёт токены + Trial подписку) |
| POST | `/auth/login` | Вход по email и паролю |
| POST | `/auth/refresh` | Обновление access-токена по refresh-токену |
| POST | `/auth/logout` | Инвалидация refresh-токена |
| GET | `/auth/me` | Профиль текущего пользователя с подпиской |

JWT: access-токен — 30 мин, refresh-токен — 7 дней, ротация при обновлении.

### Пользователи (`/users`)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/users/me` | Получить свой профиль |
| PATCH | `/users/me` | Обновить профиль (имя, возраст, вес, рост, пол) |

### Тренировки (`/workouts`)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/workouts` | Список тренировок с фильтрами (год, месяц, диапазон дат, вид спорта, выполнение) |
| POST | `/workouts` | Создать тренировку |
| GET | `/workouts/{id}` | Получить тренировку |
| PATCH | `/workouts/{id}` | Обновить тренировку |
| DELETE | `/workouts/{id}` | Удалить тренировку |
| POST | `/workouts/{id}/complete` | Отметить тренировку выполненной (с фактическими данными) |
| PATCH | `/workouts/{id}/toggle-complete` | Переключить флаг выполнения |
| PATCH | `/workouts/{id}/move` | Перенести на другую дату (drag-and-drop) |

### Соревнования (`/competitions`)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/competitions` | Список соревнований с фильтрами |
| POST | `/competitions` | Создать соревнование |
| GET | `/competitions/{id}` | Получить соревнование |
| PATCH | `/competitions/{id}` | Обновить соревнование |
| DELETE | `/competitions/{id}` | Удалить соревнование |
| POST | `/competitions/{id}/result` | Записать фактический результат гонки |

### Тренировочные планы (`/plans`)

| Метод | Путь | Описание | Подписка |
|-------|------|----------|----------|
| POST | `/plans/generate` | Сгенерировать план по методологии Фрила | Trial / Pro |
| GET | `/plans` | Список активных планов пользователя | все |
| GET | `/plans/{id}` | Детальный план с периодами и тренировками | все |
| PATCH | `/plans/{id}/settings` | Пересчитать план с новыми настройками | Trial / Pro |
| DELETE | `/plans/{id}` | Удалить план (будущие тренировки удаляются, прошлые сохраняются) | все |

### Аналитика (`/analytics`)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/analytics/monthly` | Сводная статистика за месяц |
| GET | `/analytics/daily` | Статистика по дням месяца для графиков |

### Подписки (`/subscriptions`)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/subscriptions/current` | Текущая активная подписка пользователя |

### Администрирование (`/admin`) — только для администраторов

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/admin/users` | Список всех пользователей с подписками |
| PATCH | `/admin/users/{id}` | Изменить роль / активность пользователя |
| GET | `/admin/settings` | Настройки приложения |
| PATCH | `/admin/settings` | Обновить настройки приложения |

### Служебные

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/v1/health` | Health check (используется Docker healthcheck) |

---

## Переменные окружения

### Backend (`backend/.env`)

| Переменная | Обязательная | По умолчанию | Описание |
|------------|-------------|--------------|----------|
| `APP_ENV` | нет | `development` | Окружение: `development` / `production` |
| `DEBUG` | нет | `true` | Включить debug-режим FastAPI |
| `SECRET_KEY` | **да** | — | Секрет для подписи JWT (мин. 32 символа) |
| `DATABASE_URL` | нет | `sqlite+aiosqlite:///./icanrun.db` | URL базы данных |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | нет | `30` | Время жизни access-токена (минуты) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | нет | `7` | Время жизни refresh-токена (дни) |
| `CORS_ORIGINS` | нет | `["http://localhost:3000"]` | Разрешённые origins для CORS (JSON-массив) |
| `GOOGLE_OAUTH_ENABLED` | нет | `false` | Включить вход через Google |
| `GOOGLE_CLIENT_ID` | нет | — | ID приложения Google OAuth |
| `GOOGLE_CLIENT_SECRET` | нет | — | Секрет приложения Google OAuth |
| `GOOGLE_REDIRECT_URI` | нет | — | Redirect URI для Google OAuth |
| `YOOKASSA_SHOP_ID` | нет | — | ID магазина ЮКасса |
| `YOOKASSA_SECRET_KEY` | нет | — | Секретный ключ ЮКасса |
| `YOOKASSA_RETURN_URL` | нет | — | URL возврата после оплаты |
| `GARMIN_ENCRYPTION_KEY` | нет | — | Ключ шифрования учётных данных Garmin (32 байта) |
| `ADMIN_EMAIL` | нет | `abramov.yu.v@gmail.com` | Email дефолтного администратора |
| `ADMIN_PASSWORD` | нет | `3tuka2puka` | Пароль дефолтного администратора |
| `FRONTEND_URL` | нет | `http://localhost:3000` | URL frontend (для ссылок в письмах и редиректах) |

### Frontend (переменные окружения Docker / `.env.local`)

| Переменная | Обязательная | По умолчанию | Описание |
|------------|-------------|--------------|----------|
| `NEXT_PUBLIC_API_URL` | нет | `http://backend:8000` | Базовый URL backend API |

---

## Локальная разработка

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # заполнить SECRET_KEY
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
# создать frontend/.env.local:
# NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

### Тесты backend

```bash
cd backend
pytest tests/ -v
```

### Тесты frontend

```bash
cd frontend
npm run test
```

---

## Структура проекта

```
icanrun/
├── backend/
│   ├── app/
│   │   ├── main.py                # Точка входа FastAPI, seed администратора
│   │   ├── core/                  # Конфиг, БД, JWT, зависимости
│   │   ├── api/v1/routers/        # FastAPI роутеры
│   │   ├── services/              # Бизнес-логика (план Фрила, аналитика)
│   │   ├── repositories/          # Слой доступа к данным
│   │   ├── models/                # SQLAlchemy ORM модели
│   │   ├── schemas/               # Pydantic схемы
│   │   └── utils/                 # Enums, хелперы
│   ├── tests/                     # pytest тесты
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/                   # Next.js App Router
│   │   │   ├── page.tsx           # Лендинг
│   │   │   ├── (auth)/            # Логин, регистрация
│   │   │   └── (app)/             # Защищённые страницы (dashboard, results, settings, admin)
│   │   ├── components/            # React компоненты
│   │   ├── hooks/                 # React хуки
│   │   ├── lib/                   # API клиент, утилиты
│   │   ├── stores/                # Zustand хранилища
│   │   └── types/                 # TypeScript типы
│   ├── Dockerfile
│   └── package.json
└── docker-compose.yml
```
