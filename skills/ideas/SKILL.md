---
name: ideas
description: Lädt aktuelle Schlagzeilen aus Tech- und österreichischen RSS-Newsfeeds (golem.de, derStandard Web, APA-OTS, Die Presse) ins Kontextfenster, damit Themenvorschläge einen echten Gegenwartsbezug haben statt der üblichen vorhersehbaren Beispiele. Nutze diesen Skill immer, wenn der Nutzer ein Thema, eine Idee, ein Szenario oder einen Kontext für eine Prüfungsangabe, Schularbeit, Übungsaufgabe, Musterdatenbank, Beispieldaten, ein Projekt, eine Fallstudie oder ein Unterrichtsbeispiel sucht — auch wenn er nur "mit aktuellem Bezug", "was Aktuelles", "nicht schon wieder Bibliothek/Webshop" oder "gib mir Ideen" sagt, oder auf Englisch "topic ideas", "current events", "fresh scenario". Auch nutzen, wenn der Nutzer einfach wissen will, was gerade in den Tech- oder Österreich-News los ist.
---

# Ideas aus aktuellen News

Von sich aus greift ein LLM bei Themenvorschlägen zu den immer gleichen Klassikern
(Bibliothek, Webshop, Schulverwaltung, Fuhrpark). Aktuelle Schlagzeilen liefern
Themen, die niemand erwartet und die Schüler oder Leser als relevant erleben.
Dieser Skill holt sie dir als Rohmaterial in den Kontext.

## Feeds

| Feed | Schwerpunkt | URL |
|---|---|---|
| golem.de | Tech, IT, Netzpolitik | `https://rss.golem.de/rss.php?feed=RSS2.0` |
| derStandard Web | Tech, Netz, Wissenschaft (AT-Sicht) | `https://www.derstandard.at/rss/web` |
| APA-OTS | Presseaussendungen aus Österreich: Ministerien, Firmen, Vereine, Gemeinden | `https://www.ots.at/rss/index` |
| Die Presse | Österreich allgemein: Politik, Wirtschaft, Chronik | `https://www.diepresse.com/rss` |

Wähle nach der Anfrage: Für Informatik-Themen reichen oft golem und derStandard,
für Wirtschafts- oder Alltagsszenarien eignen sich OTS und Presse. Ist nichts
eingegrenzt, lade alle vier — die Mischung erzeugt die überraschendsten Ideen.
Nennt der Nutzer eigene Feed-URLs, nimm stattdessen diese.

## Feeds laden

Pro Feed ein Aufruf, die Aufrufe sind unabhängig und können parallel laufen:

```
python <skill-dir>/scripts/get_ideas.py https://www.derstandard.at/rss/web
```

Das Skript gibt den Feed als Markdown auf der Konsole aus (`#` Feedtitel, `##`
Schlagzeile, darunter der Teaser; Werbung ist herausgefiltert) und endet mit 0,
bei Fehlern mit 1 und einer Meldung auf stderr. Ein einzelner Feed hat 4–20 KB.
Ruf die Feeds deshalb einzeln auf, statt sie zu einer Ausgabe zusammenzufassen:
Tool-Ausgaben über etwa 30.000 Zeichen werden abgeschnitten.

Fällt ein Feed aus, arbeite mit den übrigen weiter und erwähne es kurz.

## Ideen ableiten

Die Schlagzeilen sind Inspiration, kein Inhalt. Daraus folgt:

- **Auf die Aufgabe zuschneiden.** Prüf jede Schlagzeile darauf, ob sie das trägt,
  was der Nutzer braucht. Eine Musterdatenbank braucht mehrere Entitäten mit
  Beziehungen (z. B. "Sirenen-Probealarm" → Sirenen, Standorte, Gemeinden,
  Testläufe, Ausfälle); eine Programmieraufgabe braucht einen klaren Algorithmus
  oder Ablauf; ein Textbeispiel braucht einen Konflikt oder eine Fragestellung.
- **Das Unerwartete bevorzugen.** Die Stärke der News ist ihre Spezifität. Nimm
  lieber die Nischenmeldung über einen Wiener Spieleentwickler als die x-te
  KI-Schlagzeile, die ohnehin jeder als Thema wählen würde.
- **Mit Quelle vorschlagen.** Präsentiere 3–5 Ideen, jeweils mit der
  Schlagzeile als Ursprung und einem Satz, wie daraus die konkrete Aufgabe wird.
  So kann der Nutzer schnell auswählen, und du verankerst die Idee in der Realität.
- **Keine Fakten über die Meldung hinaus erfinden.** Du kennst nur Titel und
  Teaser. Wenn eine Aufgabe reale Details braucht, kennzeichne Erfundenes als
  fiktiv oder schlage vor, den Artikel nachzulesen.
- **Für den Einsatz passend wählen.** Prüfungen und Unterricht vertragen keine
  Themen, die Betroffene im Raum treffen können (Todesfälle, Gewaltverbrechen,
  Krieg) oder die parteipolitisch Stellung beziehen. Solche Meldungen nur
  verwenden, wenn der Nutzer das ausdrücklich will.
