---
name: podcast
description: Macht aus einem Video oder einer Audiodatei einen deutschen Podcast als FLAC — nur Ton, ohne Bild und ohne den Originalton darunter. Nimmt auch eine YouTube- oder sonstige URL und lädt dann allein die Tonspur. Transkribiert, übersetzt fürs Hören, trennt die Sprecher und synthetisiert mit F5-TTS, wobei jeder Sprecher seine eigene geklonte Stimme behält. Passagen ohne verwertbare Sprache — Vorspannmusik, Applaus, Abspann — werden herausgeschnitten. Nutze diesen Skill, wenn der Nutzer aus einem Video einen Podcast, eine Hörfassung, eine reine Tonfassung oder etwas zum Nebenbeihören machen will — auch bei englischen Formulierungen wie "turn this into a podcast", "audio only version", "I just want to listen to it". Gedacht für politische Interviews und Debatten, bei denen das Bild nur die Sprechenden zeigt. Erzeugt bewusst KEIN Video (voiceover), KEINE Untertitel (create-subs) und KEINE Zusammenfassung (summarize-video).
---

# Deutschen Podcast aus einem Video machen

Erzeugt aus einer fremdsprachigen Video- oder Audioquelle eine deutsche Hörfassung
als **FLAC, 48 kHz, Stereo**. Im Ergebnis steht nur die deutsche Sprache: kein Bild,
kein Originalton, keine Musik, keine Pausen ohne Inhalt.

**Das Verfahren stammt aus dem Skill `voiceover`** — Transkription, Sprechertrennung,
Stimmklone und Stimmarchiv sind dieselben, und die meisten Skripte werden von dort
aufgerufen statt kopiert. Dieser Skill beschreibt nur, was anders läuft. Was hier
nicht steht, steht dort; bei einer Frage zu Whisper, zu Referenzclips oder zum
Stimmarchiv liest du `../voiceover/SKILL.md`.

## Was hier anders ist als beim Voice-over

Alle vier Unterschiede kommen aus einer einzigen Tatsache: **es gibt kein Bild, in
das etwas passen muss.**

| | voiceover | podcast |
|---|---|---|
| Ausgabe | MKV mit Bild, deutschem Mix und Originalton | FLAC, nur die deutsche Sprache |
| Zeitachse | jede Einheit sitzt auf ihrer Originalzeit | Einheiten hängen aneinander, Pausen werden neu gesetzt |
| Zeichenbudget | begrenzt jede Einheit, `measure_rate.py` misst dafür die Klonrate | entfällt vollständig |
| Passagen ohne Sprache | bleiben stehen, der Originalton trägt sie | werden vor der Transkription weggeschnitten |

Was das praktisch heißt:

- **Die Übersetzung ist frei.** Kein Budget, keine Kürzung aus Zeitgründen, keine
  Override-Datei für Längenkorrekturen. Du schreibst den Satz, der die Sache trifft.
- **`measure_rate.py` entfällt** und mit ihm mehrere Minuten je Stimme. Die
  Zeichendichte des Referenzclips bleibt trotzdem wichtig — sie sagt voraus, ob der
  Klon schleppt —, aber du liest sie mit `check_refs.py` ab, ohne ein Modell zu laden.
- **Nichts wird gestaucht.** F5-TTS spricht jede Einheit in seinem eigenen Tempo.
  Die Stauchungszahlen des Voice-over gibt es hier nicht, weil es nichts zu stauchen
  gibt.
- **Wie lang der Podcast wird, sagt allein der Sprachanteil aus Schritt 3.**
  Weggeschnittene Musik und gekappte Denkpausen verkürzen, die deutsche Fassung
  gerät dafür länger als das Original. Bei einer Quelle ohne Musik heben sich
  beide fast auf. Schätz das Verhältnis nicht vorab — miss es am Ende.

## Grundregeln

- **Keine Untertitel, kein Video, keine Zusammenfassung.** Wer das will, bekommt
  `create-subs`, `voiceover` oder `summarize-video`.
- **Von einer URL lädst du nur den Ton** (`fetch_source.py --audio-only`). Das Bild
  wird nirgends gebraucht und kostet das Zwanzig- bis Dreißigfache an Übertragung.
- **Nie raten.** Eine TTS liest jede eckige Klammer vor. Was du nicht verstehst,
  lässt du weg oder umschreibst es sinngemäß — und berichtest es.
- **Der Arbeitsordner liegt im Scratchpad**, auch die geladene Tonspur. Im Zielordner
  landet allein die FLAC-Datei.
- **Die Ausgabedatei bekommt einen kurzen deutschen Namen** nach denselben Regeln wie
  beim Voice-over: Kanal-Slug, Bindestrich, knapper deutscher Titel aus dem Inhalt,
  nur `a-z A-Z 0-9` und Bindestriche, Umlaute ausgeschrieben, zusammen rund 60
  Zeichen. Endung ist **`.de-pod.flac`**. Beispiel: Kanal `Magyar Péter Hivatalos`,
  Titel `Miniszterelnöki viszontválasz` → `magyarpeter-ministerpraesident-antwort.de-pod.flac`.
  Ohne bekannten Kanal entfällt das Präfix.

| Skript | Zweck | Schritt | woher |
|---|---|---|---|
| `fetch_source.py --audio-only` | nur die Tonspur laden | 0a | voiceover |
| `setup_tts.py` | F5-TTS prüfen, deutschen Checkpoint laden | 0b | voiceover |
| `probe_audio.py` | Tonspur analysieren, Qualitätsklasse bestimmen | 2 | voiceover |
| `prepare_audio.py` | gefilterte Varianten, nur bei Klasse B/C | 2b | voiceover |
| **`detect_speech.py`** | **Sprache finden, alles andere wegschneiden** | **3** | **hier** |
| `transcribe.py` | dekodieren, Wortzeiten erzeugen | 4 | voiceover |
| `check_coverage.py` | verschluckte Passagen aufspüren | 4b | voiceover |
| `patch_words.py` | nachdekodierte Stellen einspleißen | 4b | voiceover |
| **`map_words.py`** | **Wortzeiten auf die Quellzeitachse zurückrechnen** | **4c** | **hier** |
| `segment_speech.py` | Wortzeiten zu Sprech-Einheiten | 5 | voiceover |
| `embed_units.py`, `diarize_ecapa.py`, `diarize.py` | Sprecher trennen | 6 | voiceover |
| `match_voices.py` | bekannte Sprecher im Archiv wiedererkennen | 6 | voiceover |
| `check_refs.py` | Referenzclips bewerten | 6 | voiceover |
| **`screen_units.py`** | **Einheiten ohne verwertbare Sprache melden** | **7** | **hier** |
| **`export_units.py`** | **Einheiten als Übersetzungsvorlage ausgeben** | **8** | **hier** |
| **`validate_podcast.py`** | **Regeln erzwingen, Cue-JSON schreiben** | **9** | **hier** |
| **`build_podcast.py`** | **synthetisieren und zum Programm fügen** | **10** | **hier** |
| `bench_subset.py`, `synth_samples.py`, `check_intelligibility.py` | Gegenprobe | 10b | voiceover |
| **`encode_podcast.py`** | **mastern, FLAC schreiben** | **11** | **hier** |
| `archive_voice.py` | eine Stimme ins Archiv aufnehmen | — | voiceover, eigener Auftrag |

**Ein Interpreter für alles**, derselbe wie beim Voice-over: auf diesem Rechner
`C:\python\python.exe`. **`PYTHONIOENCODING=utf-8` durchgehend setzen.**

Die geliehenen Skripte rufst du über ihren Pfad auf, nicht über eine Kopie:

```bash
V=~/.claude/skills/voiceover/scripts
P=~/.claude/skills/podcast/scripts
python "$V/transcribe.py" ...
python "$P/detect_speech.py" ...
```

**Das Stimmarchiv ist dasselbe.** `match_voices.py` findet `voiceover/voices/`
über seinen eigenen Pfad, egal von wo du es aufrufst. Ein Sprecher, der dort für
das Voice-over hinterlegt wurde, klingt im Podcast genauso — und umgekehrt.
Aufgenommen wird auch hier nur auf ausdrücklichen Auftrag des Nutzers, mit
`archive_voice.py`; siehe den entsprechenden Abschnitt in `../voiceover/SKILL.md`.

## Schritt 0a — Quelle laden

```bash
python "$V/fetch_source.py" "<url>" --audio-only --outdir <workdir>
```

Alles aus Schritt 0a des Voice-over gilt unverändert — Originalspur statt Dub,
Stereo vor Surround, keine DRC-Variante, Clientrotation bei 403. Nur das Bild
bleibt weg. Gemessen an den drei Testvideos: 21, 38 und 32 MB statt einiger
hundert, jeweils unter zwanzig Sekunden.

Der Bericht nennt **Titel und Kanal** für den Ausgabenamen und die **Sprache** als
Vorgabe für Schritt 1. Sondieren ohne Download geht mit `--probe-only`.

Bringt der Nutzer eine eigene Datei mit, gilt die Warnung aus dem Voice-over:
Sonderzeichen im Dateinamen kommen über das Bash-Tool als `?` an. Dann PowerShell
und `Get-ChildItem` nehmen.

## Schritt 0b — F5-TTS aufsetzen

```bash
python "$V/setup_tts.py" <workdir>
```

Unverändert, samt Installationshinweisen (`--no-deps`) und Lizenz: der deutsche
Checkpoint steht unter **CC-BY-NC-4.0**, privat nutzbar, nicht für Veröffentlichung.

Dazu kommt für diesen Skill die Spracherkennung:

```bash
python -m pip install --no-deps silero-vad
```

Das Paket bringt sein Modell mit (rund 2 MB, JIT), lädt also nichts aus dem Netz
nach und braucht kein Token. Es rechnet auf torch, das ohnehin da ist.

## Schritt 1 — Sprache erfragen

Wie beim Voice-over: per AskUserQuestion, mit der Metadatensprache als erster
Option, aber bestätigen lassen. Entfällt, wenn der Nutzer sie genannt hat.

## Schritt 2 — Tonspur analysieren

```bash
python "$V/probe_audio.py" "<audiodatei>"
```

Liefert die Qualitätsklasse A, B oder C. **Bei Dateien über 30 Minuten dauert der
Lauf mehrere Minuten** — im Hintergrund starten und derweil Schritt 0b machen.

Für den Podcast hat die Klasse eine Folge weniger und eine mehr als beim Voice-over:

- **Weniger:** Es gibt keinen Originalton im Ergebnis, der eine schwache Stelle
  noch tragen könnte. Was du nicht verstehst, ist im Podcast schlicht weg.
- **Mehr:** Die Klasse entscheidet, worauf `detect_speech.py` in Schritt 3 angesetzt
  wird — auf die Originalspur oder auf eine gefilterte Variante.

### Schritt 2b — nur bei Klasse B oder C

```bash
python "$V/prepare_audio.py" "<audiodatei>" --outdir <workdir> --profile B
```

Bei **Klasse A** überspringst du das: `detect_speech.py` dekodiert selbst und
schreibt seine eigene 16-kHz-Datei, eine zweite Kopie derselben Spur bringt nichts.

Bei **B und C** setzt du Schritt 3 auf `<workdir>/clean.wav` statt auf die Quelle.
Die Zeitachse verschiebt sich dabei nicht, die Regionen passen also weiterhin auf
das Original — und genau darauf kommt es an, weil die Referenzclips später aus der
**ungefilterten** Quelle geschnitten werden. Ein Filter nimmt tiefe Anteile weg,
die zur Stimme gehören; das schadet dem Klon und der Wiedererkennung im Archiv.

## Schritt 3 — Sprache finden und den Rest wegschneiden

Das ist der eine Schritt, den es beim Voice-over nicht gibt.

```bash
python "$P/detect_speech.py" "<audiodatei>" --outdir <workdir>
```

Heraus kommen zwei Dateien: `speech.wav` (16 kHz Mono, die Sprachpassagen
lückenlos hintereinander) und `speech_regions.json` (wo jede davon in der Quelle
saß). Alles bis zur Transkription rechnet auf `speech.wav`, ab Schritt 4c wieder
auf der Quellzeitachse.

**Erkannt wird mit Silero VAD**, einem kleinen trainierten Sprachtor. Ein Energietor
wie `silencedetect` kann diese Aufgabe nicht: Musik ist laut, und ein Vorspann würde
vollständig als „nicht still" durchgehen. Gemessen an einer Parlamentssitzung mit
Musikvorspann — 35 Minuten Quelle, Lauf unter zwanzig Sekunden auf der CPU:

| erkannt | tatsächlich |
|---|---|
| `00:00 - 06:53` weggeschnitten | Vorspann, nur Musik |
| `34:35 - 35:11` weggeschnitten | Abspann, nur Musik |
| sieben Blöcke von 3 bis 9 s | Applaus zwischen den Reden |
| 76 % der Laufzeit behalten | die Redebeiträge |

**Das ist der Hauptgrund, warum vor der Transkription geschnitten wird und nicht
danach.** Whisper bekommt die Musik gar nicht erst zu sehen und kann darüber nichts
erfinden. Die Abo-Floskel („Köszönöm, hogy megnéztétek", „Untertitel von …") ist
genau das: ein Artefakt über Musik und Stille. Dass der Dekoder danach nur noch auf
dem Material rechnet, das Text trägt, ist die Zugabe — bei sieben Minuten Vorspann
ein Fünftel der Rechenzeit.

**Sieh dir die gemeldeten Blöcke an, bevor du weitergehst.** Das Skript nennt jeden
Schnitt ab drei Sekunden mit Zeitbereich. Vorspann, Abspann, Applaus und Umbaupausen
gehören dort hin; ein Block mitten in einer Rede nicht. Bei Zweifel dekodierst du den
Block für sich und siehst nach, ob Sprache drinsteckt:

```bash
python "$V/transcribe.py" <workdir> --mode zoom --variants raw --lang hu \
    --spans "311-330"
```

Dafür braucht es eine `raw.wav` im Arbeitsordner, also einmal `prepare_audio.py
--variants raw`. Kommt nichts als eine Floskel zurück, war der Schnitt richtig.

So geprüft an einem Ortstermin, dessen Vorspann fünf Minuten und dessen Abspann
achtzig Sekunden lang weggeschnitten wurden: Sechs Stichproben über beide Bereiche
lieferten **sechsmal dieselbe Zeile**, `Feliratok az Amara.org közösségétől`. Das
ist der Beleg in beide Richtungen — der Schnitt war richtig, und ohne ihn hätte
Whisper genau diese erfundenen Sätze in den Podcast geschrieben.

**Stellschrauben, in dieser Reihenfolge:**

| Beobachtung | Griff |
|---|---|
| Sprache am Anfang oder Ende eines Blocks abgeschnitten | `--pad 0.5` |
| Musik oder Applaus bleibt stehen | `--threshold 0.6` |
| leise oder verrauschte Quelle, ganze Sätze fehlen | `--threshold 0.35`, notfalls Klasse B fahren |
| Programm wirkt zerhackt, Atempausen fehlen | `--merge 2.0` |

`--merge` ist der unterschätzte Wert: Lücken darunter bleiben **erhalten**. Eine
Sprechpause gehört zum Vortrag, und wer sie wegschneidet, bekommt einen gehetzten
Podcast. Weggeschnitten wird nur, was länger als dieser Wert ist.

**Bei einer Quelle ohne Musik und ohne Applaus meldet das Skript fast nichts** —
im Interviewtest 98 Prozent behalten, elf Sekunden weg. Das ist der Normalfall und
kein Grund, an den Schaltern zu drehen.

## Schritt 4 — Transkribieren

```bash
python "$V/transcribe.py" <workdir> --mode full --variants speech --lang hu \
    --words --max-chunk 240 --out <workdir>/words.txt \
    --json <workdir>/words_speech.json
```

Die Variante heißt **`speech`**, weil `detect_speech.py` seine Datei so benennt und
`transcribe.py` seine Eingabe als `<workdir>/<variant>.wav` sucht. Alles andere ist
unverändert: `--max-chunk 240` (nicht 300), Blockcache im Ordner `speech_blocks/`,
Fortsetzen nach einem Abbruch durch erneuten Aufruf desselben Befehls. `--out` und
`--json` absolut ausschreiben.

### Schritt 4b — Abdeckung prüfen (nicht optional)

```bash
python "$V/check_coverage.py" <workdir>/words_speech.json
```

**Auf der Sprachzeitachse prüfen, vor `map_words.py`.** Dort bedeutet eine Lücke
noch, was sie beim Voice-over bedeutet: eine verschluckte Passage. Nach der
Rückrechnung stünden dort auch alle absichtlich entfernten Blöcke, und die Prüfung
wäre wertlos.

Reparatur wie beim Voice-over: Bereich als eigenen Clip unter 30 Sekunden schneiden,
für sich dekodieren, mit `patch_words.py` einspleißen, erneut prüfen. Die Zeiten
beziehen sich dabei auf `speech.wav`.

Die drei Erscheinungsformen der Abo-Floskel — Abspann, getarnter Aussetzer, reine
Halluzination über einer Pause — stehen im Voice-over-Skill. Hier tauchen sie
seltener auf, weil ihr bevorzugter Nährboden schon weg ist, aber die Prüfung bleibt.
Gemessen an den drei Testläufen: eine verschluckte Passage von 3,9 s in einem
21-Minuten-Video, in den beiden anderen keine.

**Nach `patch_words.py` heißt die Variante `raw`**, egal wie sie vorher hieß — das
Skript schreibt diesen Schlüssel fest. `map_words.py` im nächsten Schritt nimmt
beides an und macht daraus eine schlüssellose Liste, damit sich die Frage danach
nicht mehr stellt.

### Schritt 4c — Zeiten zurückrechnen

```bash
python "$P/map_words.py" <workdir>/words_speech.json <workdir>/speech_regions.json \
    <workdir>/words.json
```

Hast du in Schritt 4b geflickt, ist die Eingabe `words_final.json` statt
`words_speech.json` — sonst rechnest du die ungeflickte Fassung weiter.

Ab hier gelten wieder die Zeiten der Quelle. Das ist keine Kosmetik: Die
Sprechertrennung schneidet ihre Referenzclips aus der **ungefilterten Originaldatei**,
und jede Zeitangabe, die du dem Nutzer meldest, muss er im Video wiederfinden können.

## Schritt 5 — Segmentieren

```bash
python "$V/segment_speech.py" <workdir>/words.json <workdir>/units.json \
    --rate 14 --duration <sek>
```

**`--speakers` bleibt weg, `--rate` ist beliebig.** Beides steuert nur das
Zeichenbudget, und das gibt es hier nicht. Lass die 14 stehen und ignoriere die
Budgetspalte; die Schnittpunkte hängen nicht daran.

`--duration` ist die Laufzeit der **Quelle**, nicht die von `speech.wav`.

Die Verteilungskontrolle aus dem Voice-over gilt weiter: rund 8 bis 9 Einheiten je
Minute Sprache, Slot-Median um 6,5 s, deutlich weniger als ein Zehntel unter zwei
Sekunden. Rechne dabei auf die **Sprachlaufzeit** um, nicht auf die Quelllaufzeit —
bei sieben Minuten Vorspann liegen die beiden weit auseinander.

## Schritt 6 — Sprecher trennen

Unverändert aus dem Voice-over, mit einer Auslassung am Ende. Der Ablauf:

1. **Trennen** — `embed_units.py` + `diarize_ecapa.py` (ein Raum, gleiche Mikrofone)
   oder `diarize.py` (getrennte Kanäle, Videoschalte, Telefon)
2. **Wiedererkennen** — `match_voices.py --apply`; wer im Archiv steht, ist fertig
3. **Bewerten** — `check_refs.py`, nur für den Rest
4. **Ersetzen**, wo ein besserer Clip im Video liegt
5. ~~Raten messen~~ — **entfällt**

```bash
python "$V/embed_units.py" "<audiodatei>" <workdir>/units.json <workdir>/emb.npy
python "$V/diarize_ecapa.py" "<audiodatei>" <workdir>/units.json <workdir>/emb.npy \
    <workdir>/refs --speakers 2 --structure <workdir>/structure.json
python "$V/match_voices.py" <workdir>/units.json <workdir>/emb.npy \
    <workdir>/refs/speakers.json --apply
python "$V/check_refs.py" "<audiodatei>" <workdir>/units.json <workdir>/refs/speakers.json
```

**Die Audiodatei ist hier immer die Quelle**, auch wenn du in Schritt 3 eine
gefilterte Variante benutzt hast. Für die Wiedererkennung ist das gemessen wichtig:
Der Filter drückt die Ähnlichkeit gegen das Archiv (0,88 auf 0,76 in einem Fall),
weil die gespeicherten Fingerabdrücke aus ungefiltertem Ton stammen.

**Anker setzen und gegenlesen** ist hier genauso Pflicht wie beim Voice-over — wer
namentlich aufgerufen wird, wer über wen in der dritten Person spricht. Ohne Bild
ist die Stimme das **einzige** Merkmal, an dem der Hörer die Sprecher auseinanderhält;
eine vertauschte Zuordnung fällt hier härter auf als in einer Fassung mit Bild.

**Eingespielte Clips und Fragesteller** nagelst du wie dort über `inserts` in der
Strukturdatei fest. Bei einer Parlamentssitzung ist das der Normalfall: Der
Präsident ruft auf, der Redner spricht, der Präsident schließt.

### Wenn ein Cluster zwei Personen enthält

`check_refs.py` beantwortet nur die Frage, ob ein Clip als Klonvorlage taugt. Ob
er die **richtige** Person zeigt, sieht es nicht — dafür müsste es den Text lesen.
Ein Cluster, das zwei Sprecher verschmolzen hat, bekommt deshalb ein „gut" und
verteilt die Stimme des einen an die Sätze des anderen.

Bei wenigen langen Redebeiträgen passiert das kaum. Bei vielen kurzen O-Tönen —
Nachrichtensendung, Straßenumfrage, Beitrag mit drei Statements — ist es der
Normalfall, weil ein Cluster je Person schlicht nicht genug Sekunden findet. Die
Ankertreue verrät es nicht: Sie misst nur die Einheiten, für die du einen Anker
gesetzt hast, und ein namenloser Passant hat keinen.

**Gefunden wird es allein beim Gegenlesen des Exports aus Schritt 8.** Geh die
Spalte Sprecher gegen den Text durch und frag bei jedem Wechsel, ob die Person zum
Inhalt passt. Ein Minister, der plötzlich über sein gestohlenes Fahrrad spricht,
sitzt im Cluster eines Passanten.

Die Reparatur ist ein eigener Sprecher, kein Umhängen auf einen bestehenden:

```bash
ffmpeg -v error -y -ss <start> -t <dauer> -i "<quelle>" -ac 1 -ar 24000 \
    <workdir>/refs_<n>/spk<neu>.wav
```

Schnittstelle ist eine Einheit dieser Person mit **Satzgrenze an beiden Enden**, unter elf
Sekunden, aus einer dichten Passage — dieselben Kriterien wie beim Ersatzclip oben.
Dann trägst du in `speakers.json` einen Eintrag mit dem nächsten freien Index nach
(`speaker`, `name`, `ref_file`, `ref_text`, `ref_unit`) und setzt die betroffenen
Positionen in `labels` auf diesen Index. Ein Cluster, das dabei alle Einheiten
verliert, nimmst du aus `speakers` heraus.

**Häng die Einheiten nicht auf einen benachbarten Sprecher um, nur weil der
thematisch näher liegt.** Zwei Passanten klingen dann identisch, und der Hörer
schließt daraus, es sei dieselbe Person — eine Aussage, die die Quelle nicht macht.
Ein eigener Clip kostet zwanzig Sekunden.

### Warum die Ratenmessung entfällt und was trotzdem bleibt

`measure_rate.py` misst, wie dicht ein Klon spricht, damit `segment_speech.py`
daraus Zeichenbudgets rechnen kann. Ohne Budgets ist die Zahl unbenutzt, und die
Messung kostet mehrere Minuten je Stimme.

**Die Zeichendichte des Referenzclips bleibt trotzdem das wichtigste Merkmal**, denn
sie sagt die Klonrate fast eins zu eins voraus, und ein zu langsamer Clip macht den
ganzen Podcast schleppend — hier sogar folgenloser als beim Voice-over und deshalb
leichter zu übersehen, weil keine Stauchungszahl mehr Alarm schlägt. `check_refs.py`
gibt sie aus, ohne ein Modell zu laden; wie es die Werte einstuft, steht im
Voice-over-Skill unter „Referenzclips bewerten, bevor du sie von Hand prüfst".

Es gelten also unverändert: Der Clip muss an einer **Satzgrenze beginnen und enden**, unter elf
Sekunden liegen und aus einer **dichten** Passage stammen, nicht aus der längsten.
Die Suchabfrage nach Dichte steht im Voice-over-Skill unter „Welche Einheit du als
Ersatz nimmst".

## Schritt 7 — Einheiten sichten

```bash
python "$P/screen_units.py" <workdir>/units.json \
    --regions <workdir>/speech_regions.json
```

Schritt 3 hat entfernt, was ein Sprachtor sicher erkennt. Übrig bleibt der
schwierigere Rest: Applaus mit einem Zwischenruf darin, das Raunen eines Saals, ein
Takt Musik, der sich an den ersten Satz drängt. Whisper beantwortet solche Stellen
mit Text, und dieser Text liest sich plausibel genug, um versehentlich übersetzt zu
werden.

Das Skript löscht nichts. Es meldet Kandidaten mit Begründung:

| Meldung | Bedeutung |
|---|---|
| **Floskel-Halluzination** | eine Abo- oder Untertitelfloskel; das stärkste Signal |
| **Wiederholungsschleife** | dasselbe Fragment mehrfach; fast immer Rauschen |
| **gedehnt** | wenige Zeichen über viele Sekunden; das Musikartefakt |
| **Randlage** | kurze Einheit direkt an einer Schnittkante |
| **Regionen fast ohne Text** | eine ganze Region trägt kaum Zeichen |

**Die Entscheidung bleibt bei dir, und sie ist nicht symmetrisch.** Einen echten
Satz zu verwerfen ist schlimmer, als einen Takt Musik stehen zu lassen — der Hörer
merkt eine fehlende Aussage nie, ein sinnloses Halbwort dagegen sofort als Fehler,
aber er kann es einordnen. Lies jede Meldung im Zusammenhang der Nachbareinheiten
nach. Eine kurze Zwischenfrage ist kurz, und ein Sprecher, der abbricht, hinterlässt
eine dünne Einheit.

Was wirklich keine Sprache ist, bekommt in Schritt 8 die Zeile `<index>|-` und
fällt damit aus dem Podcast.

## Schritt 8 — Übersetzen, fürs Hören

Exportier die Originalsprache mit Zeitmarke und Sprecher, eine Zeile je Einheit:

```bash
python "$P/export_units.py" <workdir>/units.json     --speakers <workdir>/refs/speakers.json --out <workdir>/source.txt
```

```
<index>|<mm:ss>|<sprecher>|<originaltext>
```

Die Sprecherspalte ist kein Schmuck: Dieselbe Zeile liest sich anders, je nachdem
ob der Moderator fragt oder der Gast antwortet.

**Der Index zählt ab null.** `validate_podcast.py` gleicht ihn gegen die Position in
`units.json` ab.

Die Regeln des Voice-over gelten weiter — **bis auf das Budget**:

- **Zahlen ausschreiben**, auch Ordinalzahlen. „im zehnten Jahrhundert",
  „siebenundachtzig Tage", „zweitausendsechs".
- **Keine Auslassungspunkte**, keine eckigen Klammern, keine Abkürzungen
  (`z. B.`, `ca.`, `%`, `/`).
- **Kurze Hauptsätze statt Schachtelsätze.** Zuhörer können nicht zurückspringen.
- **Eigennamen nach `../voiceover/hungarian.md` umschreiben**, den Vornamen nur bei
  der ersten Nennung, danach den Nachnamen mit einem deutschen Wort davor.
- **Vollständige Sätze bei kurzen Einheiten.** Ein Fragment wie „Echt gute Punkte."
  kippt F5-TTS in eine Wiederholschleife. Subjekt und Verb hinschreiben.
- **Rhetorische Doppelpunkte auflösen.** „Die Frage ist: …" wird zu zwei Sätzen.

Und zwei Regeln fallen weg:

- **Kein Zeichenbudget.** Kürze nicht aus Zeitgründen. Straffen bleibt trotzdem
  richtig, wo der Sprecher sich korrigiert oder wiederholt — aber jetzt aus
  Rücksicht auf den Hörer, nicht auf die Uhr.
- **Keine Override-Datei für Längenkorrekturen.** `--override` gibt es weiterhin,
  aber nur für echte Korrekturen aus der Gegenprobe in Schritt 10b.

Schreib die Übersetzung als `<index>|<deutscher Text>` in mehrere Dateien
(`pod_01.txt`, `pod_02.txt`, …). Verworfene Einheiten bekommen `<index>|-`.

**`-` verwirft nicht nur, es fügt auch zusammen.** `segment_speech.py` trennt an
Pausen, und ein Sprecher macht seine Pausen nicht an Satzgrenzen: Ein Satz zerfällt
regelmäßig in ein Bruchstück und den Rest. Beim Voice-over müssen beide Teile Text
tragen, weil beide ihren Platz im Bild haben. Hier nicht — schreib den ganzen Satz
in die zweite Einheit und gib der ersten ein `-`. In den Testläufen betraf das drei
bis vier Einheiten je Video, und es ist der häufigste Grund für ein `-` überhaupt,
häufiger als fehlende Sprache. Das Pausenmodell in Schritt 10 fängt die entstandene
Lücke auf.

**Jeder Index muss vorkommen.** Eine vergessene Zeile ist im Podcast eine
verschwundene Aussage, und anders als beim Voice-over gibt es keinen Originalton, an
dem der Hörer die Lücke bemerkt. Deshalb prüft Schritt 9 auf Vollständigkeit und
verlangt für eine Auslassung das ausgeschriebene `-`.

## Schritt 9 — Validieren

```bash
python "$P/validate_podcast.py" <workdir>/units.json <workdir>/cues_pod.json \
    <workdir>/pod_*.txt
```

Bricht ab bei Ziffern, Auslassungspunkten, Klammern, Abkürzungen, fehlenden,
doppelten oder leeren Indizes. Meldet, welche Einheiten verworfen wurden, und
schätzt die Programmlänge aus der Zeichenzahl.

## Schritt 10 — Synthetisieren

```bash
python "$P/build_podcast.py" <workdir>/cues_pod.json <workdir>/podcast.wav \
    --ckpt <workdir>/model_f5tts_german.safetensors --vocab <workdir>/vocab.txt \
    --speakers <workdir>/refs/speakers.json
```

Jede Einheit wird in ihrem natürlichen Tempo gesprochen, von ihrer eigenen Stille
befreit und angehängt. Was die Slots des Voice-over ersetzt, ist ein **Pausenmodell**:

| Situation | Pause |
|---|---|
| innerhalb eines Redebeitrags | die Originalpause, gedeckelt bei 0,9 s |
| nach einem Satzschluss | mindestens 0,32 s |
| Sprecherwechsel | mindestens 0,45 s |
| über eine geschnittene Stelle hinweg (Originallücke ab 3 s) | 1,2 s |
| zwei Hälften eines erzwungen geteilten Satzes | mindestens 0,12 s |

Die Originalpause zu übernehmen ist richtig, sie **roh** zu übernehmen wäre falsch:
Nach Schritt 3 klafft dort, wo der Applaus war, eine Lücke von Minuten. Deshalb der
Deckel — und deshalb der ausdrückliche Abschnittstrenner, der eine geschnittene
Stelle hörbar macht, statt sie zu verschweigen.

Der Satzschluss-Boden ist die Zeile, die am meisten ausmacht. `segment_speech.py`
schließt eine Einheit am Satzende auch dann, wenn der Sprecher durchgeredet hat;
die gemessene Lücke ist dort null. Für den Podcast ist null falsch, weil jede
Einheit jetzt als eigene Äußerung mit eigenem Schlussfall gesprochen wird. Gemessen
an der Parlamentssitzung lagen 78 von rund 180 Nahtstellen auf diesem Boden — an
dieser einen Zahl hängt, ob das Programm atmet oder hetzt.

**Eine Einheit, die selbst über eine geschnittene Stelle reicht, bekommt keinen
Trenner.** Der Applaus im Testvideo lag mitten in einer Einheit, deren Wortzeiten
ihn überspannen; das Modell sieht nur Lücken *zwischen* Einheiten. Das ist richtig
so — der Sprecher redet dort im Original ja weiter — und kein Fall zum Nachregeln.

`--speed` steht auf 1,0 und bleibt dort, solange der Nutzer nichts anderes sagt.

Das Skript schreibt neben der WAV eine `<ausgabe>.timeline.json` — bei
`podcast.wav` also `podcast.wav.timeline.json`, anderer Name nur über
`--timeline`. Darin steht je gesprochener Einheit ihre Position im Podcast und
ihre Position in der Quelle. Damit beantwortest du „wo im Original war das?"
ohne zu rechnen.

**Tempo:** rund 7-fache Echtzeit auf einer RTX 5090 — gemessen 2:42, 3:38 und 3:53
Rechenzeit für 20, 24 und 25 Minuten Programm.

**Das Verhältnis von Programm zu Quelle liest du an der fertigen Datei ab**, nicht
aus einer Erfahrungszahl. Es hängt am Sprachanteil, und der reicht von einer
Parlamentssitzung mit langem Musikvorspann bis zu einer Nachrichtensendung ohne
jede Musik — weit genug, dass jede Vorabschätzung danebengreift.

### Schritt 10b — Zurücklesen lassen (nicht optional)

```bash
python "$V/bench_subset.py" <workdir>/cues_pod.json <workdir>/refs/speakers.json \
    <workdir>/bench --per-speaker 10
python "$V/synth_samples.py" <workdir>/bench_cues.json <workdir>/bench \
    --ckpt <workdir>/model_f5tts_german.safetensors --vocab <workdir>/vocab.txt \
    --speakers <workdir>/bench_speakers.json
python "$V/check_intelligibility.py" <workdir>/bench
```

**Vor der Vollsynthese laufen lassen, nicht danach.** Gelesen wird auf zwei Dinge:
Einheiten **über 100 %** (dort halluziniert die Synthese) und eine **Stimme deutlich
schlechter als die anderen** (dort ist der Referenzclip schuld, nicht der Text).
Einzelwerte zwischen zwanzig und fünfzig Prozent sind Namensrauschen und kein Befund.

Die Ursachenliste — vorangestelltes Füllwort, zu kurze Einheit, fehlendes Satzgerüst
— steht im Voice-over-Skill und gilt hier unverändert. Nur eine Ursache entfällt:
Zu langer Text kann die Synthese nicht mehr unter Zeitdruck setzen.

## Schritt 11 — Mastern und schreiben

Erst eine Hörprobe:

```bash
python "$P/encode_podcast.py" <workdir>/podcast.wav <workdir>/probe.flac --sample 300 45
```

Dann die volle Fassung in den Zielordner:

```bash
python "$P/encode_podcast.py" <workdir>/podcast.wav \
    "C:/Users/Michael/Downloads/<kanal>-<titel>.de-pod.flac" \
    --title "<deutscher Titel>" --artist "<Kanal>" --date <YYYY-MM-DD> \
    --source "<url>"
```

Zweipassige Lautheitsnormalisierung auf **−16 LUFS** bei **−1,5 dBTP**, danach
zwingend zurück auf **48 kHz** — `loudnorm` schaltet seine Ausgabe sonst auf 192 kHz,
unabhängig davon, was davor im Graphen steht. Stereo ist bewusst Doppelmono:
Geklonte Stimmen gehören in die Mitte.

Zum Abschluss gegenprüfen:

```bash
ffprobe -v error -show_entries "stream=codec_name,sample_rate,channels:format=duration" \
    -of default=noprint_wrappers=1 "<datei>.de-pod.flac"
```

Erwartet: `flac`, `48000`, `2`. Die erreichte Lautheit misst du mit

```bash
ffmpeg -v info -nostdin -i "<datei>.de-pod.flac" -af ebur128=peak=true -f null -
```

Gemessen an den drei Testläufen: −16,3, −17,1 und −17,1 LUFS bei einem Spitzenwert
von jeweils −4,5 dBFS. Ein Dezibel unter dem Ziel ist normal und kein Fehler:
`loudnorm` fällt aus der linearen in die dynamische Betriebsart, sobald die nötige
Anhebung den True Peak reißen würde, und das tut sie bei einer sehr leisen Quelle
regelmäßig.

## Was du dem Nutzer berichtest

- Pfad zur FLAC-Datei, Laufzeit, und **wie sie sich zur Quelle verhält** — „26 von
  35 Minuten" sagt mehr als eine absolute Zahl.
- **Was weggeschnitten wurde**, mit Zeitbereich und Grund: Vorspann, Abspann,
  Applaus. Der Nutzer sieht dem Ergebnis nicht an, dass dort etwas war.
- **Welche Einheiten du wegen fehlender Sprache verworfen hast** und worauf du das
  gestützt hast. Bei Unsicherheit sag es dazu — er kann die Stelle im Video prüfen.
- Qualitätsklasse und was daraus folgte.
- **Wie viele Sprecher erkannt wurden**, mit Ankertreue beziehungsweise Trennschärfe,
  welchen Weg du gewählt hast und woran du gegengelesen hast.
- **Welche Sprecher aus dem Archiv kamen**, mit Ähnlichkeitswert, und welche neu
  geschnitten wurden. Knappe Treffer nahe der Schwelle ausdrücklich nennen.
- **Ob ein Referenzclip schlecht war und es keinen besseren gab**, mit dem Befund aus
  `check_refs.py` — sonst hält der Nutzer die schwache Stimme für einen Kettenfehler.
- **Die Wortfehlerrate aus Schritt 10b, je Stimme**, und ob eine Stimme aus der Reihe
  fiel. Sie misst nicht die Aussprache, sondern Halluzination und Clipqualität.
- **Ob der Durchlauf Passagen verschluckt hatte und wo** — mit Zeitbereich, auch wenn
  sie repariert wurden.
- **Welche Abschnitte nicht rekonstruierbar waren** — mit Zeitbereich. Hier besonders
  wichtig, weil sie im Ergebnis spurlos fehlen.
- **Die Lizenz**, wenn er das Ergebnis weitergeben will: CC-BY-NC-4.0, und geklonte
  Stimmen realer Personen nicht ohne deren Einverständnis veröffentlichen.
- Inhaltlich heikle oder überraschende Funde benennen, samt Beleglage.
- Keine Genauigkeit behaupten, die das Material nicht hergibt.

## Schritt 12 — Falschaussagen und Widersprüche melden

Wie im Voice-over-Skill, und **subtraktiv**: Melde am Ende, wenn dein Durchlauf eine
Aussage hier widerlegt hat oder wenn zwei Stellen dir gegenläufige Anweisungen gegeben
haben. Die Korrektur besteht darin, die falsche oder die unterlegene Aussage zu
**entfernen**, nicht sie um einen Sonderfall zu ergänzen.

Weil dieser Skill vom Voice-over borgt, kommt ein zweiter Fall dazu: **eine Aussage,
die hier steht und dort ebenfalls.** Doppelt gepflegt wird sie nicht doppelt richtig,
sondern beim nächsten Mal widersprüchlich. Was in beiden Dateien gleich lautet, gehört
in den Voice-over-Skill und hier nur als Verweis.
