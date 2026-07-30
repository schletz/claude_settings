---
name: summarize-video
description: Erstellt aus einem Videolink oder einer Video-/Audiodatei eine deutsche Zusammenfassung als AsciiDoc-Dokument samt PDF, mit Videodaten, Abstract, gegliederter Inhaltsbeschreibung, ausgewiesener eigener Einordnung und einer topografischen Karte der erwähnten Orte. Lädt YouTube-Quellen selbst herunter (nur Ton), transkribiert mit Whisper large-v3 und übersetzt fremdsprachiges Material ins Deutsche. Nutze diesen Skill, wenn der Nutzer um eine Zusammenfassung, Inhaltsangabe, ein Protokoll oder "worum geht es in diesem Video" bittet — auch bei englischen Formulierungen wie "summarize this video", "what is this video about", "give me the gist". Gedacht für politische Diskussionen, Interviews und Beiträge aus Gesellschaft und Technik in Sprachen, die der Nutzer nicht spricht. Erzeugt bewusst KEINE Untertitel (create-subs) und keine Tonspur (voiceover).
---

# Deutsche Videozusammenfassung als AsciiDoc

Erzeugt aus einem Videolink ein Dokument `<slug>.adoc`, das den Inhalt auf Deutsch
wiedergibt und **erkennbar getrennt davon** einordnet. Zielgruppe ist ein
österreichischer Leser, der die Sprache des Videos nicht spricht und die
handelnden Personen nicht kennt.

Die ersten Stufen — Download, Audioaufbereitung, Transkription — sind dieselben
wie in `voiceover`; die Skripte liegen als Kopie in `scripts/`. Ab dem Transkript
läuft dieser Skill eigene Wege.

## Grundregeln

- **Wiedergabe und Einordnung werden getrennt.** Der laufende Text sagt nur, was
  im Video gesagt wird, und schreibt es dem Sprecher zu („Fodor nennt das …").
  Alles, was du beisteuerst — Hintergrund, Bewertung, Faktencheck — steht in einer
  **Admonition** und nirgends sonst. Das ist die zentrale Anforderung dieses
  Skills; eine Einordnung, die als Inhaltsangabe durchgeht, ist ein Fehler.
- **Interpretieren ist erwünscht, nicht geduldet.** Der Nutzer will den Inhalt
  einordnen können. Ein Dokument ohne eine einzige Einordnung hat die Aufgabe
  verfehlt. Aber jede Einordnung ist als deine gekennzeichnet.
- **Nie raten.** Was das Transkript nicht hergibt, wird nicht erfunden. Eine
  unklare Passage wird als unklar benannt, mit Zeitmarke.
- **Dein Wissensstand ist nicht der Stand des Videos.** Politische Ämter,
  Parteizugehörigkeiten und Umfragewerte ändern sich. Prüfe Personenangaben per
  WebSearch, bevor du sie ins Dokument schreibst, und schreib bei allem, was sich
  ändern kann, den Stand dazu. Ein falsch zugeordnetes Ministeramt ist genau der
  Fehler, den der Nutzer nicht bemerken kann — er liest das Dokument ja, weil er
  es nicht weiß.
- **Whisper transkribiert nur, es übersetzt nicht.** Sein `task=translate` kann
  ausschließlich nach Englisch. Die Übersetzung ins Deutsche machst du selbst aus
  dem Transkript in der Originalsprache. Ist die Quelle deutsch, entfällt das.
- **Es wird nur der Ton geladen.** Eine Zusammenfassung sieht das Bild nie an,
  und eine 2160p-Quelle kostet Gigabytes für nichts. `fetch_source.py
  --audio-only`. Gemessen: 5,9 MB für 5:31, 12,7 MB für 11:56, 36,6 MB für
  37:43 — Sekunden statt Minuten Ladezeit.
- **Das Dokument landet im aktuellen Arbeitsverzeichnis**, nicht neben der
  Audiodatei im Downloads-Ordner.
- **Der Dateiname ist ein kurzer deutscher Slug**, nicht der YouTube-Titel und
  nicht die Video-ID. Nur `a-z`, `0-9` und Bindestriche, Umlaute ausgeschrieben
  (`ae`, `oe`, `ue`, `ss`), höchstens rund 40 Zeichen. Beispiel: `Súlyos válságba
  sodorta kishíján Magyarországot a Tisza leggyengébb minisztériuma? - Fodor
  Gábor` → `tisza-ministerium-krise-fodor`. Nenn den gewählten Namen im
  Abschlussbericht.
- **Vor den Titel-Slug kommt der Kanalname**, sobald die Quelle von YouTube oder
  einer anderen Plattform mit Kanalangabe stammt: der Slug lautet dann
  `<kanal>-<titel>`, das Dokument also `<kanal>-<titel>.adoc`. Damit sortieren
  sich die Zusammenfassungen eines Kanals nebeneinander, und man sieht der Datei
  an, aus welcher Ecke der Beitrag kommt. Der Name steht im Bericht von Schritt 0
  in der Zeile `Kanal:` und nachträglich in `<id>.info.json` unter `uploader`,
  ersatzweise `channel`. Slugifiziere ihn nach denselben Regeln wie den Titel und
  kürz ihn auf das unterscheidende Kernwort: generische Anhängsel wie `TV`,
  `Official`, `Channel`, `News`, `Media` oder ein `- Topic` fallen weg, rund 20
  Zeichen sind die Grenze. `Partizán` → `partizan`, `Telex.hu` → `telex`,
  `ZDFheute Nachrichten` → `zdfheute`. Bringt der Nutzer eine eigene Datei mit und
  ist kein Kanal bekannt, entfällt das Präfix — rate ihn nicht aus dem Dateinamen.
  Beispiel: Kanal `Partizán` plus der Titel oben →
  `partizan-tisza-ministerium-krise-fodor.adoc`. Alle abgeleiteten Dateien —
  `<slug>.pdf`, `<slug>-karte.png`, `<slug>-<thema>.svg` — tragen das Präfix
  automatisch mit, weil `<slug>` unten immer diesen vollständigen Namen meint.
- **Die Zusammenfassung ist privat.** Es gelten keine Veröffentlichungsstandards,
  eine deutliche Meinung in einer NOTE ist in Ordnung. Faktentreue gilt trotzdem.

| Skript | Zweck | Schritt |
|---|---|---|
| `fetch_source.py` | Quelle von einer URL laden, Originalspur wählen | 0 |
| `probe_audio.py` | Tonspur analysieren — nur bei mitgebrachten Dateien | 2 |
| `prepare_audio.py` | 16 kHz Mono-WAVs erzeugen | 2 |
| `transcribe.py` | Dekodieren, Wortzeiten erzeugen | 3 |
| `check_coverage.py` | verschluckte Passagen aufspüren | 3b |
| `patch_words.py` | nachdekodierte Stellen einspleißen | 3b |
| `render_transcript.py` | Wortzeiten zu lesbaren Absätzen mit Zeitmarken | 4 |
| `adoc_header.py` | Header und Videodaten aus der `info.json` schreiben | 6 |
| `render_map.py` | topografische Übersichtskarte der erwähnten Orte | 6b |
| `check_adoc.py` | Struktur und Markdown-Rückfälle prüfen | 7 |
| `render_adoc.py` | mit Asciidoctor in Docker nach PDF wandeln und prüfen | 7 |

**Ein Interpreter für alles.** Whisper braucht torch mit CUDA; auf diesem Rechner
ist das `C:\python\python.exe`. Alle Skripte laufen darauf. `render_adoc.py`
braucht zusätzlich das Paket `docker` (`python -m pip install docker`) und ein
laufendes Docker Desktop.

**Dateinamen unter Windows.** Was du in Schritt 0 lädst, heißt nach der Video-ID
und ist unbedenklich. Bringt der Nutzer eine eigene Datei mit, trägt sie oft
Sonderzeichen; über das Bash-Tool kommen die als `?` an und ffprobe meldet `No
such file or directory`. Nimm dafür das PowerShell-Tool und hol den Pfad über
`Get-ChildItem`, statt ihn zu tippen. Bei Python-Einzeilern zur Diagnose
`PYTHONIOENCODING=utf-8` setzen, sonst scheitert `print` an Zeichen wie `ő`.

## Schritt 0 — Quelle laden

```bash
python scripts/fetch_source.py "<url>" --audio-only --outdir C:/Users/Michael/Downloads
```

Das Skript nagelt die **Originaltonspur** fest, statt sie yt-dlp zu überlassen.
YouTube liefert für viele Videos synchronisierte Zweitspuren; erwischst du einen
Dub, fasst du eine Maschinenübersetzung zusammen und merkst es nie. Sind mehrere
Sprachen im Angebot und keine als Original markiert, bricht es ab statt zu raten —
dann Formate mit `python -m yt_dlp -F "<url>"` ansehen und mit `--audio-id`
vorgeben.

Der Bericht liefert alles, was die folgenden Schritte brauchen: Titel, Kanal,
Laufzeit, Originalsprache und **Kapitelmarken**. Titel und Kanal ergeben zusammen
den Slug für alle Ausgabedateien — nimm sie aus dem Bericht, nicht aus dem
Dateinamen, der ja nur die Video-ID trägt. Die Kapitel sind ein
Gliederungsvorschlag des Uploaders — ein guter Startpunkt für die Abschnitte in
Schritt 6, aber kein Ersatz für die eigene Gliederung.

Daneben liegt `<id>.info.json`. Die brauchst du in Schritt 6; lösch sie nicht.

Wenn der Download scheitert:

- **„Sign in to confirm you're not a bot"** → `--cookies-from-browser edge`,
  notfalls Edge vorher schließen.
- **„No supported JavaScript runtime could be found"** ist meist Rauschen. Kommt
  eine Quelle auffällig schlecht heraus oder fehlt eine Sprachspur, die die
  Weboberfläche anbietet, hilft `--js-runtime node` (Node liegt unter
  `C:\nodejs\node`).
- **Playlist-URL** → das Skript bricht ab, einzelne Video-URL angeben.
- **Laufzeit weicht von den Metadaten ab** → das Skript warnt selbst. Erneut
  starten, yt-dlp setzt fort. Ein abgeschnittener Download sieht sonst aus wie
  ein vollständiges Video, und du merkst es erst, wenn die Zusammenfassung
  mittendrin endet.

Bringt der Nutzer eine Datei statt einer URL mit, entfällt dieser Schritt — dann
gibt es aber auch keine `info.json`, und die Videodaten in Schritt 6 baust du aus
dem, was du hast (Dateiname, `ffprobe`, Angaben des Nutzers). Was du nicht weißt,
lässt du weg, statt es zu erfinden.

## Schritt 1 — Sprache bestätigen

Frag per AskUserQuestion nach der gesprochenen Sprache — **außer der Nutzer hat
sie schon genannt**. `fetch_source.py` meldet die Sprache aus den Metadaten;
stell sie als erste Option voran, aber lass sie bestätigen: Das ist eine Angabe
des Hochladenden, keine Messung. „Automatisch erkennen" ist eine der Optionen,
aber nur zweite Wahl — eine falsch geratene Sprache ruiniert den ganzen
Durchlauf.

Ist die Sprache Deutsch, sag das dem Nutzer: Es wird dann nicht übersetzt, und
der Aufwand endet früher.

## Schritt 2 — Audio aufbereiten

Für eine YouTube-Quelle ist das Material immer Klasse A. Kein Probelauf, ein
Durchgang über die unbearbeitete Spur:

```bash
python scripts/prepare_audio.py "<audio>" --outdir <workdir> --profile A
```

Arbeitsordner ins Scratchpad, nicht neben die Quelle.

**Nur bei mitgebrachten Dateien** — Digitalisate von VHS oder Kassette, Mitschnitte
aus einem Saal — vorher `probe_audio.py "<datei>"` laufen lassen und dessen
Qualitätsklasse als `--profile` übernehmen. Bei Dateien über etwa 30 Minuten
dauert dieser Lauf mehrere Minuten, weil er die Spur mehrfach vollständig
dekodiert; dann gleich im Hintergrund starten.

## Schritt 3 — Transkribieren

```bash
python scripts/transcribe.py <workdir> --mode full --variants raw --lang hu \
    --words --max-chunk 240 --out words.txt --json words.json
```

**`--words` ist nicht optional**, auch wenn die Zusammenfassung keine Wortzeiten
braucht: Schritt 3b findet verschluckte Passagen nur über die Zeitachse.

**`--max-chunk 240` bei allem über etwa zwanzig Minuten.** Der Volldurchlauf
bricht sonst hart ab — kein Traceback, kein brauchbarer Exitcode, leere
Ausgabedatei. Nimm 240 und nicht 300: Der Abbruch hängt an der Länge des
*einzelnen* Blocks, und mit 300 bleibt am Ende regelmäßig ein Rest von fast 400
Sekunden stehen. Jeder fertige Block wird zwischengespeichert; nach einem Abbruch
denselben Befehl erneut starten, dann kommen die fertigen Blöcke aus dem Cache.

Die Meldung `raw.wav: 1 Bloecke` bei einer langen Datei heißt, dass keine Pausen
gefunden wurden — dann `--silence-db` vorgeben.

**Rechenzeit.** Gemessen auf einer RTX 5090: 55 Minuten Ton in rund zwanzig
Minuten, Modellladen eingerechnet — also etwa dreifache Echtzeit, nicht die
zehnfache, die man von Kurzclips kennt. Ein 5:31-Video war nach einer Minute
fertig, das 37:43-Interview brauchte allein rund sechzehn. Bei mehreren Videos
lohnt sich ein Lauf im Hintergrund; der Modelldownload passiert nur einmal, wenn
du alle Dateien in einem Aufruf hintereinander abarbeitest.

### Schritt 3b — Abdeckung prüfen (nicht optional)

```bash
python scripts/check_coverage.py words.json
```

**Der Langform-Dekoder verschluckt gelegentlich ganze Passagen, ohne das zu
melden.** Der Text liest sich danach völlig flüssig — für eine Zusammenfassung
ist das der gefährlichste Fehler überhaupt, weil ein fehlendes Argument keine
Lücke hinterlässt, die man sehen könnte. Sichtbar wird es nur an der Zeitachse:
ausgedünnte Wörter oder ein einzelnes Wort mit einem Zeitstempel über eine halbe
Minute.

Nicht jede Meldung ist ein Fehler — ein Musik-Intro erscheint als Folge leerer
Fenster, eine Atempause als Lücke. Erklären musst du sie trotzdem.

**Die häufigste Meldung ist harmlos, und du erkennst das an einer Zahl.** In drei
Testläufen kamen ausschließlich Einzelwörter über drei Sekunden Dauer — `Als`,
`So`, `Ja,` am Satzanfang und ein langes ungarisches Kompositum. Kein einziger
dünn besetzter Abschnitt, keine Lücke. Das Unterscheidungsmerkmal: **Ein echter
Dropout meldet sich zusätzlich als dünn besetzter Abschnitt**, weil eine halbe
Minute Sprache fehlt. Ein gedehntes Einzelwort ohne Begleitmeldung ist ein
Zeitstempelartefakt.

Beleg holst du dir mit einem Kurzclip unter 30 Sekunden über die Stelle, nicht
mit einem Reparaturclip:

```bash
python scripts/transcribe.py <workdir> --mode zoom --variants raw --lang hu \
    --spans "1390-1418"
```

Steht dort derselbe Text wie im Volldurchlauf, fehlt nichts, und du notierst das
im Abschlussbericht. Genau so verlief die Prüfung des ungarischen Testvideos.

Reparatur: Bereich großzügig als eigenen Clip schneiden, für sich dekodieren, mit
`patch_words.py` einspleißen, erneut prüfen. Verschluckt der Reparaturclip die
Stelle wieder, schneide ihn **kürzer als 30 Sekunden** — dann dekodiert Whisper
in Kurzform, und die hat den Fehler nicht.

Die Abo-Floskel (`Köszönöm, hogy megnéztétek`, „Untertitel von …") am Dateiende
mit `patch_words.py --drop-after <sekunde>` wegschneiden, nicht nach Textmustern
filtern: Ein Filter auf `amara` löscht auch das ungarische Wort `Hamarabb`. Steht
dieselbe Floskel mitten in der Datei, ist sie kein Abspann, sondern die Tarnung
eines Aussetzers — die Wörter sind dann über die verschluckte Passage gedehnt,
und du brauchst einen Reparaturclip. Tragen alle Floskelwörter dagegen denselben
Zeitstempel mit Dauer null, füllen sie nur eine Denkpause; dann löscht du sie aus
`words_final.json` und sonst nichts.

## Schritt 4 — Transkript lesbar machen

```bash
python scripts/render_transcript.py words.json --out transcript.txt
```

Hast du in Schritt 3b gepatcht, ist es `words_final.json` — nimm die, sonst
fasst du eine Fassung mit der Lücke zusammen.

Gruppiert die Wörter zu Absätzen von rund einer halben Minute, geschnitten an
Satzenden, die in einer Sprechpause liegen, und stellt jedem Absatz seine
Startzeit voran:

```
[04:12] Az energiaválság kezelése a minisztérium feladata lett volna, de …
```

**Diese Zeitmarken sind die einzigen, die ins Dokument dürfen.** Erfinde keine.
Der Nutzer springt damit ins Video zurück, und eine um zwei Minuten falsche Marke
ist ärgerlicher als gar keine.

Das Skript meldet Zeichenzahl und Absatzverteilung. Gemessene Werte zum
Vergleich: 7 Absätze mit Median 47 s für 5:29, 13 Absätze mit Median 60 s für
11:55, 47 Absätze mit Median 48 s für 37:42.

**Zerteilt wird nach Satzzeichen und Länge, nicht nach Pausen — das ist keine
Sparmaßnahme, sondern der einzige Weg.** Whispers Wortzeiten kennen praktisch
keine Pausen: gemessen über eine zwölfminütige englische Aufnahme lag die
mittlere Lücke zwischen zwei Wörtern bei 0,00 s, das 99. Perzentil bei 0,16 s
und die größte Lücke der ganzen Datei bei 0,40 s. Auch nach einem Satzende
beträgt die Lücke im Median null. Wenn dir also einfällt, `render_transcript.py`
um eine Pausenschwelle zu erweitern: Das wurde probiert, es löst nie aus.

Satzzeichen sind dünn gesät — dieselbe englische Datei hatte 31 Satzenden auf
2779 Wörter, mit bis zu 222 s zwischen zweien. Deshalb liegt die harte Grenze
bei dem Anderthalbfachen des Ziels; ohne sie produziert ein schneller Sprecher
minutenlange Blöcke.

Lies das Transkript vollständig, bevor du gliederst — nicht abschnittsweise beim
Schreiben. Ein Interview kommt oft erst nach zwanzig Minuten zu seinem
eigentlichen Thema, und eine Gliederung, die vorne entsteht, hängt dann schief.

## Schritt 5 — Tiefe abstimmen

Bei komplexen Themen frag per AskUserQuestion nach, **bevor** du schreibst —
nicht hinterher. Sinnvoll ist das, wenn das Video einen Sachverhalt voraussetzt,
den der Nutzer nicht kennen kann: ein Gesetzgebungsverfahren, eine
Parteienlandschaft, einen Konflikt mit Vorgeschichte, eine technische
Architektur.

**Vorgänge, die in den internationalen Medien vorkamen, sind dem Nutzer bekannt**
— ein Regierungswechsel, eine Wahl, ein Krieg, ein Rücktritt. Biete dafür keinen
Hintergrundabschnitt an; das ist eine verschenkte Option und eine unnötige Frage.
Erklärungsbedürftig ist, was es nur in der Landessprache gab: die Vorgeschichte
eines innenpolitischen Streits, die Rolle einer Behörde, ein Detail eines
Gesetzesvorhabens. Ins Glossar darf der bekannte Vorgang trotzdem, sofern er die
Rollen im Video klärt — dort kostet er zwei Zeilen statt eines Abschnitts.

Frag konkret nach dem, was du im Transkript gefunden hast, nicht abstrakt nach
„mehr Details". Gute Optionen sind etwa:

- ein eigener Hintergrundabschnitt zu einem benannten Thema
- eine **Infografik** — Zeitleiste, Akteursgeflecht, Zahlenvergleich
- eine Tabelle statt Fließtext, wenn viele Zahlen fallen
- nichts davon, kompakt bleiben

Bei einem geradlinigen Beitrag ohne Voraussetzungen lässt du die Frage weg und
schreibst durch. Eine Rückfrage, die nur „ausführlich oder kurz" anbietet, ist
Zeitverschwendung.

Für die Frage „wo liegt das" brauchst du hier nichts anzubieten — die Karte aus
Schritt 6b kommt ohnehin ans Ende.

**Infografiken** entstehen als SVG neben dem Dokument (`<slug>-<thema>.svg`) und
werden mit `image::<slug>-<thema>.svg[Beschreibung, width=880]` eingebunden.
Asciidoctor ist auf diesem Rechner nicht installiert, es gibt also keine
Diagrammerweiterung — schreib das SVG selbst und halte es schlicht: keine
externen Ressourcen, `viewBox` gesetzt, Fließtext ab 13 px, Überschriften ab
14 px. Für reine Gegenüberstellungen ist eine AsciiDoc-Tabelle besser als ein
Bild.

**Eine Zeitleiste läuft senkrecht, nicht waagrecht.** Deutsche Beschriftungen
sind zu lang für eine liegende Achse; untereinander bleibt links Platz für das
Datum und rechts eine ganze Zeile für den Text. Bewährt: Achse bei `x=176`,
Ereignisse im Abstand von 92 px, Datum rechtsbündig davor, zwei bis drei
Textzeilen dahinter, und eine Akzentfarbe nur für die Ereignisse, um die es dem
Video geht.

**Beschneide die `viewBox` auf die tatsächliche Inhaltsbreite.** Asciidoctor
skaliert das SVG auf den Satzspiegel, also wird jeder Leerraum rechts eins zu
eins in kleinere Schrift umgerechnet. Im Testfall standen 880 Einheiten
Breite gegen 736 Einheiten Inhalt — nach dem Beschneiden war dieselbe Grafik im
PDF rund zwanzig Prozent größer, ohne eine Zeile Text zu ändern. `pdfwidth=100%`
im Bildmakro hilft dagegen nichts; die Grafik füllte die Breite schon vorher.

**Sieh dir das SVG an, bevor du es einbindest.** Textknoten überlappen sich in
einem von Hand geschriebenen SVG zuverlässig, und im Quelltext siehst du das
nicht. Für die schnelle Schleife beim Bauen macht Edge headless einen Screenshot:

```bash
"/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" --headless \
    --disable-gpu --screenshot=<scratchpad>/svg-check.png --window-size=900,640 \
    "file:///C:/Users/Michael/Downloads/<slug>-<thema>.svg"
```

Dann das PNG mit dem Read-Tool ansehen. Vorher lohnt ein XML-Parse
(`xml.etree.ElementTree`), der fängt fehlende Escapes ab. **Maßgeblich ist aber
das PDF**, nicht der Browser — wie du dir die fertige Seite ansiehst, steht in
Schritt 7.

Was im PDF gut ankommt: Asciidoctor rendert das SVG als Vektor, deutsche Umlaute
und ungarische Akzente inklusive. Was nicht ankommt: Schriften, die im Container
fehlen — gib eine Fallback-Kette an (`font-family="Segoe UI, Helvetica, Arial,
sans-serif"`), dann greift die Ersatzschrift ohne Warnung.

## Schritt 6 — Dokument schreiben

**Schreib den Rumpf mit dem Write-Tool in eine eigene Datei** (`<workdir>/body.adoc`),
beginnend mit der Titelzeile. Dann setzt das Skript Header und Videodaten davor:

```bash
python scripts/adoc_header.py <id>.info.json --body <workdir>/body.adoc \
    --out <slug>.adoc
```

**Bau das Dokument nicht über die Shell zusammen.** Ein Heredoc mit deutschen
Anführungszeichen, Umlauten und ungarischen Akzenten scheitert unter Windows an
Quoting und Codepage — beobachtet als `unexpected EOF while looking for matching`
bei einem sauber zitierten Heredoc. Auch ein Titel mit Umlauten überlebt den Weg
durch `--title` nicht. Deshalb steht der Titel als erste Zeile im Rumpf:

```asciidoc
= Ungarn: Energiekrise und Präsidentenkrise — Gábor Fodor im Interview

[.lead]
…
```

Der Titel ist ein **deutscher** Titel, den du aus dem Inhalt bildest — nicht die
Übersetzung des YouTube-Titels, der oft reißerisch ist oder gar nicht zum Inhalt
passt. Der Originaltitel steht ohnehin unverändert im Datenblock darunter.

Aufbau des Rumpfs:

```asciidoc
= <deutscher Titel>

[.lead]
Ein Absatz. Worum geht es, wer spricht, was ist die Kernaussage. Der Nutzer
muss nach diesem Absatz entscheiden können, ob er weiterliest.

== Wer spricht

Sprecher, Funktion, Sendung, Lautschrift. Bei mehreren Personen eine Liste.

== <erster inhaltlicher Abschnitt> (04:12–09:30)

Wiedergabe des Inhalts …

NOTE: Einordnung: … (dein Beitrag, klar als solcher erkennbar)

== <weiterer Abschnitt> (09:30–14:05)

== Wer und was vorkommt

Kurzglossar der Personen, Parteien, Institutionen und Begriffe, die im Video
als bekannt vorausgesetzt werden.

== Einordnung

Optionaler Schlussabschnitt, wenn eine Gesamtbewertung nötig ist, die sich
keinem einzelnen Abschnitt zuordnen lässt.

<<<

== Karte

Übersichtskarte der erwähnten Orte, siehe Schritt 6b.
```

Regeln für den Rumpf:

- **Der `[.lead]`-Absatz ist genau ein Absatz** und enthält keine Einordnung.
- **Jeder inhaltliche Abschnitt trägt seinen Zeitbereich** in der Überschrift,
  aus den Marken von Schritt 4. Vier bis acht Abschnitte sind für ein
  halbstündiges Interview richtig; zwanzig Abschnitte sind ein Inhaltsverzeichnis,
  keine Zusammenfassung.
- **Zuschreiben statt behaupten.** „Fodor hält das Ministerium für überfordert",
  nicht „Das Ministerium ist überfordert". Das gilt auch dann, wenn du der
  Aussage zustimmst.
- **Das Glossar ist bei fremdsprachigem Material Pflicht**, nicht Kür. Es ist der
  Grund, aus dem der Nutzer den Skill gebaut hat. Jeder Eintrag: Name in der
  Originalschreibweise, Funktion, Partei, ein Satz zur Einordnung, Stand der
  Angabe. Personen ohne Rolle im Video gehören nicht hinein.
- **Umfang**: Der wiedergebende Fließtext landet bei rund einem Drittel der
  Transkriptzeichen. Jede Kernaussage muss vorkommen; Wiederholungen,
  Höflichkeitsfloskeln und Selbstkorrekturen des Sprechers fallen weg.
  Glossar und Einordnung kommen als **feste Kosten** obendrauf, und die
  entscheiden über das Gesamtverhältnis: Gemessen kam ein 5:31-Video auf das
  Doppelte seiner Transkriptlänge, ein 11:56-Video auf 0,8-fach, ein
  37:43-Interview auf 0,7-fach. **Rechne bei kurzen Videos nicht mit einer
  kürzeren Datei als das Transkript** — bei fünf Minuten sind fünf Personen im
  Glossar nun einmal fünf Personen. Kürzen ist trotzdem richtig, nur eben am
  Fließtext.
- **Werbung und Eigenwerbung** werden proportional behandelt. Ein Abo-Aufruf am
  Ende bekommt einen Halbsatz mit Zeitmarke. Nimmt der Werbeteil aber einen
  wesentlichen Anteil der Laufzeit ein — im Testfall gut vierzig Prozent —, ist
  genau das die Antwort auf „was ist das für ein Video", und er bekommt einen
  eigenen Abschnitt plus eine Admonition. Den Anteil zu verschweigen wäre eine
  Fehlinformation über die Quelle.
- **AsciiDoc, nicht Markdown.** Fett ist `*text*`, kursiv `_text_`, Code
  `` `text` ``, Aufzählungen `*` und `.`. `check_adoc.py` in Schritt 7 fängt die
  üblichen Rückfälle ab.

- **Messgrößen als Ziffern**, beiläufige Mengen als Zahlwort. `78 Prozent`,
  `126 Milliarden Dollar`, `138 von 199 Sitzen`, `19. Jahrhundert` — aber „zwei
  Themen", „sechzehn Jahre Fidesz-Regierung". Beides ist im Deutschen zulässig,
  deshalb driftet es innerhalb eines Dokuments: „Achtundsiebzig Prozent" zwei
  Absätze neben „779 Prozent" macht genau die Zahlen unvergleichbar, wegen derer
  der Nutzer liest. `check_adoc.py` meldet Zahlwörter vor Maßeinheiten.

### Fremdwährungen bekommen den Eurobetrag daneben

`6000 Milliarden Forint` ist für einen österreichischen Leser keine Zahl, sondern
eine Zeichenkette. Er kann nicht abschätzen, ob das viel ist, und er kann zwei
Beträge im selben Dokument nicht gegeneinander halten. Deshalb steht hinter jedem
Betrag in einer Fremdwährung der umgerechnete Eurobetrag in Klammern:

```asciidoc
Mit knapp 645 Milliarden Forint (rund 1,8 Milliarden Euro) werde die
Magyar Fejlesztési Bank gestärkt …
```

- **Den Kurs per WebSearch holen, nie aus dem Gedächtnis.** Wechselkurse bewegen
  sich, und eine Umrechnung mit einem zwei Jahre alten Kurs ist derselbe Fehler
  wie ein falsch zugeordnetes Ministeramt: Der Nutzer liest ja gerade deshalb,
  weil er es nicht nachrechnen kann.
- **Den verwendeten Kurs einmal im Dokument nennen**, mit Stand — am besten im
  Glossareintrag zur Währung: „umgerechnet zum heutigen Eurokurs von rund 362
  Forint je Euro, Stand August 2026". Eine Zeile, und jede Umrechnung im Dokument
  ist überprüfbar.
- **Runden, und zwar deutlich.** Der Eurobetrag ist eine Größenordnung, keine
  Messung: `rund 1,7 Milliarden Euro`, nicht `1.675,3 Millionen Euro`. Zwei
  signifikante Stellen genügen, und das `rund` gehört dazu — es sagt dem Leser,
  dass hier ein Tageskurs im Spiel ist.
- **Beim ersten Vorkommen eines Betrags**, wie bei der Lautschrift. Kehrt
  derselbe Betrag später wieder, genügt die Originalwährung. In einer
  Betragstabelle bekommt dagegen jede Zeile ihre Umrechnung, weil der Leser dort
  vergleicht — entweder in derselben Zelle oder in einer eigenen Spalte.
- **Nennt das Video beide Werte selbst, übernimmst du sie so, wie sie fallen**
  („600 Millionen Euro, mehr als 230 Milliarden Forint") und rechnest nichts
  nach. Weicht die Umrechnung des Sprechers aber stark vom aktuellen Kurs ab, ist
  das eine Beobachtung wert — entweder ist die Zahl alt oder sie ist geschönt.
- **Immer der heutige Kurs, und er wird als solcher benannt.** Bei einem alten
  Video oder bei Beträgen aus der Vergangenheit — ein Haushalt von 2019, eine
  Investition, die vor zehn Jahren beschlossen wurde — ist der historische Kurs
  ein anderer, oft deutlich. Trotzdem wird zum heutigen Kurs umgerechnet: Der
  Leser will die Größenordnung in dem Geld einordnen, das er selbst in der Hand
  hat, nicht in dem von damals. Schreib es aber dazu, sonst liest er die Zahl als
  historische Angabe: „umgerechnet zum heutigen Eurokurs von rund 362 Forint je
  Euro". Das Wort *heutiger* ist die ganze Absicherung — es sagt, dass hier nicht
  der Kurs des Aufnahmezeitpunkts steht.
- **Beim Dollar mit Augenmaß.** Ein deutschsprachiger Leser schätzt Dollarbeträge
  grob richtig ein; `12 Dollar Eintritt (rund 11 Euro)` ist Zeilenrauschen. Ab
  Größenordnungen, die niemand mehr im Kopf umrechnet — Millionen und aufwärts —,
  wird auch der Dollar umgerechnet. Für alle übrigen Währungen gilt die Regel
  ausnahmslos.

### Eigennamen stehen im Transkript falsch — jeder einzelne

Das ist die verlässlichste Fehlerquelle des ganzen Durchlaufs und zugleich die,
die dem Nutzer am meisten schadet: Er kennt die Namen ja nicht und kann sie nicht
gegenlesen. Gemessen an den drei Testvideos schrieb Whisper unter anderem:

| im Transkript | richtig |
|---|---|
| Manja Peter | Magyar Péter |
| Tisser, Tisse, Disso | Tisza |
| Súlyog Tamás | Sulyok Tamás |
| Bakandrás | Baka András |
| Romszics Ignász | Romsics Ignác |
| Fülöbb Otton | Fülöp Botond |
| Forsthofer Ágnes | Forsthoffer Ágnes |
| Vidégfejlesztési Minisztérium | Vidékfejlesztési Minisztérium |
| Quinn 3.8 | Qwen 3.8 |

**Schlag jeden Namen nach, bevor er ins Dokument kommt**, und schreib ihn in der
korrekten Originalform. Eine falsche Schreibweise macht die Person für den Nutzer
unauffindbar — das Glossar wird damit wertlos. Wo dir die Korrektur nicht gelingt,
schreib die Transkriptform hin und markiere sie als unsicher, statt eine plausible
Form zu erfinden.

Umgekehrt lohnt es sich, im Glossareintrag die Transkriptform zu erwähnen, wenn
der Nutzer sie beim Nachhören wiedererkennen soll.

### Jeder Name bekommt einmal eine Lautschrift

Der Nutzer spricht die Sprache nicht. Er sieht den Namen geschrieben und hört ihn
im Video, kann beides aber nicht zusammenbringen — `Magyar` klingt nicht wie
gelesen, und `Sulyok` schon gar nicht. Deshalb steht hinter dem Namen **beim
ersten Vorkommen** eine IPA-Umschrift in eckigen Klammern:

```asciidoc
* *Péter Magyar* (ungarisch _Magyar Péter_, [ˈmɒɟɒr ˈpeːtɛr]), Vorsitzender …
```

- **Einmal pro Name, nicht bei jeder Erwähnung.** Wer in „Wer spricht" steht,
  bekommt sie dort; alle übrigen im Glossar. Doppelt ist sie Ballast.
- **Sie gilt der Originalschreibweise**, also der ungarischen Namensfolge
  (Nachname zuerst), nicht der eingedeutschten davor.
- **Auch für Institutionen und Orte**, deren Aussprache sich nicht erraten lässt
  — `Paks` [ˈpɒkʃ], `Tisza` [ˈtisɒ]. Nicht für Namen, die ein deutscher Leser
  ohnehin trifft.
- **Nie raten**, hier so wenig wie sonst. Bist du dir bei einem Laut nicht
  sicher, lass die Umschrift weg. Eine falsche Lautschrift ist schlimmer als
  keine, weil sie sich einprägt.
- **Bei deutschen und englischen Quellen entfällt sie.** Der Nutzer spricht
  beide Sprachen; `Habeck` oder `Farage` liest er ohne Hilfe, und eine Umschrift
  dazu ist nur Zeilenrauschen. Kommt in so einer Quelle ein Name aus einer
  dritten Sprache vor — ein ungarischer Politiker in einem englischen Beitrag —,
  gilt die Regel für diesen Namen wieder.

Sie überlebt den Weg ins PDF nur wegen der Fallback-Schrift aus Schritt 7 — leg
also kein eigenes Theme daneben, ohne dort denselben Fallback einzutragen.

### Die Websuche ist nicht optional, und sie findet etwas

In allen drei Testdurchläufen hat die Prüfung per WebSearch einen sachlichen
Fehler oder eine irreführende Auslassung im Video aufgedeckt — ein falsches
Veröffentlichungsdatum, eine unterschlagene Zahl, die den ganzen Vorwurf trug.
Das ist der eigentliche Mehrwert des Dokuments gegenüber dem bloßen Zusehen.

Prüf mindestens: Datumsangaben, Wahlergebnisse und Prozentzahlen, Ämter und
Parteizugehörigkeiten, Produkt- und Modellnamen samt Erscheinungsdatum. Schreib
den Prüfstand ins Dokument („Per Websuche geprüft, Stand August 2026"), und sag
im Abschlussbericht, was du nicht prüfen konntest.

### Welche Admonition wofür

| | wofür |
|---|---|
| `NOTE` | deine Einordnung, Hintergrund, Kontext, den das Video voraussetzt |
| `TIP` | praktischer Hinweis für den Nutzer, weiterführende Quelle |
| `WARNING` | eine Aussage im Video ist sachlich falsch, stark umstritten oder unbelegt |
| `IMPORTANT` | etwas, das der Nutzer für das Verständnis unbedingt wissen muss |
| `CAUTION` | eine Passage im Transkript ist unsicher, die Wiedergabe also unsicher |

Kurze Einordnungen als einzeilige Form (`NOTE: …`), längere als Block:

```asciidoc
[NOTE]
====
Mehrere Absätze Einordnung.
====
```

Eine Admonition ohne eigenen Beitrag — die nur wiederholt, was im Absatz
darüber steht — gehört gelöscht. Fünf bis fünfzehn über ein halbstündiges
Interview ist ein brauchbarer Rahmen.

## Schritt 6b — Karte der erwähnten Orte

Der Nutzer kennt die Personen nicht — die Orte kennt er genauso wenig. `Paks`,
`Szécsény`, `Kiskunhalas` sind Namen ohne Bild, und keine Glossarzeile ersetzt
den einen Blick, der zeigt, dass das Kernkraftwerk am Fluss liegt, um den es die
ganze Sendung geht. Deshalb schließt das Dokument mit einer Karte.

```bash
python scripts/render_map.py --out <slug>-karte.png \
    --bbox 45.6,15.9,48.8,23.0 \
    --place "Paks (Kernkraftwerk):46.5726,18.8556" \
    --place "Budapest:47.4979,19.0402" \
    --label "Donau:46.95,18.85"
```

Das Skript holt topografische Kacheln von OpenTopoMap — Relief, Flüsse,
Ortsnamen sind darauf schon gezeichnet — und setzt nur die Marker darüber.

- **`--place` für Punkte, `--label` für Flächiges.** Ein Fluss, ein Gebirge,
  eine Region bekommt keinen Marker, weil der auf einen Punkt zeigen würde, den
  es nicht gibt. Die Beschriftung sitzt mittig auf der angegebenen Koordinate,
  also gib eine, an der der Fluss auch verläuft.
- **`--bbox süd,west,nord,ost` für eine Landesübersicht.** Ohne sie rahmt das
  Skript nur die Punkte ein — bei einem einzigen Ort ist das ein Kartenausschnitt
  ohne Land drumherum. Ungarn ist `45.6,15.9,48.8,23.0`.
- **Koordinaten nachschlagen, nicht schätzen.** Dieselbe Regel wie bei den Namen.
  Ein Marker im falschen Landesteil ist eine Fehlinformation, die besonders
  überzeugend aussieht.
- **Die Karte ansehen, bevor sie ins Dokument geht.** Das PNG mit dem Read-Tool
  öffnen: Sitzen die Marker dort, wo die Kacheln den Ort beschriften? Überdeckt
  eine Beschriftung eine andere? Das Skript weicht Kollisionen aus, aber bei
  dicht beieinander liegenden Orten wird es eng.
- **Die Quellenangabe ist Pflicht**, nicht Höflichkeit: OpenTopoMap steht unter
  CC-BY-SA. Sie ist unten ins Bild gebrannt und gehört zusätzlich in die
  Bildunterschrift; das Skript druckt den fertigen Text aus.
- **Ein `<<<` vor den Kartenabschnitt.** Sonst bleibt die Überschrift am Ende
  der Vorseite stehen und das Bild rutscht allein auf die nächste — im Testlauf
  genau so passiert.
- **Unter der Karte zwei bis drei Sätze**, die die Lage in Worte fassen („rund
  100 km südlich von Budapest, direkt an der Donau"). Die Karte ist die
  Antwort auf „wo", der Satz die auf „wie weit".

**Wann die Karte entfällt:** wenn das Video keine Orte hat, die man verorten
muss — eine Diskussion über ein Sprachmodell, ein Grundsatzstreit über ein
Gesetz. Zwei Orte sind ein guter Mindestbestand; für einen einzigen genügt der
Satz im Glossar.

Gemessen am Testdokument: 24 Kacheln bei Zoom 8, Bild 1293 × 858 px, 1,7 MB —
und damit wächst das PDF von 132 KB auf 1,9 MB. Das ist der Preis einer
Rasterkarte und in Ordnung, solange es eine pro Dokument bleibt. Die Kacheln
landen in einem Cache im Temp-Ordner, ein zweiter Lauf mit gleichem Ausschnitt
lädt also nichts nach. Mehr als 48 Kacheln lehnt das Skript ab — beide Dienste
bitten ausdrücklich um maßvolle Nutzung, und ein größerer Ausschnitt gehört
ohnehin auf eine kleinere Zoomstufe.

Ohne Netz oder bei gesperrtem Kachelserver bricht das Skript mit einer klaren
Meldung ab. Dann bleibt das Dokument ohne Karte — sag es im Abschlussbericht,
statt eine leere Bildreferenz stehen zu lassen.

## Schritt 7 — Prüfen und nach PDF wandeln

Zwei Läufe, die verschiedene Dinge wissen. Erst der billige:

```bash
python scripts/check_adoc.py <slug>.adoc
```

Der kennt nur die Regeln *dieses* Skills: Titelzeile, Header-Attribute, den
Datenblock, genau einen `[.lead]`, Überschriftenebenen, geschlossene Blöcke,
Markdown-Syntax, die AsciiDoc wörtlich ausgeben würde, und Messgrößen, die als
Zahlwort statt als Ziffer dastehen. Er braucht keine Sekunde und keinen
Container.

Dann der maßgebliche:

```bash
python scripts/render_adoc.py <slug>.adoc
```

Der lässt **Asciidoctor selbst** ran, in dem Docker-Image, das auch
`convert_adoc.cmd` des Nutzers verwendet — `asciidoctor/docker-asciidoctor` plus
pandoc, gebaut beim ersten Lauf, falls es fehlt. Asciidoctor kennt AsciiDoc, das
Skript nicht; erst dieser Lauf findet ein Bild, das sich nicht auflösen lässt,
eine leer gerenderte Attributreferenz oder ein `include`, das ins Leere zeigt.

**Asciidoctor beendet sich auch mit Warnungen als Erfolg** — der Exitcode allein
belegt gar nichts. Deshalb liest das Skript die Diagnosen aus der
Containerausgabe, meldet `ERROR` und `FAILED` als Fehler und beendet sich dann
mit Exitcode 1. Zur Kontrolle an einem absichtlich kaputten Dokument gemessen:

```
FEHLER : asciidoctor: ERROR: line 10: include file not found: /documents/…
HINWEIS: asciidoctor: WARNING: line 15: unterminated admonition block
HINWEIS: asciidoctor: WARNING: image to embed not found or not readable: …
```

**Das PDF bleibt liegen** — der Nutzer will es. Es landet neben der `.adoc`.
Liegt dort eine `<slug>.yml`, wird sie als PDF-Theme genommen, wie im Skript des
Nutzers. Gemessene Umfänge: 5 Seiten für ein Fünf-Minuten-Video, 10 Seiten für
ein 37-Minuten-Interview.

### Lautschrift und fremde Zeichen im PDF

**Die Standardschrift von asciidoctor-pdf kann kein IPA, und niemand sagt es
dir.** Gemessen an einer Testseite: `[ˈmɒɟɒr ˈpeːtɛr]` kam als Folge leerer
Kästchen heraus, bei Exitcode 0 und null Warnungen. Der einzige Weg, das zu
sehen, ist die Seite anzusehen.

`render_adoc.py` löst das selbst: Es installiert DejaVu ins Image und hängt ein
Theme davor, das die Schrift als Fallback einträgt — die Seite behält ihr
gewohntes Aussehen, nur die fehlenden Glyphen kommen aus DejaVu. Trifft es ein
Image aus der Zeit davor, baut es das einmalig nach (rund eine Minute, am fehlenden
Label `summarize-video.fallback-font` erkannt). Danach rendern IPA-Extensions,
Diakritika und Tonbuchstaben vollständig, ebenso Kyrillisch und Griechisch.

Zwei Dinge, die dabei nicht funktionieren:

- **Das mitgelieferte `default-with-font-fallbacks` reicht nicht.** Es rendert
  `ˈ ː ə ʲ ʰ`, verschluckt aber weiter `ɒ ɟ ɛ ʃ ɡ` — geprüft, nicht vermutet.
- **Ein eigenes `<slug>.yml` verdrängt das Fallback-Theme.** Dann sind die
  Kästchen wieder da; das Skript warnt an dieser Stelle. Wer ein eigenes Theme
  braucht, kopiert die `font:`-Sektion aus `FALLBACK_THEME` in `render_adoc.py`
  hinein.

CJK bleibt außen vor: Im Image liegen zwar Noto-CJK-Schriften, aber als `.ttc`.
Trägt man die als Fallback ein, meldet Asciidoctor wieder nichts, bettet die
Schrift aber kaputt ein — `pdftoppm` bricht dann mit `Missing or empty
DescendantFonts entry` ab, und im PDF steht an der Stelle gar nichts, nicht
einmal ein Kästchen. Chinesische oder japanische Namen also in Umschrift.

### Eine PDF-Seite ansehen

Das Read-Tool kann PDFs hier nicht rendern, poppler ist lokal nicht installiert.
Im Container ist es einen `apk add` entfernt:

```bash
MSYS_NO_PATHCONV=1 docker run --rm -v "C:/Users/Michael/Downloads:/documents" \
    -w //documents asciidoctor-pandoc \
    sh -c "apk add --no-cache poppler-utils >/dev/null 2>&1; \
           pdftoppm -f 5 -l 5 -r 110 -png <slug>.pdf pdfcheck"
```

Danach das PNG mit dem Read-Tool ansehen und wieder löschen. Drei Fallen stecken
in diesem Aufruf: Ohne `MSYS_NO_PATHCONV=1` baut Git Bash den Volume-Pfad um und
Docker meckert über ein ungültiges Arbeitsverzeichnis, `-w` braucht deshalb den
doppelten Schrägstrich, und **`pdftoppm` füllt die Nummer im Dateinamen je nach
Gesamtseitenzahl unterschiedlich auf** — bei zehn Seiten `pdfcheck-05.png`, bei
sechs `pdfcheck-2.png`. Häng ein `&& ls pdfcheck*` an, statt den Namen zu raten.

Lohnt sich vor allem bei Infografiken — ob eine Grafik im Satzspiegel lesbar
ist, sieht man nur dort.

Danach selbst gegenlesen, und zwar auf die zwei Dinge, die kein Skript sieht:

- **Steht in einem Fließtextabsatz eine Bewertung?** Dann gehört sie in eine
  NOTE oder muss dem Sprecher zugeschrieben werden.
- **Stimmen die Zeitmarken?** Stichprobe gegen `transcript.txt`.

## Schritt 8 — Abschlussbericht

Nenn dem Nutzer:

- den Dateinamen von `.adoc`, `.pdf` und `-karte.png` und wo sie liegen, oder
  warum es keine Karte gibt
- Sprache, Laufzeit und Umfang des Transkripts, Seitenzahl des PDF
- was `check_coverage.py` gemeldet hat und wie du es behandelt hast
- welche Passagen unsicher geblieben sind
- welche Angaben im Glossar du per WebSearch geprüft hast und welche nicht

Die Zwischendateien im Scratchpad bleiben liegen, solange die Sitzung läuft — für
eine Rückfrage („was hat er zu X gesagt?") ist `transcript.txt` die Antwortquelle,
nicht das Dokument.
