---
name: imageselector
description: Wählt aus den RAW-Fotos eines Ordners (ARW, DNG u. a.) eine Auswahl aus und vergibt im Lightroom-Katalog 4 Sterne (Großformat-tauglich) bzw. 3 Sterne (für Screen OK). Die Auswahl deckt alle Personen, Orte und Szenen des Anlasses ab; Technik entscheidet über die Aufnahme in die Grundauswahl, Ästhetik und Emotion nur über das Ranking ähnlicher Bilder. Serienbilder (Zeitabstand unter 1 Sekunde) werden geclustert; bereits händisch bewertete Bilder bleiben unangetastet. Für jedes Genre gedacht (Feiern, Reise, Reportage, Familie, Sport, Natur). Nutze diesen Skill, wenn der Nutzer Fotos auswählen, aussortieren, "die besten Bilder finden", Serienbilder sichten oder Sterne im Lightroom-Katalog vergeben lassen will — auch bei englischen Formulierungen wie "pick the best photos", "cull this shoot", "rate my burst shots". NICHT für Bildbearbeitung, Entwicklungseinstellungen oder Export.
---

# imageselector

Markiert Fotos eines Ordners direkt im Lightroom-Katalog, in zwei Stufen. Die Bearbeitung der markierten Bilder macht der Nutzer danach händisch.

| Sterne | Bedeutung | Typische Bilder |
|---|---|---|
| **4** | Kann auf Großformat gedruckt werden (20 x 30 cm) | Schlüsselmomente, herausragende Porträts, Gruppenbilder, Bilder mit starker Aussage oder Stimmung. Technisch sauber **und** ästhetisch stark. |
| **3** | Für Screenauflösung OK (wird dort stark herunterskaliert) | Alle übrigen zugelassenen Bilder: Personen, Orte, Totalen, Dokumentarisches. Technisch sauber, Ausdruck darf neutral sein. |

## Betrachterperspektive

Bilder vermitteln Emotionen, und die bewerten Menschen. Die Leitfrage bei jeder Entscheidung lautet: **Würde sich ein Mensch dieses Bild hintereinander mit den anderen der Auswahl ansehen wollen, und was löst es aus?** Aus dieser Sicht folgen die Regeln dieses Skills:

- **Wiederholung ermüdet.** Niemand schaut sich viele fast gleiche Bilder an. Eine Auswahl darf nicht denselben Eindruck mehrfach liefern.
- **Vielfalt der Eindrücke:** Jedes Bild soll dem Betrachter etwas Neues zeigen oder fühlen lassen.
- **Bildidee vor Effekt.** Spektakuläre Effekte (Laser, Feuerwerk, Kunstflug, Gegenlicht-Spielereien) tragen nur, wenn das Bild eine Aussage, Stimmung oder Geschichte hat.

## Grundprinzip: Technik lässt zu, Ästhetik rankt

Der Nutzer will eine Auswahl, die den Anlass **vollständig** dokumentiert, nicht nur die schönsten Ausdrücke oder Effekte.

- **Technische Bewertung = Zulassung.** Sie entscheidet, ob ein Bild in die Grundauswahl kommt: Hauptmotiv (bei Personen Gesicht und Augen) ausreichend scharf, keine störende Bewegungsunschärfe, Belichtung aus dem RAW rettbar, Hauptmotiv nicht verdeckt oder abgeschnitten. Ein neutraler oder ernster Ausdruck ist **kein** Ausschlussgrund.
- **Ästhetische Bewertung = Ranking.** Ausdruck, Blick, Komposition, Licht und Emotion kommen nur zum Zug, wenn mehrere **ähnliche** Bilder konkurrieren: Dann gewinnt das ästhetisch beste, die übrigen fallen weg. Auch die Frage 4 oder 3 Sterne wird ästhetisch entschieden.
- **Abdeckung.** Jede Person, die zum Anlass gehört, soll auf mindestens einem Bild der Auswahl vorkommen, außer technische Ausschlusskriterien greifen. Ältere Menschen zählen besonders: Es sind manchmal die letzten Aufnahmen von ihnen. Ebenso soll jeder Ort und jede Szene vertreten sein.
- **Dokumentarisches gehört dazu:** Totalen, Überblicke, Räume, Details mit Erzählwert, Alltagsszenen. Ein Bild darf dokumentarisch sein, ohne „schön" zu sein.
- **Einzelbilder sind bewusste Aufnahmen.** Ein Cluster mit nur einem Frame wurde gezielt ausgelöst und hat deshalb den höheren Prior für die Grundauswahl; Frames aus Serien werden strenger gesiebt.
- **Dublette heißt praktisch gleicher Bildinhalt** (gleicher Standpunkt, gleiches Motiv, gleiche Phase). Derselbe **Ort** mit anderem Blickwinkel oder anderem Motiv ist **keine** Dublette: Bei Spaziergängen, Fahrten und Rundgängen zählt jede eigene Ansicht einzeln. Nur echte Wiederholungen werden zusammengefasst.
- **Serien mit Show-Charakter** (Feuerwerk, Lichtshow, Kunstflug, Tanz, Sportserien) wirken durch ständige Wiederholung. Aus ihnen genügen wenige Bilder, grob **eines je Phase oder Blickwinkel** (z. B. Aufbau, Höhepunkt, Finale, Publikum).
- **Vier Sterne für Aussage und Emotion, nicht für Spektakel.** Die 4-Sterne-Stufe belohnt Bildidee, Moment und Stimmung. Rein spektakuläre Bilder erreichen sie nur, wenn sie zusätzlich etwas erzählen.

## Weitere Grundsätze

- **Im Zweifelsfall aufnehmen:** Nimm das Bild im Zweifelsfall in die Auswahl auf. Der User bearbeitet die Auswahl ohnehin nach, ein Entfernen aus der Auswahl kann der User sehr schnell vornehmen.
- **Keine Zielanzahl.** Die Menge ergibt sich aus der Abdeckung, nicht aus einer Quote. Aus einer Serie wird höchstens ein Bild genommen (zwei nur bei klar verschiedenen Momenten auf hohem Niveau). Wird die Auswahl auffällig groß, enthält sie vermutlich Dubletten.
- **Schlüsselmomente entschuldigen technische Schwächen,** solange diese nicht stören (etwas dunkel, leichte Bewegungsunschärfe, Gesicht teilweise im Schatten). Die Bedeutung des Moments zählt mehr als der Standardausdruck; ein Kuss mit geschlossenen Augen ist kein Mangel. Was ein Schlüsselmoment ist, hängt vom Genre ab (siehe Anweisung in `references/`).
- **Nachbearbeitung fließt in die Bewertung ein.** Crop kann die Komposition ändern (leere Flächen, Randstörer), das RAW verträgt Korrektur von Helligkeit und Weißabgleich. Behebbare Schwächen führen nicht zum Ausschluss; nicht behebbar sind unscharfe Augen bzw. Hauptmotive, verwischte Bewegung und verdeckte Gesichter.
- **Schärfe nicht zu streng.** Großformat heißt 20 x 30 cm, also 3600 px an der langen Seite. Moderne Kameras liefern deutlich mehr Auflösung, die auch im Print nicht ausgeschöpft wird. Geprüft wird am `half_size`-Dekodat bzw. an der auf 3600 px skalierten Ansicht, nicht am 1:1-Pixel des Sensors.
- **Vorhandene Bewertungen sind heilig.** Bilder mit Sternen (händische Auswahl oder Vorbelegung des Nutzers) werden nie verändert, auch wenn sie nicht zur 3-/4-Sterne-Definition passen. Der Skill arbeitet unbeirrt nach seinem eigenen Schema. Ein Cluster mit bewertetem Bild gilt als entschieden und wird übersprungen. `apply_ratings.py` überschreibt nie eine bestehende Bewertung.
- **Keine Bildbearbeitung.** Es wird nur das Rating gesetzt.

## Skripte (`scripts/`, Aufruf mit `python`)

| Skript | Zweck |
|---|---|
| `list_clusters.py <Ordner> [--gap 1.0]` | Liefert JSON mit Clustern (Zeitabstand < `--gap` Sekunden zum Vorgänger), je Bild `id`, `file`, `captureTime`, `rating`; Cluster haben `hasRating`. Videos werden ignoriert. Nur lesend, funktioniert auch bei offenem Lightroom. |
| `make_thumbnail.py <RAW-Datei oder clusters.json> <Zielordner> <Breite> [--workers 6]` | Erzeugt `<Zielordner>/<Name>.jpg`, Höhe proportional. Bei `clusters.json` werden alle Frames parallel umgewandelt; Fehler werden je Datei gemeldet, Exitcode 1 bei mindestens einem Fehler. Benötigt `rawpy` und `Pillow` (`pip install rawpy`). |
| `make_contact_sheets.py <clusters.json> <Thumbnail-Ordner> <Ausgabeordner> [--first N] [--last M] [--pack]` | Baut Kontaktbögen mit höchstens 6 beschrifteten Frames. Ohne `--pack` je Cluster ein Bogen (Beschriftung = letzte 5 Ziffern der Dateinummer). Mit `--pack` teilen sich mehrere kleine Cluster einen Bogen (Beschriftung `cNN 08812`, Zuordnung in `sheets.json`); sinnvoll bei vielen Einzelbild-Clustern. Hoch- und Querformat werden ohne Verzerrung gemischt. |
| `merge_candidates.py <clusters.json> <Kandidaten-Ordner> [--out merged.json]` | Führt die Ergebnisdateien der Agenten zusammen und meldet Cluster, die kein Agent als gesichtet gemeldet hat. |
| `apply_ratings.py --set 4:<id>,... --set 3:<id>,... [--dry-run]` | Setzt Sterne auf Katalog-IDs ohne Bewertung, beliebig viele `--set`-Gruppen in einem Lauf (ein Backup). Prüft, ob Lightroom geschlossen ist. Ein Bild in zwei Gruppen bricht ab. |
| `lrcat.py` | Gemeinsame Katalogzugriffe (kein CLI). |

Standardkatalog im Skript: `D:\Fotos\Lightroom_Catalog\Lightroom_Catalog-v13-3.lrcat` (mit `--catalog` überschreibbar).

## Ablauf

1. **Ordner klären.** Der Nutzer nennt den Foto-Ordner; er muss im Lightroom-Katalog importiert sein. Den Anlass bzw. das Genre (Feier, Reise, Familie, Sport …) kurz festhalten; er steuert Schlüsselmomente und Abdeckung.
2. **Cluster ermitteln.** `list_clusters.py` in eine Datei im Scratchpad umleiten. Cluster mit `hasRating: true` in eine gefilterte Kopie (`clusters_todo.json`) nicht übernehmen und dem Nutzer die Anzahl nennen.
3. **Miniaturen erzeugen** (Scratchpad, nie in den Foto-Ordner). Breite 1200 px, Ausgabe nach `all_th/`. Aufruf: `python make_thumbnail.py clusters.json all_th 1200`. Das Skript liest die Frames aus `clusters.json` und arbeitet sie parallel ab (`--workers`, Standard 6). Die Abschlusszeile (`n/n thumbnails`) prüfen: Fehlerhafte Dateien erscheinen als `FAILED` auf stderr. Je nach Format dauert ein Bild 0,4 bis etwa 1 s; große Ordner laufen im Hintergrund. Danach mit `make_contact_sheets.py` die Bögen nach `all_sheets/` bauen (bei vielen Einzelbild-Clustern mit `--pack`).
4. **Runde 1: Zulassung und Kandidaten je Cluster.** Kontaktbögen mit dem Read-Tool ansehen; bei zum Verwechseln ähnlichen Frames die Einzelbilder öffnen. Je Cluster wird das technisch zugelassene, ästhetisch stimmigste Frame vorgemerkt (oder keins, wenn nichts zugelassen ist), mit Dateiname, Katalog-`id`, **`who`** (wer bzw. was ist zu sehen, für Abdeckung und Dubletten), **Bildaussage**, Stufe und Kennzeichen `key_moment`. Dabei noch **nichts schreiben**. Bei vielen Clustern wird Runde 1 auf Agenten verteilt (nächster Abschnitt); Runde 2 macht immer der Hauptagent, damit das Ranking einheitlich ist.
5. **Runde 2: Abdeckung, Ranking, Stufen.** Alle Kandidaten über den ganzen Ordner zusammenführen (`merge_candidates.py`). Cluster, die kein Agent gesichtet hat, selbst sichten. Dann:
   1. **Gruppieren** nach `who` und Szene, aber **eng**: Dubletten sind nur Bilder mit praktisch gleichem Inhalt. Verschiedene Ansichten desselben Orts sind keine Dubletten. Show-Serien werden nach Phase bzw. Blickwinkel gruppiert und auf wenige Bilder gekürzt.
   2. **Pro Gruppe das ästhetisch beste Bild behalten** (Ausdruck, Blick, Komposition, Emotion); die Gruppenmitglieder dafür nebeneinander ansehen. Die anderen fallen heraus. Bei Gleichstand gewinnt das Einzelbild-Cluster gegenüber einem Frame aus einer Serie.
   3. **Abdeckung prüfen:** Ist jede Person, jede ältere Person, jeder Ort und jede dokumentarische Szene mit mindestens einem Bild vertreten? Fehlendes nachholen, notfalls aus den Grenzfällen.
   4. **Stufen einteilen:** 4 Sterne für Schlüsselmomente, herausragende Porträts und Gruppenbilder und Bilder mit starker Aussage oder Emotion (nicht für bloßen Effekt); deren Hauptmotiv-Ausschnitte vorher mit `rawpy` (`half_size=True`) dekodieren, zuschneiden und ansehen (Maßstab „Schärfe nicht zu streng"). Alle übrigen zugelassenen Bilder bekommen 3 Sterne.
6. **Auswahl vorlegen.** Dem Nutzer beide Stufen mit je einem Satz Begründung nennen, dazu die aussortierten Dubletten (mit dem Bild, das sich durchgesetzt hat) und die Grenzfälle. Anschließend `apply_ratings.py --set 4:... --set 3:... --dry-run` ausführen.
7. **Schreiben.** Lightroom muss dafür **geschlossen** sein. Den Nutzer bitten, es zu beenden, und erst nach seiner Bestätigung `apply_ratings.py` ohne `--dry-run` starten. Bricht das Skript mit `ABORTED` ab, nicht umgehen, sondern den Nutzer informieren.
8. **Abschluss.** Anzahl gesetzter und übersprungener Bilder nennen, den Backup-Pfad angeben und darauf hinweisen, dass die Backups (je nach Katalog mehrere hundert MB) gelöscht werden können, wenn in Lightroom alles passt. Die Thumbnails im Scratchpad werden nicht weiter benötigt.

## Runde 1 auf Agenten verteilen

Ab ca. 30 Kontaktbögen lohnt sich die Verteilung auf parallele Agenten (Agent-Tool, `general-purpose`, `run_in_background: true`), je ein Block mit ca. 30 Bögen (Blöcke nach Anzahl der Bögen bilden, nicht nach Clusteranzahl; kein Cluster darf über zwei Blöcke laufen). Die vollständigen Kriterien stehen in [references/runde1-anweisung.md](references/runde1-anweisung.md). Diese Datei vorher nach `<scratchpad>/INSTRUCTIONS_round1.md` kopieren und darin `<scratchpad>` durch den echten Pfad ersetzen, damit alle Agenten dieselbe, platzhalterfreie Anweisung lesen.

Jeder Agent bekommt einen kurzen Prompt mit **konkret ausgefüllten Werten**, darunter den Anlass:

```
Lies zuerst vollständig die Anweisung <scratchpad>/INSTRUCTIONS_round1.md und arbeite sie ab.

Anlass: <Genre/Anlass in einem Satz, z. B. Städtereise, Familienfeier>
Deine Cluster: 24 bis 48 (einschließlich; nicht vorhandene Nummern überspringen).
Ergebnisdatei: <scratchpad>/cand/cand_02.json
```

Erfahrungen, die den Prompt-Aufbau bestimmen:

- **Nie Platzhalter im Prompt lassen.** Bei einem Agenten blieben `{FIRST}`, `{LAST}` und `{ID}` stehen; er hat gar nichts gesichtet. Clusterbereich und Dateinummer der Ergebnisdatei immer vor dem Absenden einsetzen und den Prompt kurz gegenlesen.
- **Die Anweisung liegt in einer Datei, nicht im Prompt.** Das hält die Kriterien für alle Agenten identisch und den Prompt kurz.
- **Ergebnisdatei mit `reviewed`-Liste.** Agenten überspringen gelegentlich einzelne Cluster („nicht vorhanden"). `merge_candidates.py` findet solche Lücken; fehlende Cluster selbst sichten.
- **UTF-8 verlangen.** Ein Agent hat die Datei in cp1252 geschrieben; `merge_candidates.py` liest mit Fallback.
- **Agenten urteilen an Kontaktbögen und wählen bei ähnlichen Frames manchmal ein anderes als der Hauptagent.** Deshalb vergleicht Runde 2 konkurrierende Frames immer direkt nebeneinander.

## Fallstricke

- **Dateinamen sind nicht eindeutig** (z. B. gleichnamige DNG und ARW in verschiedenen Ordnern). Immer mit den `id`s aus `list_clusters.py` arbeiten, nie mit Dateinamen im SQL.
- **Nie bei laufendem Lightroom schreiben.** Der Katalog ist eine gesperrte SQLite-Datei (WAL); Änderungen von außen können ihn beschädigen oder werden überschrieben. `apply_ratings.py` blockiert bei laufendem Lightroom, bei einer `.lock`-Datei und bei einem `-wal` mit Inhalt; ein leeres `-wal` und `-shm` entstehen auch bei Lesezugriffen und sind harmlos.
- **Lightroom speichert seinen Zustand beim Beenden.** Änderungen, die der Nutzer nach dem Skriptlauf in Lightroom macht (etwa Sterne ändern), bleiben erhalten und sind kein Skriptfehler.
- **Der Katalog enthält auch Videos**; sie sind keine Fotos und werden von `list_clusters.py` ausgelassen.
- Die Zeitstempel im Katalog haben Millisekunden-Auflösung; Serien moderner Kameras liegen typisch bei 0,1 bis 0,3 s Abstand.
