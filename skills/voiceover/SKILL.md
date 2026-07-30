---
name: voiceover
description: Erstellt eine deutsche Voice-over-Tonspur für eine Video- oder Audiodatei und muxt sie in ein MKV, mit dem Originalton gedimmt darunter. Nimmt auch eine YouTube- oder sonstige Video-URL und lädt die Quelle vorher selbst in bester Qualität herunter. Synthetisiert mit F5-TTS und klont dabei die Stimme jedes Sprechers aus dem Original, sodass in Interviews jeder seine eigene deutsche Stimme behält. Nutze diesen Skill, wenn der Nutzer um Voiceover, Voice-over, eine deutsche Sprachfassung, Synchronfassung, Vertonung oder ein "eingesprochenes" Video bittet — auch bei englischen Formulierungen wie "voice over this video", "dub this into German", "make a German audio track". Erzeugt bewusst KEINE Untertitel; dafür gibt es create-subs.
---

# Deutsche Voice-over-Tonspur erstellen und muxen

Erzeugt aus einer fremdsprachigen Video-/Audiodatei eine deutsche Sprachspur und
liefert ein MKV, das Bild, den deutschen Mix und den Originalton enthält.
Synthetisiert wird mit **F5-TTS**, das die Stimme jedes Sprechers aus dem Original
klont — in einem Interview behält damit jeder seine eigene deutsche Stimme.

## Grundregeln

- **Keine Untertitel.** Dieser Skill erzeugt keine SRT-Datei. Wenn der Nutzer
  Untertitel will, ist `create-subs` zuständig. Wenn er beides will, laufen beide
  Skills — sie teilen sich Sondierung und Transkription, ab der Segmentierung
  laufen sie auseinander.
- **Whisper transkribiert nur, es übersetzt nicht.** Whispers `task=translate`
  kann ausschließlich nach Englisch. Die Übersetzung ins Deutsche machst du selbst
  aus dem Transkript in der Originalsprache.
- **Die Übersetzung wird fürs Hören geschrieben, nicht fürs Lesen.** Das ist der
  entscheidende Unterschied zum Untertitel-Weg und der größte Hebel für Qualität.
  Details in Schritt 7.
- **Nie raten.** Was sich nicht belegen lässt, wird nicht erfunden. Anders als bei
  Untertiteln kannst du keine Marker in eckigen Klammern setzen — eine TTS liest
  sie vor. Unverständliches lässt du weg oder umschreibst es sinngemäß, und du
  berichtest es dem Nutzer.
- **Eine URL lädst du selbst herunter.** Gibt der Nutzer eine YouTube- oder andere
  Video-URL statt einer Datei, beginnt der Durchlauf mit Schritt 0a. Verlang keine
  Datei und frag nicht, ob du laden sollst.
- **Die Ausgabedatei bekommt einen kurzen deutschen Namen**, nicht den Basisnamen
  der Quelle. Quellnamen von YouTube sind lang und tragen Sonderzeichen, die unter
  Windows und in Shell-Aufrufen Ärger machen, und bei einem Download über Schritt 0a
  ist der Basisname die nichtssagende Video-ID. Bilde aus dem Inhalt einen knappen
  deutschen Titel — nur `a-z`, `A-Z`, `0-9` und Bindestriche, Umlaute ausgeschrieben
  (`ae`, `oe`, `ue`, `ss`), höchstens rund 40 Zeichen — und häng `.de-vo.mkv` an.
  Die Datei liegt im Ordner der Quelle. Nenn dem Nutzer den gewählten Namen im
  Abschlussbericht.
- **Vor den Titel kommt der Kanalname**, sobald die Quelle von YouTube oder einer
  anderen Plattform mit Kanalangabe stammt: `<kanal>-<titel>.de-vo.mkv`. Damit
  sortieren sich die Fassungen eines Kanals im Downloads-Ordner nebeneinander, und
  man sieht der Datei an, aus welcher Ecke der Beitrag kommt. Der Name steht im
  Bericht von Schritt 0a in der Zeile `Kanal:` und nachträglich in
  `<id>.info.json` unter `uploader`, ersatzweise `channel`. Slugifiziere ihn nach
  denselben Regeln wie den Titel und kürz ihn auf das unterscheidende Kernwort:
  generische Anhängsel wie `TV`, `Official`, `Channel`, `News`, `Media` oder ein
  `- Topic` fallen weg, rund 20 Zeichen sind die Grenze. `Partizán` → `partizan`,
  `Telex.hu` → `telex`, `ZDFheute Nachrichten` → `zdfheute`. Bringt der Nutzer
  eine eigene Datei mit und ist kein Kanal bekannt, entfällt das Präfix — rate ihn
  nicht aus dem Dateinamen. Beispiel: Kanal `Partizán`, Titel `Eltűntek Magyar
  Péter miniszterei az energiakrízis idején; mi történik a háttérben` →
  `partizan-magyar-minister-energiekrise.de-vo.mkv`.

| Skript | Zweck | Schritt |
|---|---|---|
| `fetch_source.py` | Quelle von einer URL laden, Originalspur wählen | 0a |
| `setup_tts.py` | F5-TTS prüfen, deutschen Checkpoint laden | 0b |
| `probe_audio.py` | Tonspur analysieren, Qualitätsklasse bestimmen | 2 |
| `prepare_audio.py` | 16 kHz Mono-WAVs erzeugen | 3 |
| `transcribe.py` | Dekodieren, Wortzeiten erzeugen | 4 |
| `check_coverage.py` | verschluckte Passagen aufspüren | 4b |
| `patch_words.py` | nachdekodierte Stellen einspleißen | 4b |
| `segment_speech.py` | Wortzeiten zu Sprech-Einheiten mit Zeitbudget | 5 |
| `diarize.py` | Sprecher trennen über MFCC — nur bei getrennten Kanälen | 6 |
| `embed_units.py` | ECAPA-Embedding je Einheit | 6 |
| `diarize_ecapa.py` | Sprecher trennen über Embeddings, an Ankern geprüft | 6 |
| `match_voices.py` | bekannte Sprecher in der Stimmbibliothek wiedererkennen | 6 |
| `check_refs.py` | Referenzclips bewerten, besseren im Video finden | 6 |
| `measure_rate.py` | Sprechrate je geklonter Stimme messen | 6 |
| `archive_voice.py` | eine Stimme ins Archiv aufnehmen — **eigener Auftrag**, siehe unten | — |
| `validate_vo.py` | VO-Regeln erzwingen, Cue-JSON schreiben | 8 |
| `build_voiceover.py` | synthetisieren und überlappungsfrei platzieren | 9 |
| `bench_subset.py` | nach Sprechern ausgewogene Stichprobe bauen | 9b |
| `synth_samples.py` | Einheiten als 16-kHz-WAVs für die Gegenprobe rendern | 9b |
| `check_intelligibility.py` | Synthese zurücklesen, Halluzinationen und Clipfehler finden | 9b |
| `mux_voiceover.py` | mischen, ducken, muxen | 10 |

**Ein Interpreter für alles.** Die Skripte brauchen F5-TTS und Whisper, beide auf
torch. Liegen sie im selben Python, laufen alle Skripte darauf. Auf diesem Rechner
ist das `C:\python\python.exe`.

**Dateinamen unter Windows.** Videodateien aus Downloads tragen oft Sonderzeichen
im Namen. Über das Bash-Tool kommen die als `?` an, und ffprobe meldet `No such
file or directory`. Das betrifft nur Dateien, die der Nutzer mitbringt — was du in
Schritt 0a selbst lädst, heißt nach der Video-ID und ist unbedenklich. Nimm für
alles, was einen mitgebrachten Quellpfad anfasst, das PowerShell-Tool und hol den
Pfad über `Get-ChildItem`, statt ihn zu tippen:

```powershell
$f = Get-ChildItem "C:\Users\Michael\Downloads\*.mp4" | Select-Object -First 1
python scripts/probe_audio.py $f.FullName
```

Der Arbeitsordner im Scratchpad hat einen harmlosen Namen — dort ist Bash bequemer.

**`PYTHONIOENCODING=utf-8` setzen, und zwar nicht nur bei Einzeilern.** Ohne das
scheitert `print` an Zeichen wie `ő`. Betroffen sind auch die Skripte selbst,
sobald der Quelltext Sonderzeichen trägt: `measure_rate.py` starb bei ungarischem
Material an cp1252, weil F5-TTS den `ref_text` vor jeder Synthese ausdruckt. Der
Traceback zeigt dabei auf `utils_infer.py`, nicht auf das Skript, und sieht
deshalb nach einem Installationsproblem aus. Setz die Variable bei allem, was
Quelltext anfassen könnte — also ab `measure_rate.py` durchgehend.

**Eine Eigenheit der Zwischendateien rät man leicht falsch:** `units.json` ist
eine **flache Liste**, kein Objekt mit Schlüssel `units`. Der Quelltext einer
Einheit steht unter `text`, unabhängig von der Quellsprache. Eine Einheit sieht
so aus:

```json
{"start": 0.0, "end": 9.86, "text": "Tisztelettel köszöntöm…", "slot": 9.94, "budget": 152}
```

Ältere Arbeitsordner tragen den Text noch unter `hu` — auch bei englischem oder
spanischem Material, der Schlüssel war nie ein Sprachcode. Die Skripte lesen
beide Formen, `--text-key` von `diarize_ecapa.py` brauchst du dafür nicht.

In `refs/speakers.json` liegen die Stimmen unter `speakers`, die Sprecherzuordnung
je Einheit daneben unter `labels` als Liste von Indizes. **`speaker` ist eine Zahl
und muss eine bleiben** — `segment_speech.py` schlägt damit in `labels` nach, und
ein Name an dieser Stelle bricht den Lauf mit `KeyError`. Der Klarname gehört in
`name`.

**Das Stimmarchiv `voices/` neben diesem Skill überlebt den einzelnen Durchlauf.**
Wiederkehrende Personen — ein Ministerpräsident, der Moderator eines Kanals —
bekommen dort einmal einen Referenzclip und klingen danach in jedem Video gleich.
Ohne das schneidet jeder Lauf einen neuen Clip, und dieselbe Person hat in zehn
Fassungen zehn Stimmen.

**Aufnehmen und Vertonen sind getrennte Aufträge.** Der Durchlauf *liest* aus dem
Archiv (Schritt 6) und schreibt nie hinein. Gefüllt wird es auf ausdrückliche
Ansage des Nutzers, mit eigenem Befehl und eigenem Abschnitt weiter unten — er
entscheidet, wer wiederkehrt und welche Passage die Person gut zeigt. Biete das
nicht von dir aus an und leite es nicht aus Messwerten ab.

## Schritt 0a — Quelle von einer URL laden

Gibt der Nutzer eine URL statt einer Datei, lädst du das Video selbst herunter —
ohne zu fragen, ob er das will, und in der höchsten verfügbaren Auflösung.

```bash
python scripts/fetch_source.py "<url>" --outdir C:/Users/Michael/Downloads
```

Vorher sondieren, wenn du erst die Sprache und die Laufzeit brauchst — das kostet
keinen Download:

```bash
python scripts/fetch_source.py "<url>" --probe-only
```

Das Skript lädt Bild und Ton getrennt in der besten Fassung und muxt sie zu MKV.
Es meldet dabei alles, was die folgenden Schritte ohnehin brauchen: Titel,
Laufzeit für die `--duration`-Argumente, Originalsprache als Vorgabe für
Schritt 1, Kapitelmarken und vorhandene Untertitel.

**Der Dateiname ist die Video-ID**, nicht der Titel. Damit entfällt für
heruntergeladene Quellen das Sonderzeichenproblem aus dem Abschnitt oben — du
kannst den Pfad tippen und brauchst kein `Get-ChildItem`. **Titel und Kanal für
den Ausgabenamen liest du aus dem Bericht des Skripts** (Zeilen `Titel:` und
`Kanal:`), nicht aus dem Dateinamen. Daneben liegt `<id>.info.json` mit allen
Metadaten, falls du sie später ohne zweiten Netzabruf brauchst — der Kanal steht
dort unter `uploader`.

### Warum die Tonspur nicht der Automatik überlassen wird

Das ist der Grund, aus dem hier ein Skript steht und nicht ein yt-dlp-Einzeiler.

- **YouTube liefert für viele Videos synchronisierte Zweitspuren.** Erwischst du
  einen Dub, klont die Pipeline anschließend Stimmen, die es im Original nicht
  gibt, und übersetzt eine Übersetzung. Der Fehler fällt erst an der fertigen
  Tonspur auf. Der Extraktor markiert die Originalspur (`language_preference` 10,
  Notiz „(original)"), das Skript nagelt genau die als Format-ID fest, statt sich
  auf die Sortierreihenfolge zu verlassen. Sind mehrere Sprachen im Angebot und
  keine als Original markiert, **bricht es ab statt zu raten** — dann Formate mit
  `python -m yt_dlp -F "<url>"` ansehen und die Spur mit `--audio-id` vorgeben.
- **Die höchste Bitrate ist hier die falsche Wahl.** YouTube bietet neben Stereo
  oft 5.1 an, gemessen 388 gegen 129 kbit/s. Der Dialog liegt in einer
  Surroundmischung im Center; `prepare_audio.py` mischt mit `-ac 1` alle Kanäle
  zusammen und holt damit Musik und Effekte in die Sprache, und seine
  `left`/`right`-Varianten greifen auf FL/FR, wo dann kaum Dialog steht.
  Dasselbe gilt für den Kanalvergleich in `probe_audio.py` und für Weg A der
  Sprechertrennung. Das Skript nimmt deshalb **Stereo vor Surround** und
  entscheidet erst danach nach Bitrate. Gibt es nur Surround, warnt es — dann vor
  Schritt 3 mit ffmpeg den Center herausziehen.
- **DRC-Spuren werden übersprungen.** YouTube legt dynamikkomprimierte Varianten
  ab (Format-ID auf `-drc`). Für Referenzclips ist das schlechtes Material,
  F5-TTS überträgt den Kanalcharakter mit.

Beim Bild gilt schlicht: **immer die höchste Auflösung, ohne zu fragen.** Der Ton
entscheidet über das Ergebnis, das Bild wird in Schritt 10 nur durchkopiert — 2160p
kostet also Gigabytes ohne Gewinn für die Tonspur (gemessen 679 MB gegen 119 MB für
zehn Minuten). Auf diesem Rechner ist das dank Gigabit-Anschluss gleichgültig, und
der Nutzer will die volle Bildqualität. `--max-res` ist deshalb nur für Notfälle da,
etwa wenn ein Download an der Leitung oder am Plattenplatz scheitert.

### Wenn der Download scheitert

- **`ERROR: unable to download video data: HTTP Error 403: Forbidden`**, bevor
  ein einziges Byte geflossen ist → **das macht der Player-Client, nicht die
  Leitung.** Der Extraktor fällt auf `android_vr` zurück, und dessen Medien-URLs
  weist YouTube für manche Videos rundweg ab. Die Sondierung gelingt dabei
  weiterhin, und ein `--test`-Lauf, der nach 10 KB abbricht, ebenfalls — deshalb
  sieht der Fehler zufällig aus, obwohl er es nicht ist. Gemessen an einem
  Video: rund dreißig Anläufe mit dem Standard-Client scheiterten ausnahmslos,
  `web_embedded` holte dasselbe Format mit 10 MB/s. Das Skript **wechselt den
  Client deshalb von Anlauf zu Anlauf** (`--attempts`, Vorgabe sechs) und
  behält mit `--continue`, was ein gescheiterter Versuch schon geschrieben hat.
  Es meldet am Ende, mit welchem Client es geladen hat. Scheitern alle, nennt
  die Abbruchmeldung die probierten; weitere gibst du mit `--player-client` vor,
  und `python -m yt_dlp -F "<url>"` zeigt, was das Video überhaupt hergibt.
- **Ohne JS-Laufzeit bringt der Clientwechsel nichts.** Dann bleibt die
  n-Challenge ungelöst, und `web_embedded` meldet `Only images are available for
  download`, hat also gar kein Format anzubieten. Gemessen an einem Video, das
  mit dem Standard-Client 403 lieferte: mit Laufzeit lud `web_embedded` in einer
  Sekunde durch, ohne sie gar nicht. Das Skript sucht deshalb selbst auf dem
  PATH (`deno`, `node`, `bun`), meldet die gefundene Laufzeit und **warnt, wenn
  keine da ist**. Festnageln kannst du sie mit `--js-runtime
  node:C:/nodejs/node.exe`; **der Pfad gehört hinter den Doppelpunkt.** Den
  Challenge-Solver setzt das Skript zusammen mit der Laufzeit, abschalten lässt
  er sich mit `--remote-components ""` — gegen den 403 allein richtet er nichts
  aus (1 von 4 Läufen mit, 1 von 3 ohne).
- **`Downloading android vr player API JSON`** ist die Zeile, an der du den
  Standard-Client erkennst. Steht ein 403 darunter, hat der Clientwechsel noch
  nicht gegriffen.
- **403 mitten im laufenden Download**, nachdem schon Prozente durchgelaufen
  sind → YouTube entzieht großen fortlaufenden Leseanfragen die Berechtigung.
  Gemessen starb eine 1080p-Spur bei drei Prozent, während die Tonspur desselben
  Videos vollständig durchlief. Das Skript zerlegt den Abruf deshalb in
  Bereichsanfragen (`--chunk-size`, Vorgabe `5M`).
- **„Sign in to confirm you're not a bot"** → `--cookies-from-browser`. **Mit
  Chrome oder Edge geht das nicht mehr.** Chromium verschlüsselt die Cookies
  seit Version 127 app-gebunden; yt-dlp scheitert mit `Failed to decrypt with
  DPAPI` (yt-dlp #10927). Den Browser zu schließen behebt nur die Dateisperre
  (`Could not copy Chrome cookie database`) und nicht die Verschlüsselung —
  danach kommt einfach der andere Fehler. Auf diesem Rechner ist Edge der
  einzige installierte Browser, der Cookie-Weg steht also nicht zur Verfügung.
  Bleibt `--player-client`.
- **Playlist-URL** → das Skript bricht ab. Einzelne Video-URL angeben;
  `watch?v=…&list=…` ist in Ordnung, das wird auf das Video reduziert.
- **Laufzeit weicht von den Metadaten ab** → das Skript warnt am Ende von selbst.
  Ein unvollständiger Download sieht sonst wie ein vollständiges Video aus, und
  du merkst es erst, wenn das Transkript vorzeitig endet. Erneut starten, yt-dlp
  setzt fort.

### Untertitel der Quelle als Namenshilfe

`--subs` lädt zusätzlich die **von Hand erstellten** Untertitel in der
Originalsprache als SRT. Übersetzen sollst du daraus nicht — dafür ist dein
eigenes Transkript da, und du kannst die Qualität dieser Datei nicht beurteilen.
Wofür sie taugt: die **Schreibweise von Eigennamen** nachschlagen, wenn Schritt
9b einen Namen als auffällig meldet. Genau dort verliert man sonst Zeit.

Automatische Untertitel lädt das Skript bewusst nicht. Sie sind selbst
Erkennerausgabe und tragen dieselbe Fehlerklasse wie dein Transkript, würden
also falsche Sicherheit geben.

## Schritt 0b — F5-TTS aufsetzen

```bash
python scripts/setup_tts.py <workdir>
```

Lädt den deutschen Checkpoint (`hvoss-techfak/F5-TTS-German`, 4,2 Mio. Schritte auf
Common Voice 19) und die Vokabeldatei in den Arbeitsordner. Beide bekannten
deutschen Checkpoints stehen unter **CC-BY-NC-4.0** — privat nutzbar, nicht für
Veröffentlichung. Sag das dem Nutzer, wenn er das Ergebnis weitergeben will.

### Installation: immer `--no-deps`

Das ist die Stelle, an der dieser Weg am ehesten kaputtgeht.

```bash
python -m pip install --no-deps f5-tts
python -m pip install --no-deps torchaudio torchcodec
python -m pip install cached_path vocos x-transformers torchdiffeq ema-pytorch \
    jieba pypinyin librosa pydub tomli hydra-core accelerate unidecode rjieba \
    transformers_stream_generator
```

- **`f5-tts` ohne `--no-deps` überschreibt dein CUDA-torch.** Es zieht sein eigenes
  torch, und auf einer neuen GPU-Generation fehlen der Ersatzversion die Kernel.
  Ergebnis: alles rechnet auf der CPU oder gar nicht.
- **torchaudio hinkt auf PyPI eine Version hinter torch her.** Beobachtet:
  torchaudio 2.11 als Neuestes gegen torch 2.12 und später 2.13. Mit `--no-deps`
  installiert und geprüft — es lädt sauber neben beiden, CUDA bleibt intakt.
- **torchaudio delegiert das Laden an `torchcodec`.** Ohne das Paket bricht die
  erste Synthese mit `ImportError: TorchCodec is required for load_with_torchcodec`
  ab, nicht schon beim Import.
- **`gradio` verlangt f5-tts nur für seine Weboberfläche** — weglassen, spart ein
  gutes Dutzend Pakete.

Für die Sprechertrennung über Embeddings (Schritt 6) kommt SpeechBrain dazu, aus
demselben Grund ohne Abhängigkeiten:

```bash
python -m pip install --no-deps speechbrain
python -m pip install hyperpyyaml joblib sentencepiece
```

Prüf nach jeder Installation, dass torch heil ist:

```bash
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

### Warum F5-TTS und nicht ein autoregressives Modell

F5-TTS ist ein Flow-Matching-Modell. Es kann prinzipiell nicht in die
Wiederholschleifen kippen, an denen autoregressive TTS bei kurzen Äußerungen
scheitern. Gemessen an einem Vorgänger-Modell dieses Skills: 589 % Wortfehlerrate
bei einem autoregressiven Mehrsprecher-Modell gegen 5 Prozent. Bei 200 Einheiten
pro Video triffst du so etwas garantiert.

**Es gibt keinen Phonemisierer und keine Steuersyntax.** F5-TTS schlägt jeden
Buchstaben einzeln im Vokabular nach und bildet Unbekanntes auf das Leerzeichen
ab. Es gibt deshalb weder Lautschrift noch Klammerhinweise noch SSML: `ʃuːlə`
kommt als „Toll" heraus, ein `<phoneme>`-Tag wird buchstäblich vorgelesen und
zerlegt zusätzlich den Satz. Anderslautende Dokumentationsseiten im Netz sind
maschinell erzeugt und falsch. Füttere den Rohtext der Cues.

Die einzige Stellschraube ist die **Buchstabenfolge selbst** — eine Schreibung,
die von der deutschen Lesart getroffen wird (`Seuta` statt `Ceuta`). Für
Ungarisch steht sie fertig in `hungarian.md`.

## Schritt 1 — Sprache erfragen

Frage per AskUserQuestion nach der gesprochenen Sprache, bevor du transkribierst —
**es sei denn, der Nutzer hat sie schon genannt**. Biete die plausibelsten Sprachen
an (Dateiname, Ordnerkontext, bisheriges Gespräch) und „Automatisch erkennen" als
eine Option. Kam die Quelle über Schritt 0a, nennt `fetch_source.py` die Sprache
aus den Metadaten — stell die als erste Option voran, aber **lass sie bestätigen**:
Es ist eine Angabe des Hochladenden, keine Messung. Automatik ist nur zweite Wahl: Bei verrauschtem Material rät Whisper
die Sprache oft falsch, und das ruiniert den gesamten Durchlauf.

Eine Stimmfrage gibt es nicht mehr — die Stimmen kommen aus dem Original.

## Schritt 2 — Tonspur analysieren

```bash
python scripts/probe_audio.py "<video>"
```

Meldet Container- und Streamdaten, Pegel, Störabstand, Kanalvergleich, Pausenprofil
und leitet daraus eine **Qualitätsklasse A, B oder C** samt Filterkette ab.

**Bei Dateien über etwa 30 Minuten dauert dieser Lauf mehrere Minuten** — er
dekodiert die Spur mehrfach vollständig. Beobachtet: 5 Minuten für eine 919-MB-Datei
mit 50 Minuten Laufzeit, was in einen 300-Sekunden-Timeout lief. Starte ihn bei
langen Dateien gleich im Hintergrund.

| Klasse | Typisch für | Vorgehen |
|---|---|---|
| **A** | Digitale Aufnahme, klarer Ton | Ein Durchlauf über die Originalspur |
| **B** | Brauchbar, aber leise/dumpf | Aufbereitetes Audio, Stichproben gegenprüfen |
| **C** | Analog-Digitalisat, verrauscht | Mehrere Tonvarianten dekodieren, stabile Lesungen von Filterartefakten trennen, Nutzer vorwarnen |

Die Klasse ist ein Vorschlag. Ein Vorspann mit Musik verzerrt den Durchschnitt, und
ohne echte Stille misst der „Rauschboden" Umgebungsgeräusch statt Rauschen. Deshalb
gibt das Skript ein Pausenprofil aus; findet es bei −32 dB keine Pausen, ist die
Störabstandszahl nicht belastbar.

### Durchgehend unterlegte Musik erkennst du nur hier

Politische Ansprachen und Kanalbeiträge sind oft mit leiser Musik unterlegt, die
über die ganze Laufzeit läuft statt nur im Vorspann. **Das ist die einzige Stelle
der Kette, an der du das siehst.** Der Rauschabstand aus Schritt 6 findet es nicht
— dort gleichen sich die Effekte aus, weil Musik die leisen Frames anhebt und die
Mischung dafür komprimiert wird. Gemessen an zwei Ansprachen desselben Sprechers:
die musikunterlegte kam auf **24,4 dB**, seine saubere Studioaufnahme auf **18,4**.
Die schlechtere Quelle maß sechs Dezibel besser.

Zwei Zahlen im Bericht dieses Skripts verraten es trotzdem, und beide nur im
Vergleich:

| Signal | sauber | mit Musikbett |
|---|---|---|
| Rauschboden | `-inf` (echte digitale Stille) | endlicher Wert, hier −62 dB |
| Sprechpausen bei −32 dB, acht Minuten Laufzeit | 95 | **12** |

Ein endlicher Rauschboden bei einer modernen Studioproduktion ist das erste
Zeichen, ein fast leeres Pausenprofil das zweite. Als Klassenurteil kommt trotzdem
A heraus — die Zahl allein trägt das nicht.

**Was daraus folgt, ist keine Filterung.** Musik unter Sprache bekommst du nicht
sauber weg, und der Versuch beschädigt die Stimme mehr als das Bett. Es folgt
zweierlei: Für die Transkription ist es meist unkritisch, und für den
Referenzclip nimmst du die Stimme **aus dem Archiv**, statt aus diesem Video zu
schneiden — ein Klon aus musikunterlegtem Material trägt das Bett mit. Steht die
Person nicht im Archiv, sag es dem Nutzer im Abschlussbericht; er kann sie dann
aus einer sauberen Quelle nachtragen.

**Für Voice-over ist Klasse C doppelt heikel.** Wo du den Wortlaut nicht sicher
hast, kannst du ihn nicht sprechen lassen — und anders als bei Untertiteln kannst du
die Unsicherheit nicht markieren, sondern musst die Stelle weglassen oder sinngemäß
umschreiben. Dazu kommt: Aus verrauschtem Material geschnittene Referenzclips
erzeugen verrauschte Klone, F5-TTS überträgt den Kanalcharakter mit. Bei C den
Nutzer vorwarnen, bevor du anfängst.

## Schritt 3 — Audio aufbereiten

```bash
python scripts/prepare_audio.py "<video>" --outdir <workdir> --profile <A|B|C>
```

Erzeugt 16 kHz Mono-WAVs. Arbeitsordner ins Scratchpad, nicht neben das Video.

## Schritt 4 — Transkribieren

Wortzeiten sind hier **nicht optional**: Die gesamte Segmentierung baut darauf auf.

```bash
python scripts/transcribe.py <workdir> --mode full --variants raw --lang hu \
    --words --max-chunk 240 --out <workdir>/words.txt --json <workdir>/words.json
```

**`--out` und `--json` gehen ins aktuelle Verzeichnis, nicht in den Arbeitsordner.**
Beide werden mit `open(...)` unverändert geöffnet und nie mit dem `workdir`-Argument
zusammengesetzt. Rufst du das Skript wie oben aus dem Skill-Ordner auf und gibst nur
`words.json` an, landen Transkript und Wortzeiten neben den Skripten — und der nächste
Schritt bricht im Arbeitsordner mit `FileNotFoundError: words.json` ab. Schreib die
beiden Pfade deshalb absolut aus. Dasselbe gilt für alle folgenden Skripte, die
relative Namen entgegennehmen.

**`--max-chunk` bei langen Dateien.** Der Volldurchlauf bricht hart ab — kein
Traceback, kein brauchbarer Exitcode, leere Ausgabedatei. Es ist kein VRAM-Problem.
`--max-chunk` schneidet an erkannten Sprechpausen in kleinere Blöcke.

**Nimm 240, nicht 300.** Der Abbruch hängt an der Länge des *einzelnen Blocks*, nicht
an der Gesamtlaufzeit. Gemessen: eine Datei von nur 26 Minuten starb mit `--max-chunk
300` am fünften Block, weil der Chunker dort einen Rest von 395 Sekunden stehen ließ —
die vier Blöcke davor liefen sauber durch. Mit 240 blieb derselbe Lauf bei maximal
243 Sekunden pro Block und ging glatt durch. Die frühere Angabe „bis etwa 25 Minuten
läuft es am Stück" trägt also nicht.

**Der Lauf setzt nach einem Abbruch fort.** Jeder fertige Block wird sofort nach
`<workdir>/<variant>_blocks/block_NN.json` geschrieben, bevor der nächste beginnt.
Startest du denselben Befehl erneut, kommen die fertigen Blöcke aus dem Cache und nur
der abgestürzte wird neu dekodiert. Ohne das kostet ein Abbruch am letzten Block den
gesamten Lauf: Das JSON entsteht erst ganz am Ende, vier fertige Blöcke waren im
Testfall mit einem Schlag weg.

Der Cache-Schlüssel deckt Blockgrenzen, Sprache und Modell ab. Änderst du eines davon,
wird neu dekodiert statt still eine veraltete Lesung wiederverwendet. Zum Erzwingen
eines frischen Laufs den `_blocks`-Ordner löschen.

Die Blockgrenzen werden über `silencedetect` gesucht. Die Meldung `raw.wav: 1
Bloecke` bei einer langen Datei ist das Warnzeichen, dass keine Pausen gefunden
wurden; dann `--silence-db` aus dem Probe-Lauf vorgeben. Bricht es trotzdem ab,
schneide die Blöcke selbst mit ffmpeg und addiere den Blockstart auf die Wortzeiten.

Sprecharme Vorspänne vorher abschneiden — sie liefern keine Wörter, kosten
Rechenzeit und provozieren Floskel-Halluzinationen.

### Schritt 4b — Abdeckung prüfen (nicht optional)

```bash
python scripts/check_coverage.py words.json
```

**Der Langform-Dekoder verschluckt gelegentlich ganze Passagen, ohne das zu melden.**
In einer 42-Minuten-Datei traf es zwei Stellen von je rund 28 Sekunden; der Text las
sich an beiden völlig flüssig. Sichtbar wird das nur an der Zeitachse: ausgedünnte
Wörter oder ein einzelnes Wort mit einem Zeitstempel über eine halbe Minute.

Nicht jede Meldung ist ein Fehler — eine Atempause erscheint als Lücke, und ein
Musik-Intro trägt genau die Signatur von oben: Whisper dehnt ein echtes Wort
darüber. Unterscheiden kann sie nur ein Reparaturclip unter dreißig Sekunden.
Kommt auch daraus nichts als eine Floskel, fehlt nichts — dann ist allein der
Zeitstempel des gedehnten Wortes zu korrigieren. Erklären musst du es aber,
statt es zu übergehen.

Reparatur: Bereich großzügig als eigenen Clip schneiden, für sich dekodieren, mit
`patch_words.py` einspleißen, erneut prüfen. Wenn der Reparaturclip die Stelle
wieder verschluckt, schneide ihn **kürzer als 30 Sekunden** — dann dekodiert Whisper
in Kurzform, und die hat den Fehler nicht.

**Die Naht nach jedem Patch selbst ansehen, nicht nur die Meldung lesen.**
`patch_words.py` meldet zufrieden „7 Wörter ersetzt durch 57", während der Fehler
noch dasteht: Die Bereichsgrenze wird gegen den **Start** eines Wortes geprüft, und
ein Halluzinationswort, das bei 471,88 s beginnt, überlebt ein `--patch … 471.9 …`
um zwei Hundertstel. Setz die Grenzen deshalb großzügig in die Pause hinein und
lass dir die Wörter um die Naht ausgeben:

```bash
python -c "import json; ws=json.load(open('words_final.json',encoding='utf-8'))['raw'];
[print(round(x['start'],2), repr(x['text'])) for x in ws if 470<=x['start']<=478]"
```

Am Clipende zerschneidet die Naht oft ein Wort: Der Patch endete auf
`gondolatban`, die Basis setzte mit dem Fragment `módban` fort — zusammen war es
`gondolkodásmódban`. Zieh die ersetzte Zone dann bis hinter das Fragment, statt
beides stehen zu lassen.

Die Abo-Floskel (`Köszönöm, hogy megnéztétek`, „Untertitel von …") steht
typischerweise am Dateiende hinter dem letzten echten Wort, abgesetzt durch eine
Pause. Mit `patch_words.py --drop-after <Sekunde>` wegschneiden, nicht nach
Textmustern filtern: Ein Filter auf `amara` löscht auch das ungarische Wort
`Hamarabb`.

**Sie kann aber auch mitten in der Datei stehen** — dann ist sie kein Abspann,
sondern die Tarnung eines Aussetzers. In einer 26-Minuten-Datei füllte sie bei
07:51 rund zwölf Sekunden, dahinter klaffte eine weitere Lücke von 17,7 Sekunden;
verschluckt waren insgesamt dreißig Sekunden Sprache. `--drop-after` ist dafür das
falsche Werkzeug, weil es alles Folgende mitnimmt — das ist ein Dropout und wird
über einen Reparaturclip behoben. Merkmal im `check_coverage.py`-Bericht: Die
Floskelwörter tauchen unter „Wörter über 3.0s Dauer" auf, weil sie über die
verschluckte Passage gedehnt werden.

**Es gibt aber noch einen dritten Fall: die Floskel als reine Halluzination über
einer Sprechpause, ohne dass etwas fehlt.** Beobachtet in einer 53-Minuten-Datei
bei 39:47. Verwechselt man ihn mit einem Dropout, schneidet und dekodiert man
einen Reparaturclip für nichts.

Unterscheiden lässt er sich an den Wortzeiten, nicht am Text. Beim Dropout wird
die Floskel über die verschluckte Passage **gedehnt**; hier trugen alle fünf
Floskelwörter denselben Zeitstempel mit **Dauer null**, eingeklemmt in eine Lücke
von zweieinhalb Sekunden, und nur das Wort davor war gedehnt. Anders gesagt: Die
Floskel beansprucht keine Zeit, sie füllt nur eine Pause.

Beleg holst du dir mit einem Kurzclip unter 30 Sekunden über die Stelle
(`--mode zoom`). Liest die Kurzform denselben Satz ohne die Floskel, fehlt nichts.
Im Testfall brach der Sprecher schlicht mitten im Satz ab — `csak ha valaki, ez
olyan, mint amikor` —, und genau in diese Denkpause hatte der Langform-Dekoder die
Floskel gesetzt. Dann werden nur die Floskelwörter aus `words_final.json` gelöscht;
weder `--drop-after` noch ein Patch sind nötig.

Danach neu segmentieren. Die gelöschten Wörter hinterlassen eine Lücke, die über
der Pausenschwelle von 0,45 s liegen kann — im Testfall entstand dadurch ein
zusätzlicher Schnittpunkt, aus 472 Einheiten wurden 473. **Wenn du schon Embeddings
gerechnet hast, sind die damit ungültig** und müssen neu berechnet werden, weil sie
je Einheit gespeichert sind. Also lieber vor Schritt 6 bereinigen.

## Schritt 5 — Segmentieren (erster Durchgang)

```bash
python scripts/segment_speech.py words_final.json units.json --rate 14 --duration <sek>
```

Schneidet an Satzenden und Sprechpausen ab 0,45 s. Jede Einheit bekommt einen
`slot` bis zum Beginn der nächsten — die Pause nach dem Satz ist nutzbare Sprechzeit
— und daraus ein `budget` in Zeichen.

Die `--rate` ist hier nur ein Platzhalter: Die echten Raten kennst du erst nach
Schritt 6, und du segmentierst danach noch einmal. **Die Schnittpunkte ändern sich
dabei nicht**, nur die Budgets.

**Kontrolliere die gemeldete Verteilung.** Rechne dabei auf die Laufzeit um, statt
absolute Zahlen zu vergleichen: gesund sind rund **8 bis 9 Einheiten je Minute** bei
einem Slot-Median um 6,5 s, und unter zwei Sekunden sollte deutlich weniger als ein
Zehntel liegen. Gemessen an zwei Läufen: 421 Einheiten mit 25 kurzen bei 50 Minuten,
569 Einheiten mit 37 kurzen bei 66 Minuten. Zwei Fehlversuche sind im Skript
dokumentiert und schon behoben, aber du erkennst sie an der Ausgabe:

- Zu wenige, sehr lange Einheiten, die mitten im Nebensatz enden → der Zwangsschnitt
  fällt auf ein beliebiges Wort statt auf eine Pause.
- Sehr viele kurze Einheiten (im Fehlversuch 556 Einheiten, 171 davon unter zwei
  Sekunden) → der Schnitt fällt auf die breiteste Pause irgendwo im Lauf und lässt
  Stummel übrig.

## Schritt 6 — Sprecher trennen und Raten messen

Es gibt zwei Wege. **Welcher richtig ist, entscheidet die Aufnahmesituation, nicht
die Sprecherzahl:**

| Situation | Weg |
|---|---|
| Getrennte Kanäle — Studio gegen Videoschalte, Telefon, anderes Mikrofon | `diarize.py` |
| Alle im selben Raum an gleichen Mikrofonen — Tischrunde, Panel, Podcast | `embed_units.py` + `diarize_ecapa.py` |

Beide schreiben dasselbe `speakers.json`; alles Folgende ist identisch.

Der Ablauf danach ist immer derselbe, und die Reihenfolge spart Arbeit:

1. **Trennen** — `diarize.py` oder `embed_units.py` + `diarize_ecapa.py`
2. **Wiedererkennen** — `match_voices.py`; wer sicher im Archiv steht, ist fertig
3. **Bewerten** — `check_refs.py`, für alle übrigen
4. **Ersetzen**, wo ein besserer Clip im Video liegt; sonst den schlechten
   akzeptieren und es berichten
5. **Zweifelsfälle entscheiden** — erst jetzt, gegen den Clip, der nach dem
   Ersetzen wirklich in Gebrauch ist
6. **Raten messen** — `measure_rate.py --only-missing`

Ins Archiv geschrieben wird hier nichts.

### Weg A — `diarize.py` (getrennte Kanäle)

```bash
python scripts/diarize.py "<video>" units.json <workdir>/refs --speakers 2
```

Merkmale sind bewusst schlicht: MFCC, Spektralform und Tonhöhe, geclustert mit
k-Means. Kein Zusatzdownload, kein Token. Das trägt, solange die Stimmen sich im
**Kanal** unterscheiden — Bandbreite und Rauschboden einer Videoschalte gegen ein
Studiomikrofon.

**Ohne `--speakers` testet das Skript nur zwei und drei Cluster.** Bei vier Personen
ist das Ergebnis dann strukturell falsch, ohne dass es das meldet. Sprecherzahl immer
vorgeben, wenn du sie kennst.

### Weg B — Embeddings (ein Raum, gleiche Mikrofone)

```bash
python scripts/embed_units.py "<video>" units.json <workdir>/emb.npy
python scripts/diarize_ecapa.py "<video>" units.json <workdir>/emb.npy \
    <workdir>/refs --speakers 4 --structure <workdir>/structure.json
```

**Bei einer Tischrunde versagt Weg A.** Gemessen an einem vierköpfigen Panel mit
identischen Mikrofonen: Trennschärfe 0,19, und die **beiden Frauenstimmen landeten
in einem Cluster**. Es gibt dort keinen Kanalunterschied, an dem sich MFCC
festhalten könnte, und Klangfarbe allein reicht nicht. Ein trainiertes
Sprecher-Embedding schon: derselbe Fall kam auf Ankertreue 1,00.

`embed_units.py` lädt `speechbrain/spkrec-ecapa-voxceleb` — frei herunterladbar,
kein Token, keine gated weights, also dieselbe Hürdenfreiheit wie bisher.

**Unter Windows kopiert das Skript die Checkpoint-Dateien, statt sie zu verlinken.**
SpeechBrain legt sonst Symlinks an, und ohne Entwicklermodus bricht das mit
`OSError WinError 1314` ab — erst beim Laden, nicht bei der Installation.

`diarize_ecapa.py` probiert mehrere Clusterverfahren durch und wählt nach
Ankertreue. **Die Zahl allein trägt das Urteil nicht — sieh dir immer die
Clustergrößen daneben an.** Ein Verfahren kann auf Embeddings kollabieren: Fast
alle Einheiten fallen in ein Cluster, der Rest bleibt als einzelne Ausreißer
übrig. Solange die Anker dabei in den großen Clustern liegen, sieht die
Ankertreue gut aus, und genau dieses Verfahren gewinnt dann die Auswahl. Ein
Sprecher, der am Ende nur eine Handvoll Einheiten trägt, ist deshalb ein Befund
und kein Randfall — vor allem dort, wo du für ihn ohnehin wenige Anker setzen
konntest.

### Eingespielte Clips sind eigene Sprecher

Polit- und Medienformate spielen Videos ein: eine Rede, eine Pressekonferenz, ein
Social-Media-Clip. **Diese Stimmen gehören keinem am Tisch** und dürfen nicht dessen
Klon erben. In der Testdatei waren es drei Politiker neben vier Panelisten — sieben
Stimmen, nicht vier.

Ihre Grenzen musst du nicht raten: Der Moderator kündigt jeden Einspieler an
(„sehen wir uns das erste Video an") und knüpft danach wieder an. Trag sie als
Indexbereiche in die Strukturdatei ein, dann werden sie festgenagelt statt geclustert:

```json
{"inserts": [[20, 37, "Magyar Peter"], [274, 289, "Szucs Gabor"]],
 "anchors": {"Dorottya": [0, 1, 47], "Tamas": [49, 51, 52]}}
```

Die Sprecherzahl bei `--speakers` zählt **nur die Personen im Raum**; die Einspieler
kommen zusätzlich dazu.

### Derselbe Mechanismus nagelt Fragesteller fest

`inserts` gruppiert nach **Label**, nicht nach Bereich: Mehrere getrennte Bereiche
mit demselben Namen verschmelzen zu einer Stimme. Damit deckst du auch die
**Pressekonferenz mit vielen Fragestellern** ab, die je zwei- bis achtmal kurz zu
Wort kommen — mehrere Bereiche pro Person, gleiches Label.

Gemessen an einer 2:15-stündigen Regierungspressekonferenz: drei Podiumsstimmen
geclustert (Ankertreue 0,962), fünfzehn Journalisten über 50 Insert-Bereiche
festgenagelt, **achtzehn Stimmen** insgesamt. Clustern wäre hier unterlegen —
achtzehn Cluster über kurze Einheiten sind fehleranfällig, und die Grenzen stehen
ohnehin im Text, weil jeder Fragesteller Redaktion und Namen nennt und der
Moderator ihn davor aufruft. Der Preis ist, dass du den Frageteil einmal
vollständig liest und die Wechsel notierst; das ist die einzige Handarbeit im
ganzen Durchlauf.

Zwei Fallen: **Gemischte Einheiten an der Übergabe** („Danke schön. ATV.") ordnest
du nach dem dominanten Sprecher zu und lässt Grenzfälle beim Cluster — ein halber
Satz in der falschen Stimme fällt nicht auf, eine falsch gesetzte Bereichsgrenze
schon. Und **Zwischenrufe des Hauptsprechers** mitten in einer Frage gehören nicht
in den Insert-Bereich, sonst erbt der Journalist sie.

### Gegenlesen heißt Anker setzen, nicht Stichproben ansehen

**Die Zuordnung musst du gegenlesen** — bei beiden Wegen. Aber „ein paar Einheiten
anschauen" ist zu schwach, um zwei Clusterverfahren gegeneinander zu bewerten.
Sammle stattdessen Einheiten, deren Sprecher aus dem **Dialog** folgt:

- wer namentlich aufgerufen wird und wer darauf antwortet („dann fangen wir mit
  Tamás an" → die nächste Einheit ist Tamás)
- wer über wen in der dritten Person spricht („wie Tamás schon sagte" → nicht Tamás)
- wer sich selbst verortet („meine Frau sagte" → nicht die Frauenstimme)
- Begrüßung, Gästevorstellung, Verabschiedung

Schreib sie unter `anchors` in die Strukturdatei. `diarize_ecapa.py` rechnet daraus
die **Ankertreue**: den Anteil der Anker, die im dominanten Cluster ihres Sprechers
landen, wobei ein Cluster nur für einen Sprecher stehen darf. Unter 0,95 warnt es.
Rund 60 Anker über vier Sprecher waren im Testfall ausreichend und billig.

Achtung bei der Interpretation: In einem Interview baut der Moderator vor seiner
Frage oft mehrere Einheiten Kontext auf. Eine Einheit mitten in einer Sachpassage
kann also durchaus dem Moderator gehören — such nach der Frage dahinter, bevor du
die Zuordnung für falsch hältst.

### Zuerst nachsehen, ob du die Stimme schon hast

**Sobald die Cluster stehen, fragst du das Archiv.** Nicht später — alles, was
danach in diesem Schritt kommt, entfällt für jeden Sprecher, den sie kennt.

```bash
python scripts/match_voices.py units.json <workdir>/emb.npy \
    <workdir>/refs/speakers.json --apply
```

Das Skript bildet je Cluster den ECAPA-Zentroid und vergleicht ihn mit jeder
gespeicherten Stimme. Ein Treffer ersetzt den frisch geschnittenen Clip durch den
gespeicherten, übernimmt dessen `ref_text` und dessen **gemessene Rate** und
trägt `voice_id` ein. Damit fallen für diesen Sprecher Clipsuche *und*
Ratenmessung weg.

**Der Zentroid, nicht der Clip.** Eine einzelne Einheit ist ein wackliger
Fingerabdruck: Gemessen an einem Interview streuten die Einheiten eines Sprechers
bis auf 0,49 gegen den eigenen Zentroid herunter. Der Mittelwert über alle
Einheiten ist stabil.

Gemessen an drei Videos derselben Reihe — einer Studioansprache, einer
Pressekonferenz im Saal und einem Ortstermin auf einem Schiff mit durchgehendem
Motorbrummen:

| Vergleich | Ähnlichkeit |
|---|---|
| Gleiche Person, zwei Hälften **derselben** Aufnahme | 0,99 |
| Gleiche Person, anderes Video, gleicher Tag | 0,88 |
| Gleiche Person, Studio → Saal, andere Woche | 0,84 |
| Gleiche Person, Studio → Schiff, andere Woche, Störgeräusch | **0,64** |
| **Verschiedene** Personen, egal welche Kombination | 0,05 – 0,37 |

Der schlechteste echte Treffer lag bei 0,64, der beste Fehltreffer bei 0,37. Der
Abstand ist kleiner, als er aussieht: Bei zwei Stimmen im Archiv lag der beste
Fehlwert noch bei 0,18, bei vier schon bei 0,37. **Er steigt mit jedem Eintrag**,
weil mehr Vektoren mehr Gelegenheit zum Zufallstreffer geben.

Der Fehlwert von 0,37 stammt dabei von einem **Mischcluster** — Moderator und
fünfzehn Fragesteller einer Pressekonferenz in einem Topf. Ein Zentroid über
mehrere Personen liegt näher an allem, deshalb ist eine saubere Sprechertrennung
auch für die Wiedererkennung die halbe Miete.

### Die Schwelle liegt bewusst tief

**Die beiden Arten, falsch zu liegen, kosten nicht dasselbe.** Ein *verpasster*
Treffer schickt den Sprecher zurück an einen Clip aus dem aktuellen Video — bei
schlechtem Material heißt das Artefakte, Füllwörter und eine falsche Sprechrate.
Ein *falscher* Treffer gibt ihm eine saubere, ratenvermessene Stimme, die einer
anderen Person gehört.

Und das wiegt weniger, als es klingt, weil der Klon die Originalstimme ohnehin
nicht nachbildet — siehe „Der Klon trennt Sprecher, er bildet sie nicht nach". Der
Hörer hat keinen Vergleich: Er kennt die deutsche Stimme dieser Person nur aus
diesem Skill. Was er merkt, ist eine *kaputte* Stimme, nicht eine *vertauschte*.
Deshalb stehen die Schwellen bei 0,45 und 0,30 statt in der sicheren Mitte.

### Das Zweifelsband löst du auf, ohne zu fragen

Ein Treffer zwischen 0,30 und 0,45 wird gemeldet und **nicht** übernommen; der
Sprecher behält vorerst seinen Clip aus dem Video. „Gemeldet" heißt nicht
„rückgefragt": Unterbrich einen laufenden Durchlauf nicht für eine Frage, die du
selbst beantworten kannst. Geh der Reihe nach vor.

**Erstens: Steht der Name im Transkript?** Bei Interviews, Pressekonferenzen und
Panels fast immer — „übergebe das Wort an Gocsály József", „danke, Herr General".
Das ist ein direkter Beleg und schlägt jeden Ähnlichkeitswert. Bestätige dann mit
`--accept <sprecher>=<id>` und schreib in den Bericht, worauf du dich gestützt hast.

**Zweitens, wenn der Text nichts hergibt: Lass die Alternative entscheiden.** Der
Fehltreffer ist nur deshalb billig, weil die Gegenoption meist schlechter ist —
das gilt aber nicht, wenn das Video selbst einen guten Clip hergibt. Sieh dir
deshalb an, was `check_refs.py` für genau diesen Sprecher sagt:

| `check_refs.py` sagt | Entscheidung |
|---|---|
| Clip ist brauchbar | **Video-Clip nehmen.** Ein Fehltreffer wäre hier reiner Verlust — eine richtige saubere Stimme gegen eine falsche saubere getauscht. |
| Quelle erschöpft, alles unter der Rauschgrenze | **Archivstimme nehmen** (`--accept`). Jetzt ist selbst ein zweifelhafter Treffer die bessere Wahl. |

**Frag danach aber erst, wenn der Clipwechsel hinter dir liegt.** `check_refs.py`
bewertet immer nur den Clip, der gerade eingetragen ist, und ein besserer
Ausschnitt derselben Stimme dreht sein Urteil um. Entscheidest du vorher,
entscheidest du über einen Clip, den du gleich wegwirfst — und die Antwort fällt
dann für die Archivstimme aus, wo das Video sie gar nicht gebraucht hätte.

Der zusätzliche Lauf ist billig, er lädt kein Modell.

**Erst wenn beides nichts ergibt, geht es in den Abschlussbericht**, mit Wert und
Kandidat. Der Nutzer kann die Stimme dann mit einem Aufruf nachtragen; die
Segmentierung ändert sich dadurch nicht, nur die Budgets.

**Eine Ausnahme setzt `match_voices.py` hart durch: Zwei Sprecher desselben Videos
bekommen nie dieselbe Archivstimme.** Das ist der eine Fehler, der wirklich teurer
ist als ein schlechter Clip — die beiden wären nicht mehr auseinanderzuhalten, und
Sprecher auseinanderzuhalten ist der ganze Grund, warum hier geklont wird. Bei
einer Kollision gewinnt die höhere Ähnlichkeit, der andere bekommt seinen Clip aus
dem Video. Ein mit `--accept` bestätigter Treffer sticht dabei jeden gerechneten
Wert.

**Die Embeddings kommen aus der Originalspur, nicht aus einer aufbereiteten.**
Das ist verlockend falsch: Bei der Schiffsaufnahme mit Motorbrummen lag es nahe,
für die Wiedererkennung erst den Hochpass aus Schritt 3 anzuwenden. Gemessen wird
es dadurch **schlechter** — 0,64 auf 0,55 und 0,88 auf 0,76. Die gespeicherten
Fingerabdrücke stammen aus ungefiltertem Ton, und der Filter nimmt tiefe Anteile
weg, die zur Stimme gehören und nicht zum Motor. Gib `embed_units.py` also die
Quelldatei, auch wenn du für die Transkription eine gefilterte Variante benutzt.

**Keine spätere Zahl der Kette fällt über einen Fehltreffer.** Ankertreue,
Einpassung und Wortfehlerrate messen alle etwas anderes. Was du hast, ist der
Ähnlichkeitswert und dein Ohr: Die gespeicherten Clips liegen als WAV in `voices/`
und sind in Sekunden angehört.

### Referenzclips bewerten, bevor du sie von Hand prüfst

Für jeden Sprecher **ohne** Archivstimme:

```bash
python scripts/check_refs.py "<video>" units.json <workdir>/refs/speakers.json
```

Das Skript misst den Clip, der wirklich in Gebrauch ist — es liest die WAV-Datei,
nicht `ref_unit`, und überlebt damit einen Clipwechsel von Hand. Drei Größen, und
was sie entscheiden:

| Größe | Bedeutung |
|---|---|
| **Dichte** (Zeichen/s) | sagt die Klonrate voraus; unter 16 träge, über 19 gedrängt |
| **Rauschen** (dB) | Abstand der leisen zu den lauten Frames der Einheit |
| **Satzgrenze** | beginnt der Clip einen Satz und schließt er einen ab |

Danach vergleicht es den Clip mit **allen** Einheiten derselben Stimme, die als
Clip überhaupt in Frage kämen. Das ist der Punkt, an dem sich die beiden Fälle
trennen, die in `speakers.json` gleich aussehen:

- **Ein besserer Clip ist da** — dann nennt es die Einheit. Im Testlauf schlug es
  von sich aus genau die Einheit vor, die vorher von Hand gefunden worden war
  (13,8 → 17,2 Zeichen/s).
- **Die Quelle ist erschöpft** — kein Kandidat kommt über die Rauschgrenze oder
  keiner spricht dichter als der aktuelle. Das ist der Vor-Ort-Fall mit
  Verkehrslärm. Gemessen an einem Ortstermin auf einem Schiff mit laufendem
  Motor: alle zwanzig beziehungsweise zehn Kandidaten unter der Grenze, SNR-Median
  8,8 und 11,3 dB. Dann synthetisierst du mit dem, was da ist, und **schreibst es
  in den Abschlussbericht**. Eine fremde Ersatzstimme wäre der schlechtere Tausch:
  Sie klingt sauber, aber nicht nach dieser Person, und der Zuschauer hört den
  Sprecherwechsel im Bild.

  **Der eigentliche Ausweg ist das Archiv**, und deshalb steht `match_voices.py`
  vor diesem Schritt. Im selben Schiffsvideo waren beide Sprecher dort schon
  hinterlegt, aus einer Pressekonferenz und einer Studioansprache — die Frage nach
  dem besten Clip *in diesem Video* stellte sich für sie gar nicht mehr. Was
  `check_refs.py` hier meldet, betrifft nur, wer nicht im Archiv steht.

**Kandidaten werden nach Dichte sortiert, nie nach Rauschabstand.** Der erste
Entwurf dieses Skripts rankte nach dB und schlug prompt langsamere Clips vor —
in sauberem Studiomaterial liegt der Rauschabstand bei 24 bis 68 dB, und das
Maximum zu jagen tauscht einen guten Clip gegen einen trägen. Rauschen ist ein
Veto, keine Rangfolge.

**Der Rauschabstand sieht kein Musikbett.** Eine Ansprache mit durchgehend
unterlegter Musik kam hier auf 24,4 dB und alle achtzehn Kandidaten über die
Grenze — das Skript hätte den Clip genommen und nur die Satzgrenze bemängelt.
Ob Musik unter der Stimme liegt, entscheidest du in Schritt 2 und nicht hier.

**Den Wortlaut liest du weiter selbst.** Warum der Filter das nicht abnimmt, steht
im übernächsten Abschnitt.

### Der Referenzclip muss an einer Satzgrenze beginnen und enden

**Sieh dir nach der Diarisierung jeden `ref_text` in `speakers.json` an.** Beide
Skripte schneiden den Clip aus einer Einheit, die sie nach Länge und Cluster-Nähe
wählen — nicht danach, ob dort ein Satz anfängt. Erwischt es eine Einheit, die die
vorige fortsetzt, beginnt der Clip mitten im Satz. Erkennbar am `ref_text`: Er
fängt klein an.

**`check_refs.py` meldet unter `keine Satzgrenze` beide Enden.** Sein Urteil sagt
nicht, welches gemeint ist — ein Clip mit tadellosem Satzanfang bekommt es auch
dann, wenn er auf einem Komma endet. Lies den `ref_text` an beiden Enden nach,
bevor du neu schneidest, sonst suchst du am falschen.

```bash
python -c "import json; [print(e['speaker'], repr(e['ref_text'][:60]))
    for e in json.load(open('refs/speakers.json',encoding='utf-8'))['speakers']]"
```

**Die Folge ist ein vorangestelltes Halluzinat vor jeder Einheit dieser Stimme.**
Gemessen an einem ungarischen Interview: Der Clip des Moderators kam aus einer
Einheit, die mit `pontosan hogyan fogod értékelni` einsetzte — Fortsetzung der
Einheit davor. Daraufhin bekam die deutsche Spur Vorsilben wie „Hier Leute,",
„gilt jetzt", „Ja," und „Ihr Lötje," vorgeklebt. Neu geschnitten aus einer Einheit
mit klarem Satzanfang fiel die Wortfehlerrate dieser Stimme von **36,6 % auf
15,0 %**, und die Artefakte waren restlos weg.

**Diarisierung und Einpassungszahlen sehen das nicht.** Im selben Lauf stand die
Ankertreue auf 1,00 und später keine einzige Einheit verschoben. Nur Schritt 9b
findet es, und dort am Muster, nicht an der Zahl: Sind die auffälligen Einheiten
**einer** Stimme durchweg mit einem Füllwort vorne beschlagen und die der anderen
nicht, ist es der Clip und nicht die Übersetzung. Repariere dann nicht die Texte —
das behandelt Symptome. Im Testfall brachte ein verlängerter Einheitenanfang die
Rate von 22 % auf 36 %, also schlechter.

Neu schneiden von Hand, aus einer Einheit unter elf Sekunden mit Satzanfang:

```bash
ffmpeg -y -v error -nostdin -i "<video>" -ss <start> -t <dauer> -vn \
    -ar 24000 -ac 1 -c:a pcm_s16le refs/spk1.wav
```

Danach `ref_text` in `speakers.json` auf den Wortlaut des neuen Clips setzen.
Abtastrate und Kanalzahl aus der alten Datei übernehmen, nicht raten.

### Welche Einheit du als Ersatz nimmst: die dichteste, nicht die längste

**Ein Satzanfang allein macht noch keinen brauchbaren Clip.** Gemessen an einem
ungarischen Studiointerview, in dem *jeder* Kandidat sauber am Satzanfang begann
und am Satzende schloss:

| Clip | Zeichen/s im Original | Klonrate | Ergebnis in 9b |
|---|---|---|---|
| `Na most, hát bocsánat…` | 10,5 | 10,1 | nicht gemessen, Rate unbrauchbar |
| `Én egy korrupt gazdasági merényletnek…` | 13,4 | 13,7 | 18,0 %, Füllwort vor jeder dritten Einheit |
| `Ezért van az, hogy szélben is…` | 18,0 | 17,9 | **7,9 %, artefaktfrei** |
| `Volt egyébként vendégem…` | 18,6 | 18,4 | 12,1 %, artefaktfrei |

Die zweite Zeile ist der Grund für diesen Abschnitt: Der Clip erfüllte beide
Regeln von oben und klebte trotzdem ein „Silly" vor jede dritte Einheit. Was ihn
vom vierten unterschied, war nicht die Satzgrenze, sondern das Sprechtempo. Der
Sprecher setzt dort ruhiger an — und der Klon übernimmt das für die ganze Spur.

**Die Rate des Klons folgt der Zeichendichte des Clips fast eins zu eins.** Alle
vier Zeilen treffen auf ein halbes Zeichen pro Sekunde genau. Damit musst du die
Klonrate nicht mehr erraten und auch keine Clips durchprobieren: Du liest sie am
Original ab, bevor du schneidest. `measure_rate.py` lädt dafür das Modell und
kostet Minuten, die Dichte kostet nichts. (Belegt für Ungarisch nach Deutsch;
bei einer Quellsprache mit deutlich anderer Wortlänge — Finnisch, Vietnamesisch —
erwarte einen Versatz und prüf die erste Messung gegen.)

Such den Ersatz deshalb nach Dichte, gefiltert auf saubere Satzgrenzen:

```bash
python -c "
import json
u=json.load(open('units.json',encoding='utf-8'))
lab=json.load(open('refs/speakers.json',encoding='utf-8'))['labels']
SPK=0                                 # Sprecherindex, dessen Clip du ersetzt
c=[]
for i,e in enumerate(u):
    if lab[i]!=SPK: continue
    d=e['end']-e['start']
    if not 6.0<=d<=10.5: continue     # unter 11s, sonst schneidet F5 zurueck
    t=e.get('text',e.get('hu','')).strip()   # 'hu' nur in alten Arbeitsordnern
    if not t[:1].isupper() or not t.endswith('.'): continue
    c.append((len(t)/d,i,round(d,1),t))
for r,i,d,t in sorted(c,reverse=True)[:10]:
    print('%.1f z/s  #%d  %.1fs  %s'%(r,i,d,t[:80]))"
```

**Den Wortlaut musst du dabei selbst lesen — der Filter nimmt dir das nicht ab.**
Whisper schreibt auch eine Einleitungsfloskel groß, also überleben `Tehát`, `Hát`,
`Na most` und `Szóval` die Prüfung auf Großbuchstabe mühelos. Im Testlauf begannen
drei der zehn obersten Treffer mit `Tehát`. Geh die Liste von oben durch und nimm
den ersten Treffer, der mit einem inhaltlichen Wort einsetzt.

Ziel ist der Bereich, in dem deutsche Klone liegen: etwa 11 bis 19 Zeichen/s. Die
Liste reicht oben darüber hinaus — im Testlauf stand ein Treffer mit 21,0 z/s an
der Spitze. Das ist die harmlose Seite: Ein zu schneller Klon kostet etwas
Gedrängtheit, ein zu langsamer zwingt dich, die Übersetzung zusammenzustreichen.
Trotzdem lieber einen Treffer im Band nehmen als den Spitzenwert.

Im Testfall hob das die Budgetsumme um ein Viertel und drückte die Zahl der
Einheiten über Budget von 27 auf 4.

**Auch das Ende des Clips blutet aus.** Der Clip der zweiten Stimme endete im
selben Lauf auf `csak nem mindegy, hogy hogyan.` — ein sauberer Satzschluss, und
trotzdem starteten zwei Einheiten mit „Hogian" beziehungsweise „Haugion". Das ist
milder als der Satzanfang und war bei 9,3 % Gesamtrate nicht die Mühe wert; wenn
eine Stimme aber knapp über der Marke liegt, ist ein Clip mit unauffälligem
Schlusswort der nächste Griff.

**Nach jedem Clipwechsel die Rate neu messen.** Sie ist eine Eigenschaft des
Klons, nicht des Sprechers: Derselbe Moderator kam mit dem neuen Clip auf
18,8 statt 16,7 Zeichen/Sekunde, ein Sprung von 13 Prozent. Mit den alten Budgets
wären seine Einheiten unnötig kurz geblieben. Deshalb steht dieser Abschnitt vor
dem nächsten.

### Raten messen und neu segmentieren, bei beiden Wegen gleich

```bash
python scripts/measure_rate.py --speakers <workdir>/refs/speakers.json --update \
    --only-missing \
    --ckpt <workdir>/model_f5tts_german.safetensors --vocab <workdir>/vocab.txt
python scripts/segment_speech.py words_final.json units.json --rate 14 \
    --duration <sek> --speakers <workdir>/refs/speakers.json
```

`--only-missing` überspringt Sprecher, die ihre Rate schon mitbringen — also alle
aus dem Archiv. Die Messung lädt das Modell und kostet Minuten je Stimme;
gespeicherte Raten sind bereits gemessen und gelten unverändert, solange der
Checkpoint derselbe ist. Wechselst du ihn, lässt du den Lauf einmal ohne die
Option durch und schreibst das Archiv mit `archive_voice.py --replace` nach.

**Die Sprechrate hängt bei geklonten Stimmen am Sprecher, nicht am Modell.**
Gemessen an einem Interview: 12,9 gegen 16,0 Zeichen/Sekunde zwischen Gast und
Moderator — ein Fünftel Unterschied. Ein gemeinsames Budget wäre für die langsame
Stimme zu großzügig, ihre Einheiten kämen durchweg gestaucht heraus. Deshalb
schreibt `measure_rate.py --update` die Rate je Sprecher in `speakers.json`, und
`segment_speech.py --speakers` vergibt daraus die Budgets pro Einheit.

Nimm den **p25-Wert**, nicht den Median — das Skript rechnet ihn schon aus. Mit dem
Median kommt die Hälfte der Einheiten zu lang heraus.

**Eine auffällig niedrige Rate ist ein Befund über den Clip, nicht über den
Sprecher.** Das ist das billigste Signal für einen schlechten Referenzclip, weil
`measure_rate.py` es ohnehin ausrechnet — du bekommst es geschenkt, während der
Klang selbst erst in Schritt 9b auffällt. Gemessen an einer Pressekonferenz mit
achtzehn Stimmen: Ein Klon kam auf **8,5 Zeichen/s**, während alle anderen zwischen
10,8 und 18,9 lagen. Aus einem anderen Ausschnitt derselben Person neu geschnitten
waren es **12,5** — ein Sprung um die Hälfte, allein durch den Clip.

Sieh dir deshalb die Ratenspalte als Ganzes an, bevor du neu segmentierst.
Faustregel aus den bisherigen Läufen: Deutsche Klone liegen zwischen etwa 11 und
19 Zeichen/s. Was deutlich darunter fällt, hat ein Clipproblem — und die Folge wäre
sonst, dass genau diese Stimme unnötig knappe Budgets bekommt und du ihre Sätze
grundlos zusammenstreichst.

Den Ersatzclip suchst du dann nicht auf Verdacht, sondern nach Zeichendichte —
die sagt die neue Klonrate voraus, bevor du schneidest. Siehe „Welche Einheit du
als Ersatz nimmst" weiter oben.

**Bei nur einem Sprecher** meldet `diarize.py` einen Sprecher und du kannst
`build_voiceover.py` auch direkt mit `--ref` und `--ref-text` füttern.

### Der Klon trennt Sprecher, er bildet sie nicht nach

**Versprich keine Stimmähnlichkeit zum Original**, weder dem Nutzer noch dir selbst.
Gemessen an einem Interview mit zwei männlichen Sprechern über acht identische Sätze
je Stimme: Die tiefere Originalstimme kam **höher** heraus (102,3 → 109,4 Hz), die
höhere tiefer (109,0 → 101,3 Hz). Die Tonhöhe wird also nicht übernommen, sondern
vertauscht. Der Abstand der Klone zueinander stimmt dagegen ungefähr, die Sprecher
bleiben unterscheidbar. Nützlich ist das Klonen damit für die *Trennung*, nicht für
die *Ähnlichkeit*.

Es gibt keine Einstellung, die das behebt — gemessen über `cfg_strength` 2/3/4 und
`nfe_step` 32/64 bleibt der Fehler bei etwa ±7 Hz. **Die Voreinstellung ist so gut
wie es wird**, dreh nicht daran. Was hälfe, wäre ein Finetune auf den Zielsprecher,
also Training statt Inferenz.

Die Referenz ist **hart auf 12 Sekunden begrenzt** (`utils_infer.py` schneidet in
drei Stufen zurück). Längere Clips bringen nichts; beide Diarisierungsskripte
schneiden deshalb maximal 11 Sekunden. Ein Clip, der nicht trägt, wird also nicht
länger, sondern **anders** gewählt — ein anderer Ausschnitt derselben Stimme, mit
Satzanfang und ruhiger Sprechweise.

## Schritt 7 — Übersetzen, für's Hören

Das ist der Schritt, der über die Qualität entscheidet. Eine Untertitel-Übersetzung
hinterher zu vertonen funktioniert, ist aber deutlich schlechter: gemessen 32 %
gestauchte Einheiten und bis zu 2,1 s Versatz gegen 8 % und 0,5 s, wenn von
vornherein fürs Hören übersetzt wird. Was am Ende gut ist, steht als Skala in
Schritt 9.

Exportier die Originalsprache mit Budget, eine Zeile je Einheit:

```
<index>|<mm:ss>|<slot>s|<budget>|<originaltext>
```

**Der Index zählt ab null.** `validate_vo.py` gleicht ihn gegen die Position in
`units.json` ab, und eine Nummerierung ab eins verschiebt die gesamte Spur um eine
Einheit gegen das Bild.

Regeln, die der Übersetzer einhält:

- **Im Zeichenbudget bleiben.** Bis etwa 1,25-fach fängt die Stauchung das ab,
  darüber wird es hörbar schnell.
- **Zahlen ausschreiben**, auch Ordinalzahlen: „im zehnten Jahrhundert",
  „siebenundachtzig Tage", „zweitausendsechs". Der Übersetzer weiß, ob eine
  Ziffernfolge Zahl oder Eigenname ist; ein Regelwerk muss raten.
- **Keine Auslassungspunkte**, keine eckigen Klammern, keine Abkürzungen
  (`z. B.`, `ca.`, `%`, `/`).
- **Kurze Hauptsätze statt Schachtelsätze.** Zuhörer können nicht zurückspringen.
  Ein deutscher Nebensatz mit Verb am Ende ist gelesen elegant und gehört zäh.
- **Straffen ist erlaubt und nötig.** Deutsch braucht mehr Zeichen als die meisten
  Quellsprachen. Redundanz, Füllwörter und Selbstkorrekturen des Sprechers fallen weg.
- **Eigennamen nach `hungarian.md` umschreiben.** Dort steht die feste Umschrift
  je Wort, dazu die Regeln, aus denen du ein neues Wort beim ersten Vorkommen
  bildest. Die Umschrift wird einmal gebildet und danach nicht mehr geprüft —
  keine Lautschrift, keine Klammerhinweise, kein SSML.
- **Den Vornamen nur bei der ersten Nennung setzen**, danach den Nachnamen
  allein und mit einem deutschen Wort davor („über Solyom", „Herrn Sulyok").
  Zwei fremde Namen hintereinander verschmilzt F5-TTS zu einem Fantasiewort.

Schreibe die Übersetzung als `<index>|<deutscher Text>` in mehrere Dateien
(`vo_01.txt`, `vo_02.txt`, …). Bei mehreren hundert Einheiten ist das erheblich
weniger Schreibarbeit als JSON und macht Nachkorrekturen zu Ein-Zeilen-Änderungen.

## Schritt 8 — Validieren

```bash
python scripts/validate_vo.py units.json cues_vo.json vo_*.txt --override vo_fix.txt
```

Bricht ab bei Ziffern, Auslassungspunkten, Klammern, Abkürzungen, fehlenden oder
doppelten Indizes. **Ein fehlender Index verschiebt die gesamte Spur gegen das
Bild, ohne dass es später auffällt** — deshalb ist die Vollständigkeitsprüfung
härter als die Längenprüfung.

Längenkorrekturen gehören in die `--override`-Datei, nicht in die Übersetzung. Das
hält den Haupttext unangetastet und macht nachvollziehbar, was nur aus Zeitgründen
gekürzt wurde.

**Denselben Index zweimal zu überschreiben ist ein Versehen, kein Schichten.**
Die Override-Datei wächst über den Durchlauf: erst die Längenkürzungen aus dieser
Prüfung, später die Reparaturen aus der Gegenprobe in Schritt 9b. Dabei fasst man
dieselbe Einheit leicht ein zweites Mal an — im beobachteten Fall stand eine
Einheit einmal mit korrigierter Namensschreibweise und einmal in der alten Fassung
darin. Es gewinnt die **zuletzt genannte** Zeile, und das ist genauso wahrscheinlich
die verworfene wie die gewollte Fassung. Sichtbar wird es sonst nirgends: Die
Zeichenzahl stimmt, die Vollständigkeitsprüfung stimmt, und die Gegenprobe hast du
zu dem Zeitpunkt schon hinter dir.

`validate_vo.py` meldet das inzwischen mit beiden Zeilennummern und schreibt keine
Cue-Datei. Räumst du die Datei von Hand auf, achte auf die Richtung: „letzte Zeile
gewinnt" hält die *ältere* Fassung, wenn du die Korrektur oben eingefügt hast.

## Schritt 9 — Synthetisieren

```bash
python scripts/build_voiceover.py cues_vo.json vo.wav --duration <sek> \
    --ckpt <workdir>/model_f5tts_german.safetensors --vocab <workdir>/vocab.txt \
    --speakers <workdir>/refs/speakers.json
```

Passt jede Einheit in ihren Slot: Wo der deutsche Text zu lang ist, erhöht das
Skript F5s `speed` (Obergrenze 1,45) — also tatsächlich schnelleres Sprechen statt
nachträglicher Zeitdehnung, dadurch keine Stretch-Artefakte.

**Platziert wird überlappungsfrei.** Eine Einheit beginnt nie, bevor die vorige zu
Ende gesprochen hat; der Verzug wird in der nächsten echten Pause abgebaut. Die
Alternative — an der Originalzeit festhalten und überlappen lassen — wurde probiert
und ist hörbar schlechter: 57 Stellen mit bis zu einer Sekunde Doppelstimme.

Die gemeldeten Zahlen sind dein Qualitätsmaß **für die Einpassung**. Eine Skala,
die für den ganzen Skill gilt:

| gestaucht | Urteil |
|---|---|
| unter 5 % | so soll es aussehen, nichts zu tun |
| 5 bis 10 % | in Ordnung |
| über 25 % | die Übersetzung ist zu lang — dort kürzen, nicht hier nachregeln |

Der Versatz sollte dabei unter einer halben Sekunde bleiben.

**Null gestaucht ist erreichbar**, und zwar nur, wenn beides zusammenkommt: Budgets
pro Sprecher aus `measure_rate.py --update` und eine Übersetzung, die von vornherein
fürs Hören geschrieben ist. Gemessen: 0 von 565 Einheiten bei einem 60-Minuten-Panel
(Raten 13,4 bis 18,7 Zeichen/s, ein gemeinsamer Wert hätte die langsamen Stimmen
überfahren), 1 von 318 bei einem 37-Minuten-Interview, 26 von 569 bei einer
66-Minuten-Diskussion. Dass ein gemeinsamer Ratenwert manchmal genügt hätte,
erkennst du erst nach der Messung.

Ob die Synthese auch sagt, was im Cue steht, sagen diese Zahlen nicht. Dafür ist
Schritt 9b da.

**Tempo:** Auf einer RTX 5090 rund 4-fache Echtzeit, eine halbe Stunde Sprache also
in etwa acht Minuten. F5-TTS gibt Pegel über 1,0 aus (gemessen 1,29); die Skripte
normalisieren deshalb, statt zu clippen — sonst verzerren genau die lauten Silben.

### Schritt 9b — Zurücklesen lassen (nicht optional)

Stauchungs- und Versatzzahlen bleiben tadellos, während die Stimme Unsinn spricht.
Miss deshalb, ob die Synthese sagt, was sie sagen soll:

```bash
python scripts/bench_subset.py cues_vo.json <workdir>/refs/speakers.json \
    <workdir>/bench --per-speaker 10
python scripts/synth_samples.py <workdir>/bench_cues.json <workdir>/bench \
    --ckpt <workdir>/model_f5tts_german.safetensors --vocab <workdir>/vocab.txt \
    --speakers <workdir>/bench_speakers.json
python scripts/check_intelligibility.py <workdir>/bench
```

**Mach das vor der Vollsynthese, nicht danach.** Der Lauf kostet ein paar Minuten
und spart dir eine Viertelstunde Neurechnen, wenn eine Stimme kippt.

`synth_samples.py` labelt je Sprecher, die Tabelle bekommt also eine Zeile pro
Stimme. **Ein Referenzclip, der schlecht klont, fällt genau dort auf und sonst
nirgends** — der Rest der Pipeline sieht ihn nicht.

**Deshalb `bench_subset.py` statt `synth_samples.py --count`.** Dessen Auswahl läuft
positionsbasiert über die ganze Datei. Eine Stimme in einem engen Indexbereich — ein
eingespielter Clip ist genau das — zieht dabei null Proben: Bei `--count 12` über
sieben Stimmen blieben zwei komplett ungemessen. `bench_subset.py` nimmt eine feste
Zahl je Sprecher, kürzeste zuerst.

Zum Nachmessen genau der Einheiten, die du überarbeitet hast:
`bench_subset.py … --only 0 436 443`.

**Lesen der Zahlen — und zwar nur auf zwei Dinge hin.** Die Wortfehlerrate
vergleicht Schreibungen und ist bei Eigennamen blind: Sie zählt jede Näherung als
Fehler, obwohl der Name richtig gesprochen wurde. Einzelwerte zwischen zwanzig
und fünfzig Prozent sind deshalb fast immer Namensrauschen und **kein Befund** —
die Aussprache wird hier nicht repariert, dafür gibt es `hungarian.md`.

**Dieselbe Blindheit trifft ausgeschriebene Zahlen.** Der Cue verlangt sie in
Worten, die Rücklesung schreibt sie in Ziffern zurück: `fünfzig Milliarden` kommt
als `50 Milliarden` an und zählt als ein Fehler von zwei Wörtern. Bei einer
zahlenlastigen Passage hebt das den Wert einer Stimme um mehrere Punkte, ohne dass
an der Synthese etwas falsch wäre. Gemessen an einer Haushaltsdebatte: 18 % für die
Hauptstimme, kein einziger Wert über 100 %, und jede der auffälligen Zeilen war eine
Zahl. Sieh dir die Zeilen deshalb an, bevor du eine Zahl für einen Befund hältst.

Was zählt, ist:

- **Über 100 % bei einer Einheit.** Dort halluziniert die Synthese, sie sagt
  etwas völlig anderes als der Cue. Lies deshalb immer die Spalte `>100%`, nicht
  den Mittelwert — eine einzige solche Einheit reißt den Schnitt ihrer Stimme auf
  700 %, während alle anderen sauber sind.
- **Eine Stimme deutlich schlechter als die anderen.** Das ist der Referenzclip,
  nicht der Text, und es ist der einzige Ort, an dem ein schlecht geschnittener
  Clip überhaupt auffällt.

Gemessene Werte zum Vergleich: 4,3 % über 61 Einheiten einer Ansprache mit
geklonter Sprecherstimme. In einer Diskussionsrunde lagen sechs von sieben Stimmen
zwischen 2,9 % und 16 %. Ein Interview mit zwei Sprechern kam auf 7,0 und 9,3 %.

### Was auffällige Einheiten haben — in dieser Reihenfolge prüfen

Fast alle echten Ausfälle in 9b haben eine von drei Ursachen, und sie kosten
unterschiedlich viel Zeit. Arbeite die Liste **von oben nach unten** ab — die
erste ist die einzige, die nicht am Text liegt, und die billigste zu beheben.

**1. Ein vorangestelltes Füllwort, das nicht im Cue steht** („Ja,", „Hier Leute,",
„Silly,"). Das ist die einzige Ursache, die **nicht** am Text liegt. Häuft es sich
bei *einer* Stimme und fehlt bei den anderen, ist der Referenzclip schuld — siehe
„Der Referenzclip muss an einer Satzgrenze beginnen und enden" in Schritt 6. Am Text zu
drehen macht es dort schlimmer: Im Testfall stieg die Rate durch einen verlängerten
Einheitenanfang von 22 % auf 36 %.

**Ein sauberer Satzanfang schließt diese Ursache nicht aus.** In einem zweiten Lauf
trug der Clip Satzanfang und Satzende und produzierte das Füllwort trotzdem; erst
ein Clip mit höherer Zeichendichte war frei davon (18,0 % auf 7,9 %). Wenn du also
schon am Satzanfang nachgebessert hast und das Muster bleibt, ist der nächste Griff
ein **schnellerer** Clip derselben Stimme, nicht der Text — siehe „Welche Einheit
du als Ersatz nimmst" in Schritt 6.

**2. Die Einheit ist zu kurz.** Der häufigste Fall, und er tarnt sich als
Namensproblem. Ein Ortsname in einer Einheit von 32 Zeichen blieb durch **alle
sechs** getesteten Schreibvarianten hindurch falsch, während dieselbe naive
Schreibweise im längeren Satz sauber zurückkam. Ein alleinstehender Name kam als
„Lars Loh" zurück, wo „László" stand; mit einem Halbsatz drumherum („Und die Frage
an László.") war er fehlerfrei.

Der Test kostet zwei Minuten: denselben Namen einmal in der kurzen
Originaleinheit und einmal in einem vollen Satz synthetisieren und zuruecklesen
lassen. Faellt nur die kurze Fassung aus, ist die Einheit zu kurz — umschreiben
und die Schreibweise unangetastet lassen.

Position im Satz zaehlt mit: Am Satzanfang und am Satzende verschmilzt der Name
mit dem Nachbarwort (`in Ceuta zurueck` → „Seutter-Zurueck“), eingebettet mit
Folgekontext laeuft er sauber. Bau den Namen deshalb mit einem deutschen Wort
davor und etwas Text dahinter ein, statt ihn an den Rand zu stellen.

**3. Das Satzgerüst fehlt — oder die Wortstellung klemmt.** Bei sehr kurzen
Einheiten kann F5-TTS doch in eine Wiederholschleife kippen, nicht über die Spur,
aber innerhalb der Einheit: „Echt gute Punkte." auf 1,6 Sekunden kam als „Und? Und?
Und? …" zurück, **7400 %**. Eine einzige solche Einheit reißt den Schnitt ihrer
Stimme auf 770 %, während alle anderen sauber sind — lies deshalb immer die Spalte
`>100%`, nicht nur den Mittelwert.

Die Reparatur ist ein **vollständiger Satz mit Subjekt und Verb**, nicht bloß „mehr
Kontext": `Echt gute Punkte.` → `Er bekommt gute Punkte.`, `Natürlich, denn` →
`Natürlich ist das so, denn`, `Von ihrer Seite.` → `Das ist ihre Seite.` Reproduziert
an einer Diskussionsrunde, wo drei Fragmente einer Stimme („Also solange", „Ich gebe
also", „ist Mi Hazánk.") dreimal denselben halluzinierten Satz erzeugten; als
vollständige Sätze fiel die Stimme von 141 % auf 15 %.

**Ein finites Verb ist aber keine Garantie.** Gemessen an einer Einheit von 1,2
Sekunden: `Ist das endlich?` kam als „Letztendlich ist" zurück (100 %), obwohl
Subjekt und Verb dastehen. Einen Satz zu bauen wäre hier falsch — der Slot gibt
keine Zeichen her. Was half, war eine andere Wortstellung bei *gleicher* Länge:
`Das ist endlich?` (16 Zeichen, sauber) gegen `Ist das endlich?` (16 Zeichen,
100 %). Probier deshalb bei einer kurzen Einheit über 100 % **zuerst eine andere
Wortstellung bei gleicher Länge**. Erst wenn das nichts bringt, ist das Satzgerüst
die Ursache und Verlängern der richtige Griff.

**Eine Ursache steht bewusst nicht auf dieser Liste: die Schreibweise des
Namens.** Sie wird hier nicht getestet und nicht repariert. Umschriften stehen
fest in `hungarian.md` und werden beim ersten Vorkommen einmal gebildet — ein
Variantenvergleich gegen die Synthese misst den Zufall, nicht die Schreibung.

### Zwei Muster, die du beim Übersetzen gleich vermeidest

Beide entstehen beim Übersetzen laufend und kosten dich sonst eine Runde Gegenprobe.

**Zwei- bis vierwortige Vorstellungen mit Kürzel.** Der häufigste Ort für ein
Kürzel ist der ungünstigste: der Moderationsaufruf („Danke. HVG.") und die
Selbstvorstellung („Réka Debreceni, Portfolio."). Dort kippt die Synthese —
gemessen 150 %, 100 % und 100 %, während dieselben Kürzel in vollen Sätzen
durchliefen. Die Ergänzung muss dabei ins Zeitbudget passen; „Jetzt fragt",
„Ich bin … von …" und „Die nächste Frage kommt von …" sind billige Füllungen:

| vorher | nachher | WER |
|---|---|---|
| `Danke. HVG.` | `Danke. Jetzt fragt Ha Fau Geh.` | 150 % → sauber |
| `Réka Debreceni, Portfolio.` | `Réka Debreceni von Portfolio.` | 100 % → 17 % |
| `Danke, hier bin ich.` | `Ich bin hier.` | 25 % → sauber |

Die letzte Zeile zeigt die Gegenrichtung: Wo nichts mehr hineinpasst, **kürze**
stattdessen, damit das Fragment vorne wegfällt.

**Der Doppelpunkt als Ankündigung.** Ein Doppelpunkt, der eine ganze Aussage
ankündigt statt eine Aufzählung einzuleiten, kippt die Stimme mitten im Satz — und
zwar unabhängig von der Länge. Gemessen an einer Einheit von 149 Zeichen: `Die naive
Frage: Sie glauben nicht, dass …` kam als „Die naive Frau um nicht, sagen es …"
zurück (50 %). Als zwei schlichte Sätze — `Zuerst die naive Frage. Glauben Sie
nicht, dass …` — fiel dieselbe Einheit auf 5 %. Der Aufzählungsdoppelpunkt
(`Sicher ist: Es gibt eine Kraft dahinter.`) war im selben Lauf unauffällig.
Rhetorische Aufhänger wie „Die Frage ist:" oder „Mein Punkt ist:" schreibst du
deshalb gleich als eigenen Satz. Prüf beim Nachbessern die Nachbareinheiten auf
dasselbe Muster; im Testfall stand es zweimal direkt hintereinander.

## Schritt 10 — Mischen und muxen

Erst eine Hörprobe, bevor du 50 Minuten encodierst:

```bash
python scripts/mux_voiceover.py "<video>" vo.wav probe.m4a --sample 300 45
```

Dann die volle Fassung:

```bash
python scripts/mux_voiceover.py "<video>" vo.wav "<kanal>-<kurzname>.de-vo.mkv" --audio-lang hun
```

`<kanal>-<kurzname>` ist der Name aus den Grundregeln — Kanal-Slug plus kurzer
deutscher Titel, nicht der Quellname. Ohne bekannten Kanal entfällt das Präfix.

Der Originalton wird per Sidechain-Kompression unter der Sprache weggeduckt und
bleibt in den Pausen hörbar. Stellschrauben, falls dem Nutzer die Balance nicht
passt: `--original-gain` (Grundpegel), `--duck-ratio` (Stärke), `--duck-release`
(höher setzen, wenn es pumpt). Neu mischen dauert zwei Minuten, weil das Video nur
kopiert wird — die Synthese muss nicht wiederholt werden.

Mit geklonten Stimmen darf der Originalton **leiser** liegen als früher: Er musste
Sprecherwechsel hörbar halten, solange alle Sprecher dieselbe deutsche Stimme
bekamen. Das erledigen jetzt die Stimmen selbst.

**Die Abtastrate ist kein Detail.** `loudnorm` schaltet seine Ausgabe auf 192 kHz
um, unabhängig davon, was davor im Graphen steht — ein `aformat` mit 48 kHz vor dem
Filter greift also nicht. Ohne abschließendes Resampling wählt der AAC-Encoder
daraufhin sein eigenes Maximum; beobachtet wurden 96 kHz. Am PC spielt das sauber,
auf einem Samsung-Fernseher kamen nur kurze verzerrte Bruchstücke, weil dessen
Decoder bei 48 kHz endet. `--sample-rate` steht deshalb auf 44100 und wird sowohl
im Filtergraphen als auch am Encoder gesetzt. Prüf die Rate in der Gegenprobe unten
mit, nicht nur die Spurbelegung.

Zum Abschluss gegenprüfen:

```bash
ffprobe -v error -show_entries "stream=index,codec_type,codec_name:stream_tags=language,title" \
    -of default=noprint_wrappers=1 "<kanal>-<kurzname>.de-vo.mkv"
```

## Stimmen ins Archiv aufnehmen — ein eigener Auftrag

**Das ist kein Schritt des Durchlaufs.** Es passiert, wenn der Nutzer es sagt, und
sein Auftrag sieht ungefähr so aus:

> Nimm für den Skill /voiceover die Stimme von Magyar Péter aus dem Video
> https://www.youtube.com/watch?v=… ins Archiv auf. Verwende den Zeitbereich von
> 1:00 bis 2:00.

Dann läuft genau ein Befehl:

```bash
python scripts/archive_voice.py "<url oder datei>" --from 1:00 --to 2:00 \
    --name "Magyar Péter" --note "Ministerpräsident" --lang hu
```

Er lädt nur den Bereich, transkribiert ihn, sucht darin den Clip, misst die Rate,
bildet den Fingerabdruck und schreibt den Eintrag. Der Checkpoint kommt aus dem
Hugging-Face-Cache, es sind keine Pfade anzugeben und kein Arbeitsordner nötig.

**Warum der Nutzer den Bereich wählt und nicht du.** Ob eine Person wiederkehrt,
weiß nur er. Und ob die Stelle sie gut zeigt — ruhig gesprochen, nicht
übertönt, nicht im Zwischenruf — hört er, während eine Messung dafür blind ist.
Frag nicht nach „besonders geeigneten" Clips und leite den Vorschlag nicht aus
`check_refs.py` ab; das war ein früherer Entwurf und ist bewusst entfernt.

**Was du beisteuerst, ist die Auswahl innerhalb des Bereichs.** F5-TTS schneidet
Referenzen über zwölf Sekunden hart zurück, aus zwei Minuten muss also ein
Ausschnitt werden. Das Skript nimmt dafür aufeinanderfolgende Einheiten, solange
keine Pause über 0,6 s dazwischen liegt, verlangt ganze Sätze an beiden Enden und
wählt unter den Kandidaten im Dichteband den **längsten**, nicht den dichtesten.
Der Unterschied ist real: nach Dichte sortiert kam ein 4,3-Sekunden-Clip heraus,
wo ein 6,4-Sekunden-Clip im selben Bereich lag.

**Der Bereich wird mit Puffer transkribiert, aber nur der Bereich selbst benutzt.**
Whispers Satzzeichen hängen vom Kontext ab, und die Clipauswahl hängt an den
Satzgrenzen — derselbe Ausschnitt lieferte isoliert transkribiert einen Clip mit
12,5 Zeichen/s, mit 45 Sekunden Kontext auf beiden Seiten einen mit 17,9. Das
Skript schneidet deshalb ein größeres Fenster, sucht Clips aber nur innerhalb
deiner Vorgabe und mittelt auch den Fingerabdruck nur darüber. Der Puffer könnte
eine andere Person enthalten; er dient ausschließlich der Interpunktion.

**Das ganze Video wird nicht durchsucht, und das ist eine Entscheidung.** Naheliegend
wäre, den Bereich nur als Saatkorn für eine Sprecherverifikation zu nehmen und den
Clip aus dem gesamten Video zu wählen. Gemessen bringt das fast nichts: 18,3 gegen
17,9 Zeichen/s beim besten Kandidaten. Es kostet dafür einen vollen
Transkriptionslauf statt zwei Minuten und verliert die Zusage, dass im Bereich
keine Störgeräusche liegen. Schlag es nicht erneut vor.

**Ein bis zwei Minuten Bereich sind eine gute Vorgabe.** Der Clip wird so oder so
nur ein paar Sekunden lang, aber der Fingerabdruck ist der Mittelwert über den
ganzen Bereich, und je mehr Material dort liegt, desto sicherer wird die Person
unter anderem Mikrofon wiedererkannt.

**Der Bereich muss eine einzelne Person enthalten.** Es wird nicht diarisiert —
das Skript nimmt an, was du ihm gibst. Ein Bereich mit Zwischenfrage darin
mischt zwei Stimmen in einen Fingerabdruck.

**Sporadische 403 beim Bereichsabruf sind normal.** YouTube lässt ffmpeg die
Bytebereiche nicht immer holen; das Skript versucht es zweimal und lädt dann die
volle Tonspur, um lokal zu schneiden. Das dauert länger und geht immer.

Einen besseren Clip derselben Person schreibst du mit `--replace` darüber.

## Was du dem Nutzer berichtest

- Pfad zum MKV, Spurbelegung, Anzahl der Sprech-Einheiten, Dauer.
- **Bei einer URL als Quelle**: wo die geladene Datei liegt, welche Auflösung und
  welche Tonspur du genommen hast, und ob die Quelle Zweitspuren anbot. Der Nutzer
  sieht sonst nicht, dass diese Wahl überhaupt getroffen wurde.
- Qualitätsklasse und was daraus folgte.
- **Wie viele Sprecher erkannt wurden, mit welcher Trennschärfe beziehungsweise
  Ankertreue**, welchen Weg du gewählt hast und woran du die Zuordnung gegengelesen
  hast. Bei schwacher Trennung sag es dazu.
- **Welche Sprecher aus dem Archiv kamen**, mit Ähnlichkeitswert, und welche neu
  geschnitten wurden. Bei einem bestätigten Zweifelsfall sag, dass du ihn
  bestätigt hast. Nenn auch **knappe Treffer nahe der Schwelle** — die Schwelle
  ist bewusst tolerant, also ist ein Wert um 0,45 bis 0,55 eine Angabe wert, die
  der Nutzer mit einem Blick ins Video prüfen kann.
- **Wenn zwei Sprecher auf dieselbe Archivstimme passten** und einer deshalb
  seinen Clip aus dem Video behalten hat.
- **Ob ein Referenzclip schlecht war und es keinen besseren gab** — mit dem
  Befund aus `check_refs.py`. Sonst hält der Nutzer die schwache Stimme für einen
  Fehler der Kette statt für eine Grenze der Quelle.
- **Ob eingespielte Clips im Material stecken** und wie viele Stimmen daraus
  insgesamt wurden — der Nutzer erwartet die Zahl der Leute im Bild, nicht die Zahl
  der Stimmen auf der Spur.
- **Die Einpassungszahlen**: wie viele Einheiten gestaucht, wie viele verzögert,
  maximaler Versatz. Das ist das ehrlichste Maß für die *Zeitpassung*.
- **Die Wortfehlerrate aus Schritt 9b, je Stimme**, und ob eine Stimme dabei
  auffällig aus der Reihe fiel. Sie misst nicht die Aussprache — die
  Rate ist bei Eigennamen blind —, sondern ob eine Stimme halluziniert oder einen
  schlechten Referenzclip hat. Nenn dazu die Einheiten, die du deswegen
  umgeschrieben hast.
- **Ob der Durchlauf Passagen verschluckt hatte und wo** — mit Zeitbereich, auch
  wenn sie repariert wurden.
- **Welche Abschnitte nicht rekonstruierbar waren** — mit Zeitbereich. Bei
  Voice-over besonders wichtig, weil sie im Audio spurlos fehlen.
- **Die Lizenz**, wenn der Nutzer das Ergebnis weitergeben will: CC-BY-NC-4.0.
- Inhaltlich heikle oder überraschende Funde benennen, samt Beleglage.
- Keine Genauigkeit behaupten, die das Material nicht hergibt.

## Stimmklonen: was erlaubt ist

Der Klon bildet die Stimme einer realen Person nach. Für privates Mitschauen ist
das unproblematisch. **Veröffentlichen** solltest du geklonte Stimmen realer
Personen nicht ohne deren Einverständnis, und der Checkpoint verbietet kommerzielle
Nutzung ohnehin. Wenn ein Nutzer das Ergebnis weitergeben will, sag beides dazu —
einmal, sachlich, ohne Belehrung.

**Das Archiv ist etwas anderes als ein Klon, der nach einem Video verschwindet.**
Sie ist eine dauerhafte Sammlung von Stimmreferenzen realer Personen. Für privates
Mitschauen ändert das nichts; es ist der Grund, warum `archive_voice.py` nur auf
ausdrücklichen Wunsch läuft und nicht als Teil des Durchlaufs. Weitergeben
solltest du den Ordner `voices/` nicht.

## Schritt 11 — Falschaussagen und Widersprüche melden

Dieser Schritt ist **subtraktiv**. Es geht nicht darum, neue Regeln aus deinem
Durchlauf zu ergänzen, sondern darum, den Skill von dem zu befreien, was
nachweislich nicht stimmt.

**Melde am Ende, wenn dein Durchlauf eine Aussage hier widerlegt hat oder wenn
zwei Stellen dir gegenläufige Anweisungen gegeben haben.** Melden und zur
Korrektur anbieten, nicht ungefragt umbauen — und erst, wenn die Tonspur fertig
ist. Die Korrektur besteht dann darin, die falsche oder die unterlegene der
beiden Aussagen **zu entfernen**, nicht sie um einen Sonderfall zu ergänzen. Ein
Widerspruch, den man durch Anbauen auflöst, ist danach zwei Absätze lang und
immer noch ein Widerspruch.

Zwei Sorten sind meldenswert:

- **Falschaussage.** Eine Anweisung hier hat dich in die Irre geführt, und du
  kannst das an deinem Lauf zeigen — der beschriebene Fehler trat nicht auf, der
  empfohlene Griff machte es schlechter, ein genannter Grenzwert passte nicht.
- **Widerspruch.** Zwei Stellen sagen Gegenläufiges, sodass die Reihenfolge, in
  der du sie liest, deine Entscheidung bestimmt. Das ist der gefährlichere Fall,
  weil beide Stellen für sich plausibel klingen.

### Warum hier nicht ergänzt wird

**Beide Modelle in dieser Kette sind stochastisch.** F5-TTS ist ein
Flow-Matching-Modell und startet jede Synthese aus zufälligem Rauschen; Whisper
dekodiert autoregressiv. Derselbe Text ergibt beim zweiten Lauf nicht dieselbe
Welle und nicht dieselbe Rücklesung. Eine Wortfehlerrate ist damit eine
**Stichprobe, kein Messwert** — Unterschiede von einigen Prozentpunkten zwischen
zwei Varianten können reines Rauschen sein.

Daraus folgt zweierlei. Erstens taugt eine Einzelbeobachtung an einem Video nicht
als allgemeine Regel; was bei dieser Stimme, diesem Referenzclip und dieser
Sprache trug, muss anderswo nicht tragen. Zweitens ist genau deshalb ein
Unterschied, der **groß** ist, trotzdem aussagekräftig: 20 % gegen 125 % ist kein
Rauschen, und eine Rücklesung, die das Zielwort korrekt schreibt, belegt die
Aussprache unabhängig von der Zahl daneben.

Miss deshalb, was du für diesen Durchlauf brauchst, und entscheide danach — aber
schreib das Ergebnis nicht als Regel fest, solange es an einer einzigen Quelle
hängt. Was hier stehen bleiben soll, sind die Prinzipien und das Vorgehen. Die
Einzelfälle findest du beim Arbeiten ohnehin, und sie kosten dich weniger Zeit,
als ein zugewachsener Skill dich kostet.
