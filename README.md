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

1. W panelu bocznym wybierz etapy (F2 jest zawsze włączone — bramka wejściowa).
2. Każdy etap ma **osobną zakładkę**. Kolejna odblokowuje się dopiero po zaliczeniu poprzedniej (PASS / WARN / STUB).
3. Pliki wgrywaj **w zakładce danego etapu**: IFC w F2, XLSX w F4 i F5.
4. Przy błędzie F2 (lub innego etapu) popraw dane i uruchom ten etap ponownie — dalsze zakładki zostają zablokowane.
5. Po ostatnim etapie otwórz zakładkę **Raport** i pobierz XLSX.

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
