import tempfile
from pathlib import Path

from configuration_auditor.core import audit, write_reports

out = Path(__file__).parent
root = out.parent
rules = root / "audit-rules.json"
compliant = audit(root, rules)
write_reports(compliant, out / "compliant.json", out / "compliant.html")
with tempfile.TemporaryDirectory() as directory:
    broken = Path(directory)
    (broken / "pyproject.toml").write_text('[project]\nversion="wrong"\n')
    noncompliant = audit(broken, rules)
    write_reports(noncompliant, out / "noncompliant.json", out / "noncompliant.html")
print("Соответствующий проект:", compliant["passed"], "; нарушающий:", noncompliant["passed"])
if not compliant["passed"] or noncompliant["passed"]:
    raise SystemExit("Неверный результат демонстрации аудита")
