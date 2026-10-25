# Модель данных — демонстрационная версия

```mermaid
erDiagram
    BROWSER_PROFILE ||--o{ APPLICATION : "creates"
    APPLICATION ||--o{ DOCUMENT_METADATA : "mentions"
    APPLICATION ||--o{ HISTORY_ENTRY : "records"
    APPLICATION ||--o{ SCORING_FACTOR : "calculates"
    BROWSER_PROFILE {
      string name
      string inn
      string form
      string industry
      boolean isNew
    }
    APPLICATION {
      string id PK
      string status
      number amount
      integer term
      string purpose
      string product
      number cfads
      number debt
      boolean consent
      boolean checks
    }
    DOCUMENT_METADATA {
      string id
      string name
      number size
      string date
    }
    HISTORY_ENTRY {
      string time
      string text
    }
    SCORING_FACTOR {
      string name
      number weight
      number score
    }
```

- На сервере одна таблица SQLite `applications`: `id TEXT PRIMARY KEY`, `payload TEXT NOT NULL`, `updated_at TEXT NOT NULL`.
- Досье хранится как JSON-снимок, содержащий профиль, цель, параметры, статусы, историю и метаданные документов.
- Локально в браузере `localStorage['alfa-bolshe-v1']` содержит данные проекта, финансовую модель, проекты, черновики и копии заявок. Раздел паспорта использует `state.passports`, в котором каждое поле имеет `value`, `source` и необязательный `period`.
- Все источники и показатели из API компании синтетические; пользователь может внести сведения сам.
- Серверное хранилище общедоступно любому, кто может обратиться к демо API. Реальные персональные данные запрещены.
