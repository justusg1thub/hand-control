# Hand Control

Ein Projekt zum Steuern von Maus, Klicks, Scrollen, Lautstärke und Mehr mit Handgesten.

## Features

- Maus steuern mit Zeigefinger
- Linksklick, Rechtsklick, Doppelklick
- Drag & Drop mit Pinch
- Scrollen mit Peace-Geste
- Lautstärke mit Rock-Geste
- Task-Ansicht, Play/Pause, Stumm
- globale Hotkeys und kleines Tray-Symbol
- Vorschau im Fenster mit Hilfe, Debug, aktive Zone
- Start im Vorschau-Modus, mit `K` oder Shaka-Geste aktivieren

## Installation

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Start

```bash
python hand_control.py
```

Optionen:

```bash
python hand_control.py --preview full --start-active
python hand_control.py --main-hand right
python hand_control.py --camera 1
```

## Gesten

- Zeigefinger hoch: Maus bewegen
- Daumen + Zeigefinger: Linksklick / ziehen
- Daumen + Mittelfinger: Rechtsklick
- Daumen + Ringfinger: Doppelklick
- Peace: Scrollen
- Rock: Lautstärke
- Offene Hand wischen: Links/Rechts
- 3 Finger: Task-Ansicht
- Daumen hoch: Play/Pause
- Daumen runter: Stumm
- Shaka lang halten: Steuerung an/aus

## Tasten im Vorschau-Fenster

- `Q` / `ESC`: Beenden
- `K`: Steuerung an/aus
- `H`: Hilfe anzeigen
- `D`: Debug anzeigen
- `L`: Skelettlinien
- `Z`: aktive Zone anzeigen
- `P`: Vorschau wechseln
- `S`: Screenshot

## Hinweis

Falls das Projekt als Administrator läuft, müssen auch simulierte Eingaben mit Administratorrechten laufen, damit sie in Administratorprogrammen funktionieren.
