---
name: create-subs
description: Erstellt deutsche Untertitel für eine Video- oder Audiodatei und muxt sie in ein MKV mit gleichem Dateinamen. Nutze diesen Skill, wenn der Nutzer um Untertitel, Subtitles, SRT, eine Transkription oder Übersetzung eines Videos bittet — auch bei englischen Formulierungen wie "create subtitles", "subtitle this video", "transcribe and translate". Deckt sowohl aktuelle Aufnahmen in guter Qualität als auch verrauschte Digitalisate analoger Quellen (VHS, S-VHS, Kassette) ab.
---

# Deutsche Untertitel erstellen und muxen

Erzeugt aus einer Video-/Audiodatei deutsche Untertitel und liefert ein MKV, das Bild,
Ton und Untertitelspur enthält. Zielgruppe sind private Aufnahmen; **markierte
Unsicherheiten sind akzeptabel und ausdrücklich erwünscht** — erfundene Glättung ist es
nicht.

## Grundregeln

- **Untertitelsprache ist immer Deutsch.** Die Sprache im Video wird erfragt (Schritt 1).
- **Whisper transkribiert nur, es übersetzt nicht.** Whispers `task=translate` kann
  ausschließlich nach Englisch. Die Übersetzung ins Deutsche machst du selbst aus dem
  Transkript in der Originalsprache. Ist die Originalsprache Deutsch, entfällt das.
- **Nie raten.** Was sich nicht belegen lässt, wird als Marker ausgewiesen, z. B.
  `[unverständlich]` oder `[Gespräch über X – Wortlaut unklar]`. Eine flüssige
  Formulierung, die mehr Sicherheit suggeriert als der Ton hergibt, ist ein Fehler.
- **Ausgabe trägt den Basisnamen der Quelle**: `<name>.mkv` plus `<name>.de.srt` daneben.
- Leistungsstarke GPU vorausgesetzt (Whisper `large-v3` in fp16). Rechenzeit ist kein
  Argument, Genauigkeit schon.

Alle Skripte liegen in `scripts/` neben dieser Datei. Sie sind eigenständig lauffähig
und geben lesbare Diagnosen aus:

| Skript | Zweck | Schritt |
|---|---|---|
| `probe_audio.py` | Tonspur analysieren, Qualitätsklasse bestimmen | 2 |
| `prepare_audio.py` | 16 kHz Mono-WAVs erzeugen | 3 |
| `transcribe.py` | Dekodieren (`full`, `windows`, `zoom`) | 4 |
| `check_coverage.py` | verschluckte Passagen aufspüren | 4b |
| `patch_words.py` | nachdekodierte Stellen einspleißen | 4b |
| `segment_cues.py` | Wortzeiten zu Cue-Einheiten gruppieren | 6 |
| `build_srt.py` | SRT schreiben und normalisieren | 6 |
| `check_srt.py` | SRT validieren | 6 |
| `mux_mkv.py` | Untertitelspur in MKV muxen | 7 |

**Dateinamen unter Windows.** Videodateien aus Downloads tragen oft Emoji und Sonderzeichen
im Namen. Über das Bash-Tool kommen die als `?` an, und ffprobe meldet `No such file or
directory`. Nimm für alles, was den Quellpfad anfasst, das PowerShell-Tool und hol den Pfad
über `Get-ChildItem`, statt ihn zu tippen:

```powershell
$f = Get-ChildItem "C:\Users\Michael\Downloads\*.mp4" | Select-Object -First 1
python scripts/probe_audio.py $f.FullName
```

Der Arbeitsordner im Scratchpad hat einen harmlosen Namen — dort ist Bash weiter bequemer,
etwa für Python-Einzeiler zur Diagnose. Bei diesen `PYTHONIOENCODING=utf-8` setzen, sonst
scheitert `print` an ungarischen Zeichen wie `ő`.

## Schritt 1 — Sprache erfragen

Frage **immer** per AskUserQuestion nach der gesprochenen Sprache, bevor du transkribierst.
Biete die plausibelsten Sprachen als Optionen an (Dateiname, Ordnerkontext und bisheriges
Gespräch als Hinweis) und stelle „Automatisch erkennen" als eine der Optionen bereit.

Automatische Erkennung ist nur die zweite Wahl: Bei verrauschtem Material rät Whisper die
Sprache oft falsch, und eine falsch geratene Sprache ruiniert den gesamten Durchlauf.

## Schritt 2 — Tonspur analysieren

```bash
python scripts/probe_audio.py "<video>"
```

Das Skript meldet Container- und Streamdaten, Pegel, geschätzten Störabstand, den
Stereo-Kanalvergleich, ein Pausenprofil und leitet daraus eine **Qualitätsklasse A, B
oder C** samt empfohlener Filterkette ab.

| Klasse | Typisch für | Vorgehen |
|---|---|---|
| **A** | Digitale Aufnahme, klarer Ton, SNR hoch | Ein Durchlauf, Segment-Timings direkt übernehmen |
| **B** | Brauchbar, aber leise/dumpf | Aufbereitetes Audio, ein Durchlauf, Stichproben gegenprüfen |
| **C** | Analog-Digitalisat, verrauscht, mehrere Sprecher | Mehrere Tonvarianten, Fensterlauf, Konsensbildung |

Die Klasse ist ein Vorschlag, kein Urteil. Wenn der erste Durchlauf einer als A
eingestuften Datei offensichtlichen Unsinn liefert, behandle sie wie C. Und umgekehrt:
Eine als C gemeldete Datei, deren erster Durchlauf flüssigen, in sich stimmigen Text
liefert, ist keine C — dann den A/B-Weg über Wortzeiten nehmen.

### Wann die Messung in die Irre führt

Der Störabstand ist RMS minus Rauschboden. Beide Größen setzen voraus, dass die Datei
durchgehend Sprache enthält und zwischen den Sätzen wirklich still wird. Ist das nicht
so, misst das Verfahren etwas anderes, als der Name sagt:

- **Ein Vorspann verzerrt den Durchschnitt.** Musik, Applaus oder eine Standbildtafel
  „Wir starten in Kürze" gehen voll in Pegel und Rauschboden ein. Beobachtet: ein
  20-Minuten-Video mit 4:37 Musik-Intro wurde als Klasse C gemeldet, obwohl der
  Sprachteil sauberstes Klasse-A-Material war.
- **Ohne echte Stille ist der „Rauschboden" kein Rauschen.** Bei Außenaufnahmen (Ufer,
  Straße, Halle) und bei durchgehender Rede ohne Pausen liegt der leiseste gemessene
  Moment nicht bei Grundrauschen, sondern bei Umgebungsgeräusch oder leiser Sprache. Der
  Störabstand fällt dadurch dramatisch aus — im genannten Video 6,2 dB im Sprachteil,
  bei tadelloser Verständlichkeit.

Deshalb gibt `probe_audio.py` ein **Pausenprofil** aus: die Zahl der bei −32, −28, −24
und −20 dB erkennbaren Sprechpausen. Findet es bei −32 dB keine, enthält die Aufnahme
keine echte Stille; das Skript weist die Störabstandszahl dann ausdrücklich als nicht
belastbar aus und empfiehlt einen Probelauf statt des vollen Klasse-C-Aufwands.

Den Sprachteil gezielt nachmessen, wenn ein Vorspann im Spiel ist:

```bash
python scripts/probe_audio.py "<video>" --from 300 --to 600
```

Merke dir den gemeldeten Wert `--silence-db` — Schritt 4 braucht ihn.

## Schritt 3 — Audio aufbereiten

```bash
python scripts/prepare_audio.py "<video>" --outdir <workdir> --profile <A|B|C>
```

Erzeugt 16 kHz Mono-WAVs. Bei Klasse A nur eine unbearbeitete Spur, bei B eine
aufbereitete, bei C vier Varianten (`raw`, `clean`, `gentle`, `left`). Der Sinn mehrerer
Varianten: Was über unterschiedlich gefilterte Spuren hinweg gleich bleibt, ist echt —
was nur in einer Variante auftaucht, ist meist ein Filterartefakt.

Lege den Arbeitsordner im Scratchpad an, nicht neben dem Video.

## Schritt 4 — Transkribieren

Ein Skript, drei Modi, ein einziger Modell-Ladevorgang pro Aufruf:

```bash
# Vollständiger Durchlauf über eine oder mehrere Varianten
python scripts/transcribe.py <workdir> --mode full --variants clean --lang hu --out full.txt

# Überlappende Kurzfenster über alle Varianten (Klasse C)
python scripts/transcribe.py <workdir> --mode windows --variants clean gentle left \
    --lang hu --window 20 --step 15 --out windows.txt

# Gezielte Nachprüfung einzelner Stellen, optional zeitgedehnt
python scripts/transcribe.py <workdir> --mode zoom --variants clean gentle \
    --lang hu --spans "130-150@0.75" "725-745@0.7" --out zoom.txt
```

**Klasse A/B:** `--mode full` genügt. Für die Timings aber **immer zusätzlich mit
`--words` laufen lassen**:

```bash
python scripts/transcribe.py <workdir> --mode full --variants raw --lang hu \
    --words --max-chunk 300 --out words.txt --json words.json
```

Die Segmentzeiten der Langform-Dekodierung kollabieren regelmäßig gegen Ende einer Datei
— beobachtet wurden 150-Zeichen-Sätze mit 0,44 s Dauer und Segmente, deren Ende vor dem
Start liegt. Wortzeiten haben dieses Problem nicht und sind die verlässliche Grundlage.

**`--max-chunk` bei langen Dateien.** Bis etwa 25 Minuten läuft der Volldurchlauf am
Stück. Bei 42 Minuten bricht er hart ab — Exitcode 5, kein Traceback, keine Fehlermeldung,
die Ausgabedatei bleibt leer. Es ist kein VRAM-Problem (32 GB waren fast frei).
`--max-chunk 300` schneidet die Spur intern an erkannten Sprechpausen in Blöcke von rund
fünf Minuten, dekodiert Block für Block mit einem einzigen Modell-Ladevorgang und rechnet
die Zeitstempel auf die absolute Zeitachse zurück. Das Skript warnt von sich aus, wenn
eine Datei über 30 Minuten ohne `--max-chunk` läuft.

**Die Blockgrenzen sind der wunde Punkt.** Sie werden über `silencedetect` gesucht, und
ein fester Schwellwert passt nicht zu jeder Aufnahme: Bei einer Aufnahme am Flussufer lag
der Grundpegel über −32 dB, es wurde also **keine einzige** Sprechpause gefunden. Das
Skript fiel auf einen einzigen Block zurück, und genau der brachte den Dekoder zum
Absturz — `--max-chunk` war gesetzt und wirkungslos. Die Meldung `raw.wav: 1 Bloecke` bei
einer 15-Minuten-Datei ist das Warnzeichen.

`find_cut_points` probiert deshalb −32, −28, −24 und −20 dB durch, bis genug Pausen
zusammenkommen, und meldet, wenn die Blöcke trotzdem zu groß bleiben. Den von
`probe_audio.py` gemeldeten Wert kannst du direkt vorgeben:

```bash
python scripts/transcribe.py <workdir> --mode full --variants raw --lang hu \
    --words --max-chunk 200 --silence-db -24 --out words.txt --json words.json
```

Bricht der Durchlauf trotzdem ab, schneide die Blöcke selbst mit ffmpeg, transkribiere
jeden für sich in einem eigenen Unterordner und addiere den Blockstart anschließend auf
die Wortzeiten. Das ist der letzte, immer funktionierende Ausweg; lies dabei jede
Blocknaht einmal gegen, damit dort kein Wort fehlt oder sich doppelt.

**Sprecharme Vorspänne vorher abschneiden.** Ein Musik-Intro liefert keine Wörter, kostet
aber Rechenzeit und provoziert Floskel-Halluzinationen. Schneide es weg, transkribiere
nur den Sprachteil und addiere den Offset auf die Zeiten:

```bash
ffmpeg -y -v error -i <workdir>/raw.wav -ss 270 <workdir>/sp/raw.wav
```

Zoom-Spans dürfen **höchstens 30 Sekunden** lang sein. Darüber schaltet die Kurzclip-
Pipeline auf Langform-Dekodierung um und bricht mit `ValueError: more than 3000 mel input
features` ab. `transcribe.py` weist überlange Spans jetzt vorab ab.

### Schritt 4b — Abdeckung prüfen (Klasse A/B, nicht optional)

```bash
python scripts/check_coverage.py words.json
```

**Der Langform-Dekoder verschluckt gelegentlich ganze Passagen, ohne das zu melden.** In
einer 42-Minuten-Datei traf es zwei Stellen von je rund 28 Sekunden — einmal direkt die
Begrüßung am Dateianfang, einmal einen inhaltlich tragenden Abschnitt in der Mitte. Der
zurückgelieferte Text las sich an beiden Stellen völlig flüssig; nichts im Transkript
deutete auf den Verlust hin. Kleinere Blöcke helfen nicht zuverlässig dagegen: Der Ausfall
am Dateianfang trat auch bei einem 5,5-Minuten-Block und bei einem 47-Sekunden-Clip auf,
erst ein Clip unter 30 Sekunden (Kurzform-Dekodierung) förderte den Text zutage.

Sichtbar wird so ein Ausfall nur an der Zeitachse: Die Wörter dünnen aus, oder ein
einzelnes Wort trägt plötzlich einen Zeitstempel über eine halbe Minute. Genau darauf
prüft `check_coverage.py` — dünn besetzte Zeitfenster, Lücken zwischen Wörtern und
stehengebliebene Wörter. Das Skript endet mit Exitcode 1, solange es Verdachtsstellen gibt.

Nicht jede Meldung ist ein Fehler: Ein Musik-Intro erscheint als Folge von Fenstern mit
0 Wörtern, eine Atempause als Lücke von 3 Sekunden. Beides ist erklärbar und braucht
keine Reparatur — erklären musst du es aber, statt es zu übergehen.

Jede gemeldete Stelle einzeln reparieren:

```bash
# 1. Bereich großzügig als eigenen Clip schneiden
ffmpeg -y -v error -i <workdir>/raw.wav -ss 1900 -to 1996 <workdir>/g1/raw.wav

# 2. Clip für sich dekodieren
python scripts/transcribe.py <workdir>/g1 --mode full --variants raw --lang hu \
    --words --out g1.txt --json <workdir>/g1/words.json

# 3. In die Zeitachse einsetzen (Offset = der -ss Wert)
python scripts/patch_words.py words.json words_final.json \
    --patch <workdir>/g1/words.json 1900 1905 1994 --drop-after 2493

# 4. Erneut prüfen
python scripts/check_coverage.py words_final.json
```

Wenn der Reparaturclip die verschluckte Stelle wieder verschluckt, schneide ihn **kürzer
als 30 Sekunden**. Dann dekodiert Whisper in Kurzform, und die Kurzform hat den Fehler
nicht. Für längere Passagen den Bereich in mehrere Clips unter 30 s zerlegen und nacheinander
einspleißen.

Die Nahtstellen (`FROM`/`TO`) in eine Sprechpause legen, nicht mitten in ein Wort — sonst
fehlt oder doppelt sich dort ein Wort. `patch_words.py` entfernt Dopplungen an der Naht
und hält die Zeitachse monoton, kann aber kein Wort erfinden, das keine Seite geliefert
hat. Nach dem Einsetzen die Naht einmal mit Read gegenlesen.

`--drop-after` wirft alles ab einer Sekunde weg — gedacht für den halluzinierten Abspann
am Dateiende. Nicht stattdessen nach Textmustern filtern: Ein Filter auf `amara` löscht
auch das ungarische Wort `Hamarabb`.

**Klasse C:** Erst `--mode full` über zwei Varianten für den Zusammenhang, dann
`--mode windows` über alle Varianten. Übernimm nur, was in mehreren Varianten
übereinstimmt. Danach `--mode zoom` mit `@0.7`–`@0.8` auf alle Stellen, die inhaltlich
tragend, aber noch wackelig sind. Zeitdehnung löst erstaunlich viel auf.

Lies bei langen Aufnahmen die Ausgabedateien mit Read, nicht über die Konsole — sie
werden schnell sehr groß.

### Halluzinationen erkennen

Bei Rauschen und in sprecharmen Passagen erfindet Whisper Floskeln. Typisch sind
Abo-/Danke-Formeln der Trainingsdaten (ungarisch „Köszönöm, hogy megnéztétek!", deutsch
„Untertitel von ...", englisch „Thanks for watching") sowie Wortwiederholungen über
mehrere Zeilen. `transcribe.py` markiert verdächtige Segmente mit `⚠`.

Solche Stellen kommen **nicht** in die Untertitel. Setze dort einen Marker.
Details und weitere Gegenmittel: `reference/noisy-sources.md`.

Die Abo-Floskel steht typischerweise **hinter** dem letzten echten Wort, abgesetzt durch
eine Pause. Sie erscheint auch bei sauberen digitalen Quellen der Klasse A, nicht nur bei
Rauschen. `check_coverage.py` meldet sie als Lücke plus stehengebliebenes Wort;
weggeschnitten wird sie mit `patch_words.py --drop-after <Sekunde>`.

## Schritt 5 — Videobilder als Kontext

Zieh bei Unklarheiten Standbilder heran:

```bash
ffmpeg -y -v error -ss <sek> -i "<video>" -frames:v 1 -vf "scale=640:-1" "<workdir>/f<sek>.jpg"
```

Schauplatz, Anzahl der Personen, Datumseinblendungen und sichtbare Gegenstände klären
regelmäßig, was der Ton offenlässt. Das kostet Sekunden und ist oft entscheidend.

## Schritt 6 — Untertitel bauen

**Klasse A/B** — aus den Wortzeiten ein Cue-Gerüst schneiden lassen. Verwende die Datei,
die `check_coverage.py` fehlerfrei durchlaufen hat:

```bash
python scripts/segment_cues.py words_final.json cues_src.json --max 3.5 --hard-max 6.5
```

`segment_cues.py` schneidet an Satzenden, an Kommagrenzen sobald eine Einheit lang wird,
und an Sprechpausen. Ergebnis ist eine JSON-Liste mit exakten Zeiten, deren `text` noch
die Originalsprache enthält. **Ersetze jeden `text` durch die deutsche Übersetzung** und
lass die Zeiten unangetastet.

Achte dabei auf die Länge: Mehr als rund 90 Zeichen passen nicht in zwei Zeilen. Kürze
lieber die Formulierung, als den Cue zu überfüllen — Untertitel dürfen straffen.

Bei mehreren hundert Cues schreibe die Übersetzung nicht als JSON, sondern als schlichte
`<Index>|<deutscher Text>`-Zeilen in mehrere Textdateien und führe sie mit einem kleinen
Skript im Arbeitsordner mit `cues_src.json` zusammen. Das spart viel Schreibarbeit und
macht das Nachkürzen einzelner Cues zu einer Ein-Zeilen-Änderung. Prüfe beim Zusammenführen,
dass jeder Index genau einmal vorkommt und keiner fehlt — ein verrutschter Index verschiebt
den Text gegen das Bild, ohne dass eines der Skripte das merken könnte.

**Klasse C** — Segmentzeiten des Volldurchlaufs als Raster nutzen und die Cues von Hand
schreiben. Das Fenster-Raster aus Schritt 4 ist zum Timing **zu grob**; es dient der
Textfindung, nicht der Synchronisation.

Dann in beiden Fällen:

```bash
python scripts/build_srt.py cues_de.json "<name>.de.srt"
```

`build_srt.py` normalisiert: bricht auf maximal zwei Zeilen à ~45 Zeichen um, erzwingt
Mindest- und Maximaldauer, entfernt Überlappungen und nummeriert durch. Text wird dabei
**nie gekürzt** — passt er nicht, meldet das Skript den Cue zum Aufteilen. Die gemeldeten
Cue-Nummern sind 1-basiert und beziehen sich auf die SRT-Datei; hast du beim Übersetzen
Cues ausgelassen, stimmen sie nicht mehr mit den Indizes in `cues_src.json` überein.
Kürzen und neu bauen, bis die Warnung verschwindet.

Lange zusammengesetzte Substantive sind der häufigste Grund, warum ein Cue nicht umbricht,
obwohl er unter 90 Zeichen liegt — „Verteidigungs-Arbeitsgruppe" oder
„Wasserwirtschaftsexperten" passen in keine 45-Zeichen-Zeile. Dort hilft nur ein kürzeres
Wort, kein kürzerer Satz.

Redaktionelle Regeln:

- Ein Sprecherwechsel innerhalb eines Cues wird mit `–` am Zeilenanfang der Antwort
  markiert.
- Unsichere Stellen als Marker in eckigen Klammern, sichtbar für den Zuschauer.
- Bei nicht wörtlich belegbaren Aufnahmen (Klasse C) einen kurzen Hinweis-Cue an den
  Anfang setzen, dass es sich um eine sinngemäße Übersetzung handelt.

Dann validieren:

```bash
python scripts/check_srt.py "<name>.de.srt" --media-duration <sek>
```

Muss fehlerfrei durchlaufen, bevor gemuxt wird.

## Schritt 7 — Muxen

```bash
python scripts/mux_mkv.py "<video>" "<name>.de.srt" --audio-lang hu
```

Kopiert Video und Audio ohne Neukodierung (`-c copy`), hängt die Untertitel als SubRip an,
setzt `language=deu`, einen sprechenden Spurtitel und die Default-Disposition.

Das Skript prüft vorher den freien Speicherplatz — ein Remux braucht noch einmal die volle
Dateigröße. Heißt die Quelle bereits `.mkv`, schreibt es `<name>.sub.mkv`, um die Quelle
nicht zu überschreiben.

Zum Abschluss gegenprüfen, dass die Spur im Container sauber angekommen ist:

```bash
ffprobe -v error -show_entries "stream=index,codec_type,codec_name:stream_tags=language,title" \
    -of default=noprint_wrappers=1 "<name>.mkv"
```

## Was du dem Nutzer berichtest

- Pfade zu MKV und SRT, Anzahl der Cues, Dauer.
- Die ermittelte Qualitätsklasse und was daraus folgte.
- **Ob der Durchlauf Passagen verschluckt hatte und wo** — mit Zeitbereich, auch wenn sie
  repariert wurden. Der Nutzer soll wissen, an welchen Stellen der Text aus einem zweiten
  Anlauf stammt.
- **Welche Abschnitte nicht rekonstruierbar waren** — mit Zeitbereich. Das ist die
  wichtigste Information, wenn jemand die Aufnahme kennt und die Lücke schließen kann.
- Inhaltlich heikle oder überraschende Funde ausdrücklich benennen, samt Hinweis, wie gut
  sie belegt sind.
- Keine Genauigkeit behaupten, die das Material nicht hergibt.

## Schritt 8 — Neue Erkenntnisse anbieten

Dieser Skill ist aus Fehlschlägen gewachsen: Jede Warnung und jeder Grenzwert darin steht
für einen Durchlauf, der einmal schiefgegangen ist. Halte das am Laufen.

**Wenn ein Durchlauf dich etwas gelehrt hat, das beim nächsten Mal Zeit spart, biete am
Ende an, es hier aufzunehmen.** Anbieten, nicht ungefragt umbauen — und erst, wenn die
Untertitel fertig sind. Mitten in der Arbeit ist der Skill nicht das Thema.

Aufnahmewürdig ist, was sich auf andere Dateien überträgt:

- Ein Skript scheitert auf eine Weise, die hier nicht beschrieben ist — besonders bei
  stillem Abbruch oder falschem Ergebnis ohne Fehlermeldung.
- Ein fester Wert im Skript passt zu einer Quellenart nicht (Schwellwerte, Blockgrößen,
  Fenstergrößen, Filterketten).
- Eine Quelle verhält sich anders, als die Klassen A/B/C es vorsehen.
- Ein Workaround, den du improvisieren musstest, weil kein Skript den Fall abdeckte.
- Eine Aussage hier stimmt nachweislich nicht mehr.

Nicht aufnehmen: Eigenheiten genau dieser einen Aufnahme, Inhaltliches zum Video,
Vermutungen ohne Beleg. Der Skill soll knapp bleiben — jede Zeile, die niemandem einen
Fehlschlag erspart, macht die wichtigen Zeilen schwerer auffindbar.

So anbieten, dass der Nutzer ohne Rückfrage entscheiden kann:

- Was ist passiert, mit den konkreten Zahlen aus diesem Durchlauf (Pegel, Sekunden,
  Exitcode, Blockgrößen). Ein Beispielwert ist mehr wert als eine allgemeine Regel.
- Was würdest du ändern und wo — `SKILL.md`, ein Skript oder `reference/noisy-sources.md`.
- Ob es eine Ergänzung der Doku ist oder eine Korrektur am Code.

Prüfe eine Skriptänderung am realen Fall nach, bevor du sie als erledigt meldest. Beim
Chunker sah eine plausible Korrektur zunächst richtig aus und half trotzdem nicht — sie
zählte Sprechpausen, statt die entstehende Blocklänge zu messen. Erst der Gegentest an
der Datei, die den Fehler ausgelöst hatte, brachte das ans Licht.
