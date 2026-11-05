"""Configurable project checks; results are evidence, not certification."""
import html
import json
import re
import subprocess
import tomllib
from pathlib import Path

DEFAULT_RULES = {'required_files': ['README.md', 'CHANGELOG.md', 'pyproject.toml'],
                 'require_git': True, 'require_ci': True, 'min_commits': 5,
                 'severity': {'files': 'error', 'version': 'error', 'git': 'error',
                              'commits': 'warning', 'ci': 'error'}}


def load_rules(path):
    try:
        rules = json.loads(Path(path).read_text(encoding='utf-8'))
        if not isinstance(rules, dict) or rules.keys() - DEFAULT_RULES.keys():
            raise ValueError('Неизвестные правила')
        result = DEFAULT_RULES | rules
        if (not isinstance(result['required_files'], list)
                or any(not isinstance(f, str) or Path(f).is_absolute() or '..' in Path(f).parts
                       for f in result['required_files'])
                or type(result['min_commits']) is not int or result['min_commits'] < 0
                or type(result['require_git']) is not bool
                or type(result['require_ci']) is not bool
                or not isinstance(result['severity'], dict)
                or result['severity'].keys() - DEFAULT_RULES['severity'].keys()
                or any(s not in ('error', 'warning', 'info') for s in result['severity'].values())):
            raise ValueError('Неверные типы или значения правил')
        result['severity'] = DEFAULT_RULES['severity'] | result['severity']
        return result
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        raise ValueError('Конфигурация правил отсутствует или повреждена') from exc


def audit(directory, rules_path):
    root = Path(directory).resolve()
    findings = []
    try:
        rules = load_rules(rules_path)
    except ValueError as exc:
        return {'passed': False, 'findings': [{'rule': 'config', 'severity': 'error',
                                             'passed': False, 'message': str(exc)}]}

    def record(rule, passed, message):
        findings.append({'rule': rule, 'severity': rules['severity'][rule],
                         'passed': passed, 'message': message})

    for name in rules['required_files']:
        record('files', (root / name).is_file(), name)
    try:
        config = tomllib.loads((root / 'pyproject.toml').read_text(encoding='utf-8'))
        version = config['project']['version']
        valid = isinstance(version, str) and bool(re.fullmatch(
            r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', version))
        record('version', valid, f'project.version: {version}')
    except (OSError, KeyError, TypeError, tomllib.TOMLDecodeError):
        record('version', False, 'pyproject.toml отсутствует, повреждён или не содержит версию')
    git_present = (root / '.git').exists()
    if rules['require_git']:
        record('git', git_present, 'Локальный Git-репозиторий')
    if rules['min_commits']:
        count = 0
        if git_present:
            try:
                proc = subprocess.run(['git', '-C', str(root), 'rev-list', '--count', 'HEAD'],
                                      capture_output=True, text=True, timeout=10, check=False)
                count = int(proc.stdout.strip()) if proc.returncode == 0 else 0
            except (OSError, ValueError, subprocess.TimeoutExpired):
                count = 0
        record('commits', count >= rules['min_commits'], f'{count}/{rules["min_commits"]} коммитов')
    if rules['require_ci']:
        folder = root / '.github' / 'workflows'
        workflows = list(folder.glob('*.yml')) + list(folder.glob('*.yaml'))
        record('ci', any(p.is_file() and p.stat().st_size for p in workflows),
               'Наличие непустого workflow; синтаксис YAML и запуски проверяются отдельно')
    return {'passed': all(f['passed'] for f in findings), 'findings': findings,
            'limitations': 'Проверка внутренних правил не является сертификацией ISO/IEC/IEEE 828.'}


def write_reports(result, json_path, html_path):
    Path(json_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    rows = ''.join('<tr>' + ''.join(f'<td>{html.escape(str(f[k]))}</td>' for k in
                                   ('rule', 'severity', 'passed', 'message')) + '</tr>'
                   for f in result['findings'])
    page = ('<!doctype html><html lang="ru"><meta charset="utf-8">'
            '<title>Аудит конфигурации</title><style>body{font:16px system-ui;margin:32px}'
            'td,th{border:1px solid #999;padding:8px}table{border-collapse:collapse}</style>'
            f'<h1>Аудит: {"пройден" if result["passed"] else "есть нарушения"}</h1>'
            '<table><tr><th>Правило</th><th>Критичность</th><th>Пройдено</th><th>Сообщение</th></tr>'
            + rows + '</table><p>Учебная проверка, не сертификация стандарта.</p></html>')
    Path(html_path).write_text(page, encoding='utf-8')
