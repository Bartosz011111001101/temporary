# QmlWord

Desktopowy edytor dokumentów: interfejs w **QML / Qt Quick Controls** (Qt 6), logika w **Pythonie (PySide6)**.
Dokument to uporządkowana lista bloków (akapity, sekcje, tabele, obrazy, podpisy, podziały stron),
zapisywana w czytelnym, wersjonowanym formacie JSON.

## Uruchomienie

Wymagania: Python 3.11+ i PySide6 6.8+ (sprawdzone na Python 3.12 + PySide6 6.11.2, Windows 11).

```bash
pip install -r requirements.txt
python main.py                              # nowy dokument
python main.py examples/przyklad.qwd.json   # przykładowy dokument
```

W VS Code: **F5** (konfiguracja „QmlWord: uruchom” w `.vscode/launch.json`). Są też konfiguracje
„QmlWord: przykładowy dokument” i „Testy (pytest)”.

Testy (bez okna na ekranie – Qt w trybie offscreen):

```bash
python -m pytest -q tests
```

Narzędzia: `python tools/make_icons.py` (generuje ikony SVG), `python tools/make_example.py`
(odtwarza przykładowy dokument).

## Co faktycznie działa

**Plik**
- Nowy / Otwórz / Zapisz / Zapisz jako (`*.qwd.json`), zapis atomowy (plik tymczasowy + podmiana).
- Pytanie o niezapisane zmiany przy zamykaniu, nowym i otwieraniu dokumentu.
- Przypomnienie o niezapisanych zmianach po 10 minutach pracy bez zapisu.
- Kopia robocza co 30 s i odzyskiwanie po awarii (blokada `QLockFile` na sesję).
- Eksport PDF (`QPdfWriter`): prawdziwa paginacja, numery stron, powtarzanie nagłówka tabeli na kolejnych stronach.
- **Podgląd stron** pokazuje dokładnie ten układ, który trafia do PDF.
- Czytelne komunikaty błędów zapisu, odczytu i eksportu. Uszkodzone lub nieznane dane nie wywracają aplikacji:
  bloki nieznanego typu są zachowywane bez zmian, a poprawki pokazywane są jako ostrzeżenia.

**Edycja**
- Bloki: akapit, Tytuł, Nagłówki 1–6 (sekcje), lista punktowana/numerowana z wcięciami, tabela, obraz,
  podpis, podział strony, pusty blok.
- Formatowanie znaków: pogrubienie, kursywa, podkreślenie, przekreślenie, kolor tekstu, zakreślenie,
  krój, rozmiar, link (Ctrl+klik otwiera), czyszczenie formatowania.
- Akapit: wyrównanie (4 rodzaje), wcięcia, odstęp przed/po, interlinia.
- Enter dzieli blok, Backspace na początku scala z poprzednim, Shift+Enter to nowy wiersz,
  wklejenie kilku akapitów tworzy kilka bloków.
- Cofnij/Ponów dla wszystkich operacji (pisanie scalane w jeden krok), wycinanie, kopiowanie, wklejanie.
- Wyszukiwanie w akapitach, komórkach i podpisach z przechodzeniem między wynikami (F3 / Shift+F3).
- Menu kontekstowe dla tekstu, tabel, obrazów, sekcji i bloków.
- Potwierdzenia przy usuwaniu sekcji z zawartością i tabel z tekstem.

**Sekcje i nawigacja**
- Automatyczne drzewo sekcji z numeracją (1, 1.1, 1.1.1), znacznikiem poziomu i liniami zagnieżdżenia.
- Zwijanie i rozwijanie gałęzi. Kliknięcie przenosi do nagłówka.
- Szybkie dodawanie sekcji i podsekcji, zmiana nazwy (F2 lub dwuklik) i poziomu (całe poddrzewo albo sam nagłówek).
- Przeciąganie sekcji w panelu: górna część wiersza = przed, środek = do środka (jako podsekcja), dół = za.
  Niedozwolone upuszczenia (np. sekcja do własnej podsekcji, przekroczenie 6 poziomów) są oznaczane
  na czerwono i blokowane. To samo z klawiatury: Ctrl+↑/↓ zmienia kolejność, Ctrl+←/→ poziom.
- Opis sekcji (krótki tekst pod nagłówkiem) jest osobnym polem i nie jest podpisem elementu.

**Tabele**
- Wstawianie z wyborem rozmiaru, dodawanie i usuwanie wierszy oraz kolumn.
- Scalanie (Shift+klik zaznacza zakres) i dzielenie komórek.
- Zmiana szerokości kolumn i wysokości wierszy przez przeciąganie krawędzi (dwuklik przywraca wysokość automatyczną)
  lub w panelu właściwości.
- Wyrównanie i tło komórek, formatowanie tekstu w komórkach.
- Wiersz nagłówka z opcją powtarzania na kolejnych stronach (w podglądzie i PDF).
- Tab / Shift+Tab przechodzi między komórkami, Tab w ostatniej komórce dodaje wiersz, strzałki przechodzą między wierszami.

**Podpisy**
- Podpis tabeli lub obrazu jest powiązany przez `targetId` i numerowany automatycznie („Tabela 2.”, „Rysunek 1.”).
- Przy przenoszeniu, kopiowaniu i usuwaniu podpis podąża za swoim elementem.
  Nie da się niczego upuścić między element a jego podpis.

**Przeciąganie (drag and drop)** ze wskaźnikiem miejsca upuszczenia i autoprzewijaniem:
- bloki dokumentu (uchwyt w lewym marginesie; nagłówek przenosi całą sekcję);
- tabele i obrazy (razem z podpisem);
- sekcje i podsekcje w panelu nawigacji;
- elementy z zakładki „Wstaw” do wybranego miejsca w dokumencie.

Esc anuluje przeciąganie. Bez myszy blok przenosi Alt+Shift+↑/↓.

**Interfejs**
- Panel sekcji, centralna kartka z widocznymi marginesami i podziałami stron (tryb ciągłego przewijania) oraz panel właściwości.
- Panel właściwości zależy od zaznaczenia: tekst, sekcja, tabela, obraz, podpis albo cały dokument.
- Wąskie okno: panele chowają się automatycznie, pasek narzędzi zawija się. Panele przełącza się też Ctrl+Shift+1/2.
- Powiększenie 50–200% (Ctrl+kółko, Ctrl+±, suwak).
- Obsługa klawiaturą: F6 przełącza obszary (sekcje → dokument → właściwości → paski), pełna lista skrótów pod F1.

## Ograniczenia MVP

- **DOCX nie jest obsługiwany.** Architektura jest przygotowana (`qmlword/io/formats.py`: rejestr importerów
  i eksporterów, okna dialogowe biorą filtry z rejestru), ale importera ani eksportera DOCX nie ma.
- Edycja to tryb ciągłego przewijania. Prawdziwy podział na strony widać w „Podglądzie stron” i w PDF,
  a w edytorze tylko wymuszone podziały stron.
- Zaznaczenie tekstu działa w obrębie jednego bloku. Nie da się zaznaczyć ani skopiować kilku bloków naraz
  (bloki przenosi się uchwytem).
- Formatowanie bez zaznaczenia obejmuje słowo pod kursorem lub pusty akapit. W środku odstępu między słowami
  nie ustawia formatu „na następne znaki”.
- Wysokości wierszy tabeli są respektowane w edytorze; w PDF wysokość wynika z treści.
- Lista numerowana ma jeden styl numeracji (1., 2., 3.); punktory nie mają wariantów.
- Obrazy są linkowane (ścieżka względna do katalogu dokumentu albo bezwzględna), nie osadzane w pliku.
- Zmiana nazwy sekcji w panelu zastępuje formatowanie znaków w tytule zwykłym tekstem.

## Format pliku (`*.qwd.json`)

```json
{
  "format": "qmlword-document",
  "schemaVersion": 1,
  "meta":  { "title": "…", "author": "…", "created": "…", "modified": "…", "fontFamily": "Calibri", "fontSize": 11 },
  "page":  { "size": "A4", "orientation": "portrait", "margins": { "top": 25, "bottom": 25, "left": 25, "right": 25 } },
  "blocks": [
    { "id": "b…", "type": "heading", "level": 1, "runs": [{ "text": "Wstęp" }], "description": "…", "para": { … } },
    { "id": "b…", "type": "paragraph", "style": "body",
      "runs": [{ "text": "Ala ", "bold": true }, { "text": "link", "link": "https://…" }],
      "para": { "align": "justify", "indent": 0, "spaceBefore": 0, "spaceAfter": 6, "lineHeight": 1.15, "list": "none" } },
    { "id": "t1", "type": "table", "table": { "rows": 2, "cols": 2, "colWidths": [0.5, 0.5], "rowHeights": [0, 0],
      "headerRow": true, "repeatHeader": true, "cells": [[{ "runs": [], "align": "left", "rowSpan": 1, "colSpan": 1 }, …]] } },
    { "id": "c1", "type": "caption", "caption": { "targetId": "t1", "text": "Wyniki" } },
    { "id": "b…", "type": "image", "image": { "path": "img/wykres.png", "width": 0.6, "align": "center", "alt": "" } },
    { "id": "b…", "type": "pageBreak" }
  ]
}
```

- Tekst to lista przebiegów (`runs`) z jawnym formatowaniem, a nie HTML.
- Sekcje to bloki `heading`. Relacje rodzic–dziecko wynikają z poziomów i kolejności, a drzewo
  (z `parentId` i numeracją) buduje `ops.outline()`.
- Migracje schematu dodaje się w `json_format.MIGRATIONS`.

## Architektura

```
main.py                       start aplikacji (PySide6 + QQmlApplicationEngine)
qmlword/model/                czysty model bez Qt: bloki, dokument, style, operacje (sekcje, przenoszenie), tabele
qmlword/io/                   JSON (wersjonowany), rejestr formatów, budowa QTextDocument, eksport PDF
qmlword/qt/                   typy dla QML: DocumentModel (lista + QUndoStack), OutlineModel, SearchController,
                              AutosaveManager, PageLayout/PagePreview, RichText (TextEdit ↔ przebiegi), AppUtils
qml/                          interfejs; każdy widok, panel, blok, dialog i menu to osobny plik:
  Main.qml, Theme.qml, EditorController.qml, DragController.qml
  panels/  blocks/  properties/  dialogs/  menus/  controls/  icons/
tests/                        pytest: model, operacje, I/O, rich text, DocumentModel, usługi, przepływ na prawdziwym UI
```

Każda zmiana dokumentu to nowa, niemutowalna migawka na `QUndoStack`. Bloki są współdzielone między migawkami,
więc cofanie jest tanie. Przy nakładaniu migawki model wylicza minimalną różnicę: przeniesienie zgłasza jako
`rowsMoved`, zmianę treści jako `dataChanged`. Dzięki temu aktywne edytory nie są odtwarzane i nie tracą kursora.
