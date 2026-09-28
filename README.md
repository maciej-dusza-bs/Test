# Kontrola IFC (demo)

Lokalna aplikacja webowa (Streamlit) do kontroli pojedynczego pliku IFC (do 50 MiB). Wersja demonstracyjna jest przygotowana pod schemat **IFC2X3**. Logika sprawdzeń, I/O i raport są niezależne od interfejsu.

## Wymagania

- Python 3.10+
- Windows / Linux / macOS

## Uruchomienie

W katalogu projektu:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run ifc_qa/app.py
```

Aplikacja otworzy się w przeglądarce (zazwyczaj `http://localhost:8501`).

## Przebieg pracy

1. W panelu bocznym wybierz sprawdzenia (F2 jest zawsze włączone — to bramka wejściowa).
2. Wgraj plik `*.ifc`.
3. Opcjonalnie wgraj XLSX dla F4/F5 (w tej iteracji pliki są tylko parsowane).
4. Uruchom kontrolę.
5. Jeśli F2 zakończy się błędem, popraw plik i wgraj ponownie.
6. Pobierz **Raport Kontroli** w formacie XLSX (arkusz Podsumowanie + arkusz na każde sprawdzenie).

### Walidacja F2

| Kod | Warunek |
|-----|---------|
| V2.1 | Plik został wybrany |
| V2.2 | Rozszerzenie `*.ifc` |
| V2.3 | Rozmiar od 10 B do 50 MiB |
| V2.4 | Nagłówek zawiera `ISO-10303-21` |
| V2.5 | Obecne `FILE_SCHEMA` |
| V2.6 | `ifcopenshell.open()` otwiera plik |

Inny schemat niż IFC2X3 daje **WARN** (plik idzie dalej). Twarde odrzucenie: `unknown_schema_policy: fail` w `ifc_qa/config/settings.yaml`.

F3, F4 i F5 zwracają status **STUB** — reguły merytoryczne są zaplanowane na iterację 2.

## Testy

```bash
pytest
```

## Jak dodać nowe sprawdzenie

Nie zmieniaj UI ani generatora raportu. UI i XLSX czytają rejestr i ujednolicony `CheckResult`.

1. Utwórz plik `ifc_qa/checks/f6_moje_sprawdzenie.py`.
2. Zaimplementuj klasę:

```python
from ifc_qa.checks.base import BaseCheck
from ifc_qa.core.models import CheckContext, CheckResult, CheckStatus
from ifc_qa.core.registry import register_check

@register_check
class MojeSprawdzenie(BaseCheck):
    id = "F6"
    name = "Opis sprawdzenia"
    group = "model"
    requires_attachments = ()  # np. ("xlsx",) albo ("docx",)

    def run(self, ctx: CheckContext) -> CheckResult:
        return CheckResult(
            check_id=self.id,
            name=self.name,
            status=CheckStatus.PASS,
            summary="OK",
            findings=[],
        )
```

3. Dodaj import w `ifc_qa/checks/__init__.py` (rejestracja przy starcie).

Załączniki XLSX/DOCX parsuj wyłącznie przez `ifc_qa.io.xlsx_adapter` / `docx_adapter` w warstwie UI lub pipeline — w `run()` korzystaj z `ctx.attachments`.

## Iteracja 2 (poza zakresem demo)

- F3: metadane projektu / OwnerHistory / jednostki.
- F4: whitelist klas IFC z XLSX.
- F5: wymagane parametry (Pset) dla wybranej klasy z XLSX.
