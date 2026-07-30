# Verrauschte Quellen: Artefakte, Gegenmittel, Grenzen

Referenz für Klasse-C-Material — Digitalisate von VHS/S-VHS, Kassetten, Telefonmitschnitten.
Nur lesen, wenn `probe_audio.py` Klasse C meldet oder ein Durchlauf offensichtlichen
Unsinn liefert.

## Zuerst: Ist es wirklich Klasse C?

Der volle Klasse-C-Aufwand lohnt nur bei echtem Rauschen. Zwei Fälle sehen in der Messung
aus wie Rauschen, sind aber keins:

- **Nebengeräusch statt Rauschen.** Eine Aufnahme im Freien — Flussufer, Straße, Menge —
  hat einen hohen, aber *breitbandig harmlosen* Grundpegel. Die Sprache selbst kann dabei
  völlig klar sein. Kennzeichen: `probe_audio.py` findet bei −32 dB keine Sprechpause und
  weist den Störabstand selbst als nicht belastbar aus.
- **Fremdmaterial im Schnitt.** Musik-Intro, Applaus, Jingle. Kennzeichen: Der Störabstand
  ändert sich stark, wenn man mit `--from`/`--to` nur den Sprachteil misst.

In beiden Fällen zuerst einen einfachen Volldurchlauf über die unbearbeitete Spur fahren.
Liest sich das Ergebnis flüssig und in sich stimmig, ist es Klasse A/B — dann über
Wortzeiten weiterarbeiten und diese Referenz beiseitelegen. Entrauschen, was nicht
verrauscht ist, macht das Ergebnis schlechter, nicht besser.

## Die drei typischen Fehlerbilder

### 1. Floskel-Halluzination

In sprecharmen Passagen füllt Whisper die Lücke mit Formeln aus seinen Trainingsdaten:
`Köszönöm, hogy megnéztétek!`, `Untertitel von ...`, `Thanks for watching`,
`Feliratozta: ...`. Diese Sätze wurden **nie gesprochen**.

Erkennungsmerkmal: Sie erscheinen dort, wo im Video nichts oder nur Nebengeräusch ist,
und verschwinden, sobald man dieselbe Stelle aus einer anderen Tonvariante dekodiert.
`transcribe.py` markiert sie mit `<<WARN Floskel-Halluzination>>`.

Gegenmittel: Stelle als unverständlich markieren. Nicht übernehmen, auch nicht
abgeschwächt.

### 2. Wiederholungsschleife

Ein kurzer Ausdruck wird dutzendfach wiederholt (`Ilyen, ilyen, ilyen, ...`). Entsteht,
wenn das Modell im Rauschen keinen Ankerpunkt findet.

Gegenmittel: `repetition_penalty` ist bereits gesetzt. Hilft das nicht, die Stelle mit
`--mode zoom` und Zeitdehnung erneut dekodieren; oft löst sich die Passage dann in
einen echten, kurzen Satz auf.

### 3. Kontextverschleppung

Ein halluziniertes Segment beeinflusst alle folgenden, weil Whisper den bisherigen Text
als Kontext weiterreicht. Symptom: Ab einer bestimmten Stelle driftet das ganze
Transkript thematisch ab.

Gegenmittel: `condition_on_prev_tokens=False` — im Skript für Langform bereits aktiv.
Das kostet etwas Kohärenz, verhindert aber Totalausfälle.

## Warum mehrere Tonvarianten

Jede Filterkette erzeugt eigene Artefakte. Eine Lesart, die in `clean`, `gentle` und
`left` gleich lautet, ist mit hoher Wahrscheinlichkeit echt. Eine Lesart, die nur in
einer Variante auftaucht, ist meist ein Artefakt genau dieser Kette.

Beobachtet: Aggressives Entrauschen (`afftdn=nr=24`) kann eine Passage vollständig
zerstören, die in der unbearbeiteten Spur verständlich ist — und umgekehrt rettet es
Passagen, die im Original im Rauschen untergehen. Deshalb immer beide Richtungen prüfen.

Bei Stereo lohnt der Blick auf die Einzelkanäle: Bei manchen Digitalisaten ist ein Kanal
deutlich sauberer. `probe_audio.py` meldet, ob sich die Kanäle unterscheiden.

## Zeitdehnung

Das wirksamste Einzelmittel für schwierige Stellen. `atempo=0.7` bis `atempo=0.8`
verlangsamt ohne Tonhöhenänderung und löst genuschelte oder überlagerte Wörter oft auf:

```bash
python scripts/transcribe.py <workdir> --mode zoom --variants clean gentle \
    --lang hu --spans "137-150@0.75" "725-745@0.7"
```

Unter 0,7 wird es meist wieder schlechter.

## Fenstergröße

20 Sekunden Fenster bei 15 Sekunden Schrittweite hat sich bewährt: genug Kontext für
sinnvolle Sätze, genug Überlappung, damit kein Wort an einer Fenstergrenze verlorengeht.

Der 30-Sekunden-Chunking-Modus der Transformers-Pipeline (`chunk_length_s`) ist für
verrauschtes Material **ungeeignet** — er erzeugt Dopplungen und verschluckte Passagen an
den Nahtstellen. Stattdessen die native Langform-Dekodierung verwenden (kein
`chunk_length_s` setzen), so wie es `transcribe.py` tut.

## Timing bei Klasse C

Die Zeitmarken der Langform-Dekodierung sind brauchbar, aber gröber als bei sauberem
Material; gegen Ende einer Aufnahme driften sie manchmal. Die Fensterzeiten sind zum
Timing **untauglich** — sie liegen auf dem Schrittraster, nicht auf Sprechgrenzen.

Praktisch: Timings aus dem Langform-JSON nehmen, bei sichtbarem Drift die betroffenen
Cues anhand von Standbildern nachjustieren.

## Wann Schluss ist

Wenn eine Passage nach Volldurchlauf, Fensterlauf über alle Varianten und Zeitdehnung
immer noch in jeder Variante etwas anderes liefert, ist sie nicht rekonstruierbar.

Dann einen Marker setzen und den Zeitbereich im Bericht an den Nutzer nennen. Jemand, der
die Aufnahme und die Beteiligten kennt, kann die Lücke oft in Sekunden schließen — eine
erfundene Formulierung nimmt ihm genau diese Chance, weil sie plausibel aussieht.

Das gilt besonders für Namen, Orte, Zahlen und alles inhaltlich Heikle. Ein falscher Name
in einer Familienaufnahme ist schlimmer als eine sichtbare Lücke.
