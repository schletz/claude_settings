# Sichtungsanweisung Runde 1 (für parallele Agenten)

Du sichtest Fotos (Kontaktbögen) eines Anlasses, der im Prompt genannt ist (z. B. Feier, Reise, Familie, Sport, Natur), und schlägst Kandidaten für die **Grundauswahl** vor. Du veränderst NICHTS außer deiner einen Ergebnisdatei. Kein Zugriff auf den Lightroom-Katalog, keine Fotoordner, keine anderen Dateien schreiben.

## Betrachterperspektive

Bilder vermitteln Emotionen, und die bewerten Menschen. Frage dich bei jedem Bild: **Würde sich ein Mensch dieses Bild mit den anderen der Auswahl hintereinander ansehen wollen, und was löst es aus?** Wiederholung ermüdet: Niemand will viele fast gleiche Bilder derselben Sache sehen. Bildidee, Stimmung und Aussage zählen mehr als bloßer Effekt.

## Grundgedanke: Technik lässt zu, Ästhetik rankt

Die Auswahl soll **jede Person und jede Szene des Anlasses abdecken**, nicht nur die schönsten Ausdrücke sammeln. Dafür gilt eine strikte Trennung:

- **Technische Zulassung** entscheidet, ob ein Bild in die Grundauswahl kommt.
- **Ästhetik** (Ausdruck, Blick, Lächeln, Komposition, Licht) entscheidet nur, welches von mehreren **ähnlichen** Bildern gewinnt. Ein neutraler oder ernster Ausdruck ist KEIN Ausschlussgrund.

### Technische Zulassung (alle müssen erfüllt sein)

1. Das Hauptmotiv ist ausreichend scharf (bei Personen: Gesicht und Augen). Maßstab ist 20 x 30 cm Druck bzw. Screen; die Sensorauflösung übertrifft das deutlich. Sei bei der Schärfe NICHT zu streng.
2. Keine störende Bewegungsunschärfe (gewollte Bewegung, z. B. Wischer bei Verkehr, ist kein Fehler).
3. Die Belichtung ist aus dem RAW rettbar (etwas dunkel/hell ist in Ordnung).
4. Das Hauptmotiv ist nicht verdeckt oder abgeschnitten (bei Personen: Gesicht sichtbar).

Behebbares zählt nicht: Crop (leere Flächen, Randstörer), Helligkeit, Weißabgleich, schiefer Horizont.

### Abdeckung

- **Jede Person, die zum Anlass gehört, soll auf mindestens einem Foto der Auswahl vorkommen** (bei Feiern jeder Gast, auf Reisen die Mitreisenden und Begegnungen, in der Familie alle Familienmitglieder), außer technische Ausschlusskriterien greifen. Achte besonders auf **ältere Menschen**: Es sind manchmal die letzten Aufnahmen von ihnen.
- **Jeder Ort und jede Szene** soll vertreten sein (Schauplätze, Räume, Stationen, Stimmungen).
- **Dokumentarische Bilder** gehören in die Auswahl: Totalen, Überblicke, Räume, Detailaufnahmen mit Erzählwert, Schilder, Essen, Alltagsszenen. Ein Bild darf dokumentarisch sein, ohne „schön" zu sein.
- Wähle je Cluster das technisch beste, ästhetisch stimmigste Frame; mit dem Cluster ist die Abdeckung dieser Personen/Szene erledigt.
- **Einzelbild-Cluster** (ein einziges Frame) sind bewusst ausgelöste Aufnahmen und haben den höheren Prior. Bei Serien (mehrere Frames) bist du strenger: Melde sie nur, wenn sie etwas Eigenes zeigen.
- **Dublette = praktisch gleicher Bildinhalt** (gleicher Standpunkt, gleiches Motiv, gleiche Phase), auch aus verschiedenen Clustern. Melde beide, aber mit identischer Beschreibung in `who`, damit Runde 2 nur das ästhetisch beste behält.
- **Derselbe Ort mit anderem Blickwinkel oder anderem Motiv ist KEINE Dublette.** Bei einem Spaziergang, Rundgang oder einer Fahrt zählt jede eigene Ansicht einzeln (Weg, Detail, Schild, Kreuzung, Gebäude). Beschreibe sie deshalb in `who` unterscheidbar (nicht alle mit dem Ortsnamen).
- **Serien mit Show-Charakter** (Feuerwerk, Licht- und Lasershow, Kunstflug, Tanz, Sportserien) wiederholen sich stark. Melde daraus pro Phase oder Blickwinkel nur das beste Bild (insgesamt wenige) und beschreibe die Phase in `who` (Aufbau, Höhepunkt, Finale, Publikum), damit Runde 2 sie unterscheiden kann.

### Schlüsselmomente

Die Bedeutung eines Moments entschuldigt technische Schwächen, solange sie nicht stören (etwas dunkel, leichte Bewegungsunschärfe, Gesicht teilweise im Schatten). Die Ausdrucksregeln gelten dort nur eingeschränkt. Markiere sie mit `key_moment: true`.

Was ein Schlüsselmoment ist, hängt vom Anlass ab. Orientierung:

| Genre | Schlüsselmomente |
|---|---|
| Feiern und Zeremonien (z. B. Hochzeit) | Höhepunkte des Programms (Kuss, Ringtausch, Einzug, Jawort, Anschneiden, Tanz), Tränen der Rührung, Applaus, Gratulation, Umarmungen |
| Reise/Reportage | Wahrzeichen, Begegnungen und Gesten, flüchtige Alltagsszenen mit starker Aussage, besondere Lichtstimmungen, Feste |
| Familie/Kinder | Gesten, erste Male, spontane Emotionen, gemeinsame Momente mehrerer Generationen |
| Sport/Action | Entscheidende Momente, Höhepunkte der Bewegung, Emotionen von Siegern und Verlierern |
| Natur/Tiere | Charakteristisches Verhalten, besondere Lichtstimmungen, seltene Motive |

## Stufen

| Stufe | Bedeutung |
|---|---|
| **4** | Großformat 20 x 30 cm. Schlüsselmoment oder starke Aussage und Emotion (starker Ausdruck, Bildidee, besondere Stimmung), auch die besten Porträts und Gruppenfotos. Bloßer Effekt reicht nicht: Ein Show-Bild bekommt Stufe 4 nur, wenn es zusätzlich etwas erzählt, z. B. Gesichter der Zuschauer im Licht der Show. |
| **3** | Für Screenauflösung OK: alle übrigen zugelassenen Bilder (Personen, Dokumentation, Totalen, Räume, ruhige Szenen). |

Nicht zugelassen (keine Stufe): technisch unbrauchbar (unscharf, verwackelt, verdeckt), reine Wiederholung ohne neuen Inhalt.

## Material

- Kontaktbögen `<scratchpad>/all_sheets/sheet_*.jpg` (je max. 6 Frames). Zwei Beschriftungsarten:
  - `sheet_cNN_P.jpg`: ein Bogen gehört zu Cluster NN (P = Teil ab 0); die Beschriftung im Bild zeigt die letzten 5 Ziffern der Dateinummer (08832 = DSC08832).
  - `sheet_pNNN.jpg` (gepackt): mehrere Cluster teilen sich einen Bogen; die Beschriftung lautet `cNN 08812` (Cluster, Dateinummer). `<scratchpad>/all_sheets/sheets.json` ordnet jedem Bogen seine Cluster zu.
- Einzelbilder 1200 px: `<scratchpad>/all_th/<Dateiname ohne Endung>.jpg`. Bei knappen Entscheidungen zwischen ähnlichen Frames ÖFFNE DIE EINZELBILDER, urteile nicht nur am Kontaktbogen. Die Endung der Originale kann ARW, DNG o. ä. sein; `file` in der Ergebnisdatei ist immer der Dateiname ohne Endung, wie er im Bogen steht (Präfix, z. B. `DSC`, ergänzt du aus den Namen in `all_th/`).
- Ein Cluster = Serienbild (Abstand < 1 s); viele Cluster sind Einzelbilder. Betrachte Bilder mit dem Read-Tool.
- Der Prompt nennt deinen Bereich (Bogen bzw. Cluster). Lege dir vor dem Start per Glob die Liste deiner Bögen an und arbeite JEDEN davon ab. Überspringe nichts, nur weil es dir nicht auffällt.

## Ergebnisdatei

Schreibe **UTF-8** (Python: `open(pfad, "w", encoding="utf-8")`, `ensure_ascii=False`) ein JSON-Objekt:

```json
{
  "reviewed": [12, 13, 14],
  "candidates": [
    {"cluster": 12, "file": "DSC08999", "who": "Großmutter und Enkelin, Terrasse",
     "statement": "Großmutter und Enkelin lachen gemeinsam", "tier": "3",
     "key_moment": false, "note": "kurze Begründung auf Deutsch"}
  ]
}
```

- `reviewed`: ALLE Clusternummern, die du gesichtet hast, auch die ohne Kandidat. Der Hauptagent prüft damit, ob du keine übersprungen hast.
- `file`: Dateiname ohne Endung. Höchstens ein Kandidat pro Cluster, zwei nur bei klar verschiedenen Motiven.
- `who`: Wer bzw. was ist zu sehen (Personen, Ort, Szene). Wird für Abdeckung und Dubletten in Runde 2 gebraucht.
- `statement`: Bildaussage in wenigen Worten; gleiche Aussage = gleiche Formulierung.
- `tier`: `"4"`, `"3"` oder `"grenzfall"` (knapp technisch nicht zugelassen; 1 Satz Grund).
- Datei immer schreiben, auch wenn `candidates` leer ist.

Abschlussmeldung: max. 5 Zeilen (gesichtete Cluster, Anzahl je Stufe, Auffälligkeiten). Keine Kandidatenlisten in der Antwort.
