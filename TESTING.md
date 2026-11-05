# Проверка и демонстрация CI

## Локальная проверка отдельного клона

```sh
uv sync --locked
uv run pytest -v
uv run ruff check .
uv run python examples/demo.py
```

Python CI запускается при push и pull_request на Python 3.11 и 3.12.
Локальные протоколы examples/verification.txt и результаты GitHub Actions — разные
свидетельства. Ссылки на удалённые запуски собраны в CI_EVIDENCE.md.

## Аудит

```sh
uv run configuration-auditor audit . --rules audit-rules.json
```

Успех означает прохождение внутренних правил, а не сертификацию стандарта.
CI получает полную историю Git через fetch-depth: 0, чтобы число коммитов
сравнивалось с audit-rules.json. JSON/HTML сохраняются в Actions Artifacts.
Проверка наличия workflow не является проверкой реального успешного запуска.
