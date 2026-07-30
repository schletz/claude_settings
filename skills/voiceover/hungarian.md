# Ungarische Wörter in der deutschen Tonspur

Wortliste für den Übersetzungsschritt: ungarische Eigennamen, Parteien, Kürzel
und Orte, die in der deutschen Übersetzung stehen bleiben, mit der Schreibweise,
in der sie in den **Cue** gehören.

**Zwei Skills lesen diese Datei** — `voiceover` in Schritt 7 und `podcast` in
Schritt 8. Sie hat deshalb keine Kopie: Dieselbe Person soll in der Videofassung
und in der Hörfassung gleich klingen, und zwei gepflegte Listen driften
auseinander. Was du hier ergänzt, gilt für beide.

## Grundregeln

**Die Cue-Schreibung ist keine Schreibung, sondern eine Aussprache-Anweisung.**
Sie wird nie gelesen — der Hörer bekommt nur Ton. Dass hier `Fidess` steht und
nicht `Fidesz`, ändert nichts an dem Namen, den der Hörer hört; es stellt ihn
erst her. Für Untertitel gilt das Gegenteil, dort steht die Originalschreibweise.

**Die Umschrift wird beim ersten Vorkommen gebildet und danach nicht mehr
angefasst.** Nicht gegen die Synthese optimieren, nicht zurücklesen, nicht
Varianten vergleichen. Beide Modelle der Kette sind stochastisch: Derselbe Cue
ergibt bei jedem Lauf eine andere Welle, ein Vergleich misst also den Zufall.
Eine feste, regelmäßig gebildete Schreibweise ist einer optimierten überlegen,
weil sie im ganzen Video gleich klingt.

**Steht ein Wort nicht in der Liste, bilde es nach den Regeln unten und trag es
ein.** Die Liste wächst über die Videos hinweg; ein Wort, das einmal drinsteht,
wird nicht erneut hergeleitet.

**Ein sehr kurzes Wort braucht manchmal einen Buchstaben mehr, als die Regeln
hergeben.** Bei zwei oder drei Buchstaben ist die deutsche Lesart nicht eindeutig,
und das Modell fällt dann auf die englische zurück: `Mi Hazánk` als `Mi Hasank`
geschrieben kam als „May-hazank" heraus. `Mie` nagelt den langen Vokal fest, und
genau das ist der Zweck der Umschrift. Das ist **kein** Verstoß gegen die Regel
darüber — dort geht es darum, Varianten gegen die Synthese durchzuprobieren. Hier
wird die deutsche Lesart eindeutig gemacht, was jedes Mal dasselbe Ergebnis liefert.
Betroffen sind vor allem einzeln stehende Silben und Buchstabenkürzel.

**Es gibt keine Lautschrift und keine Steuersyntax.** F5-TTS schlägt jeden
Buchstaben einzeln im Vokabular nach. IPA-Zeichen werden als seltene
Schriftzeichen geraten (`ʃuːlə` → „Toll"), Klammerhinweise werden mitgesprochen,
SSML-Tags buchstäblich vorgelesen und zerlegen zusätzlich den Satz.

## Umschriftregeln

Ungarisch ist lautlich regelmäßig — anders als das Deutsche entspricht jedem
Buchstaben genau ein Laut. Die Umschrift ist deshalb mechanisch.

### Konsonanten

| ungarisch | Cue | Laut | Beispiel |
|---|---|---|---|
| `s` | `sch` | [ʃ] | Sólyom → Schojom |
| `sz` | `ss` | [s] | Szabó → Ssabo |
| `zs` | `sch` | [ʒ] | Zsolt → Scholt |
| `cs` | `tsch` | [tʃ] | Kocsis → Kotschisch |
| `c` | `tz` | [ts] | Ferenc →Ferentz |
| `cz` | `tz` | [ts] | Toroczkai → Torotzkai |
| `z` | `s` | [z] | Lázár → Lasar |
| `gy` | `dj` | [ɟ] | Magyar → Madjar |
| `ny` | `nj` | [ɲ] | Károly → Karolj |
| `ty` | `tj` | [c] | Batthyány → Battjanj |
| `ly` | `j` | [j] | Király → Kiraj |
| `v` | `w` | [v] | Vitézi → Witesi |
| `th` | `t` | [t] | Tóth → Toht |

Doppelkonsonanten bleiben doppelt (`Szijjártó` → `Ssijjarto`). Alles Übrige —
`k p t b d g m n l f h j r` — bleibt unverändert.

### Vokale

**Die Akzente entfallen.** Im Ungarischen sind `á é í ó ú` reine Längenzeichen,
und deutsche Vokale in offener Silbe sind ohnehin lang. `ő ű` werden zu `ö ü`,
das hält die Vokalqualität.

| ungarisch | Cue | Beispiel |
|---|---|---|
| `á í ó ú` | `a i o u` | Novák → Nowak, Dúró → Duro |
| `é` | `e` | Vitézi → Witesi |
| `ö ő` | `ö` | Gyöngyösi → Djöndjöschi |
| `ü ű` | `ü` | Szűcs → Sütsch |
| `a` | `a` | Magyar → Madjar |

Ein **Dehnungs-h** nur dort, wo die deutsche Lesart den Vokal sonst kürzen würde,
weil die Silbe geschlossen ist: `Kövér` → `Köwehr`, `Tóth` → `Toht`.

Das ungarische `a` ist [ɒ], ein gerundetes a, das im Standarddeutschen fehlt und
nur bairisch-österreichisch vorkommt. Es ist nicht erreichbar; `a` ist die
nächstbeste Näherung, bei einsilbigen Wörtern klingt `o` gelegentlich näher.

### Zwei Regeln, die den Satz betreffen

**Vorname nur bei der ersten Nennung.** Danach der Nachname allein, mit einem
deutschen Wort davor („über Solyom", „Herrn Schujok"). Zwei fremde Namen
hintereinander verschmelzen zu einem Fantasiewort.

**Buchstabenkürzel werden ausgeschrieben**, wenn sie allein oder in einer kurzen
Vorstellung stehen. `V` heißt dabei `Fau`, nicht `Vau`.

## Wortliste

### Parteien, Medien, Institutionen

| Original | Cue |
|---|---|
| Fidesz | `Fidess` |
| Tisza (Partei) | `Tissa` |
| Mi Hazánk | `Mie Hasank` |
| Jobbik | `Jobbik` |
| KDNP | `Ka De En Peh` |
| MSZP | `Em Es Zet Peh` |
| SZDSZ | `Es Zet De Es` |
| DK | `De Kah` |
| Hír TV | `Hir Teh Feh` |
| HVG | `Ha Fau Geh` |
| MCC | `Em Ce Ce` |
| Mathias Corvinus Alapítvány | `Mathias-Corvinus-Stiftung` — übersetzen |
| Kék Bolygó Klímavédelmi Alapítvány | `Klimaschutzstiftung Blauer Planet` — übersetzen |
| Batthyány Lajos Alapítvány | `Lajosch-Battjanj-Stiftung`, danach `Battjanj-Stiftung` |
| Alapjogokért Központ | `Zentrum für Grundrechte` — übersetzen |
| Danube Institute | `Denjub Institjut` — englischer Name, die Umschrift nagelt die englische Lesart fest |
| Budapest Műhely | `Budapest Mühelj` |
| Richter (Gedeon Richter) | `Richter` |
| MVM | `Em Fau Em` |
| Telex | `Telex` |
| Magyar Nemzet | `Madjar Nemset` |
| 444 | `vierhundertvierundvierzig` |
| Origo | `Origo` |
| Index | `Index` |
| Blikk | `Blick` |
| Inforádió | `Inforadio` |
| Medián | `Median` |
| Századvég | `Ssasadweg` |
| Duna House | `Duna Haus` |
| Duna Aszfalt | `Duna Asfalt` |
| Exim (Exim Bank) | `Exim` |
| MFB | `Em Ef Beh` |
| Gondosóra | `Gondoschora` |
| Kréta (Schulsystem) | `Kreta` — ein deutsches Wort davor („das Verwaltungssystem Kreta"), sonst hört der Zuhörer die Insel |
| Neptun (Hochschulsystem) | `Neptun` |
| Poszeidón (Aktensystem) | `Posseidon` |
| Vodafone | `Wodafone` |
| KEKVA | `Vermögensverwaltungsstiftung` — übersetzen, das Kürzel sagt im Deutschen nichts |
| Nemzeti Vagyonvisszaszerzési és Vagyonvédelmi Hivatal | `Nationales Amt für Vermögensrückgewinnung und Vermögensschutz` — übersetzen |
| Nemzeti Nyomozó Iroda | `Nationales Ermittlungsbüro` — übersetzen |
| ÁVH (Staatsschutz der Rákosi-Zeit) | `Ah Fau Ha` — ein deutsches Wort davor („die Staatssicherheit Ah Fau Ha"), das Kürzel allein sagt im Deutschen nichts |
| janicsár | `Janitschar` — übersetzen |
| 4iG | `Fier I Geh` |
| Otthon Start | `Otthon Start` |
| Paks 2 | `Paks zwei` |
| NER | `Ner` |
| Partizán | `Partisan` |
| OTP Bank Liga | `O Teh Peh Bank Liga` |
| OTP | `O Teh Peh` |
| MOL | `Mol` |
| Antenna Hungária | `Antenna Hungaria` |
| Világgazdaság | `die Wirtschaftszeitung` — übersetzen, die Umschrift ist unaussprechbar |
| BRFK | `die Budapester Polizei` — übersetzen |
| trafipax | `Blitzer` — übersetzen |
| Bécsig Mentem (YouTube-Kanal) | `Behtschig mentem` |
| bécsigmentem.at | `Behtschig mentem punkt a teh` |
| Bayer Construct | `Bayer Konstrukt` |
| ZVK Development | `Zet Fau Ka Development` |
| MOHU | `Mohu` — ein deutsches Wort davor („das Entsorgungsunternehmen Mohu“) |
| Magyar Fejlesztési Bank | `Ungarische Entwicklungsbank` — übersetzen |
| Nemzeti Reorganizációs Nonprofit Kft | `Nationale Reorganisations-Gesellschaft` — übersetzen |
| Zeneakadémia | `Musikakademie` — übersetzen |

### Personen

| Original | Cue |
|---|---|
| Magyar | `Madjar` |
| Orbán | `Orban` |
| Nagy | `Nadj` |
| Gyurcsány | `Djurtschanj` |
| Karácsony | `Karatschonj` |
| Kocsis | `Kotschisch` |
| Semjén | `Schemjen` |
| Szijjártó | `Ssijjarto` |
| Gulyás | `Gujasch` |
| Sulyok | `Schujok` |
| Toroczkai | `Torotzkai` |
| Hadházy | `Hadhasi` |
| Kövér | `Köwehr` |
| Navracsics | `Nawratschitsch` |
| Gyöngyösi | `Djöndjöschi` |
| Lázár | `Lasar` |
| Novák | `Nowak` |
| Dobrev | `Dobrew` |
| Szabó | `Ssabo` |
| Vitézi | `Witesi` |
| Dúró | `Duro` |
| Rogán | `Rogan` |
| Pintér | `Pinter` |
| Varga | `Warga` |
| Vona | `Wona` |
| Áder | `Ader` |
| Batthyány | `Battjanj` |
| Jakab | `Jakab` |
| Márki-Zay | `Marki-Sai` |
| Kelemen | `Kelemen` |
| Gajdos | `Gajdosch` |
| Kapitány | `Kapitanj` |
| Gavra | `Gawra` |
| Király | `Kiraj` |
| Tóth | `Toht` |
| Polgár | `Polgar` |
| Sólyom | `Schojom` |
| Mádl | `Madl` |
| Göncz | `Göntz` |
| Ruszin-Szendi | `Russin-Sendi` |
| Szűcs | `Sütsch` |
| Kerényi | `Kerenji` |
| Lőrinc | `Lörintz` |
| Torockai | `Torotzkai` |
| Rétvári | `Retwari` |
| Bóka | `Boka` |
| Panyi | `Panji` |
| Szentkirályi | `Ssentkiraji` |
| Havasi | `Hawaschi` |
| Hack | `Hack` |
| Lezsák | `Leschak` |
| Szegő | `Ssegö` |
| Farkas | `Farkasch` |
| Kis | `Kisch` |
| Fülöp | `Fülöp` |
| Vidnyánszky | `Widnjanski` |
| Mészáros | `Messarosch` |
| Szíj | `Ssij` |
| Tiborcz | `Tibortz` |
| Hallerné Nagy | `Hallerne Nadj` |
| Csiky | `Tschiki` |
| Kutai | `Kutai` |
| Gacsály | `Gatschaj` |
| Kádár | `Kadar` |
| Forsthofer | `Forsthofer` |
| Gálfalviné Toth | `Galfalwine Toht` |
| Hortay | `Hortai` |
| Lendvai | `Lendwai` |
| Németh | `Nemet` |
| Bohár | `Bohar` |
| Aranyosi | `Aranjoschi` |
| Felméri | `Felmeri` |
| Gecse | `Getsche` |
| Szepesfalvi | `Ssepeschfalwi` |
| Kozma | `Kosma` |
| Kós | `Kosch` |
| Ligeti | `Ligeti` |
| Unger | `Unger` |
| Barna | `Barna` |
| Tasnádi | `Taschnadi` |
| Tomori | `Tomori` |
| Szapolyai | `Ssapojai` |
| Szulejmán (Sultan) | `Suleiman` |
| Ady | `Adi` |
| Hunyadi | `Hunjadi` |
| II. Lajos | `Ludwig der Zweite` — übersetzen, im Deutschen etabliert |
| Nagy Lajos | `Ludwig der Große` — übersetzen |
| Mátyás király | `König Matthias` — übersetzen |
| Szent István | `der heilige Stephan` — übersetzen |
| Árpádok | `Arpaden` — übersetzen |
| Anzsuk | `Anjous` — übersetzen |
| Baka | `Baka` |
| Schiff (Sif András) | `Schiff` — der Pianist ist im Deutschen als András Schiff bekannt |

### Vornamen

Sie stehen fast immer neben einem Nachnamen und werden deshalb genauso mechanisch
gebildet. Im Deutschen kommt der Vorname zuerst — die ungarische Reihenfolge
`Magyar Péter` wird zu `Peter Madjar`, sonst hört der Zuhörer einen Doppelnachnamen.

| Original | Cue |
|---|---|
| László | `Laslo` |
| József | `Joschef` |
| Sándor | `Schandor` |
| János | `Janosch` |
| Péter | `Peter` |
| Viktor | `Wiktor` |
| Ákos | `Akosch` |
| Ágnes | `Agnesch` |
| Anikó | `Aniko` |
| Bence | `Bentze` |
| Miklós | `Miklosch` |
| Ciprián | `Tziprian` |
| Gergely | `Gergelj` |
| Lajos | `Lajosch` |
| Dávid | `Dawid` |
| Tamás | `Tamasch` |
| Pál | `Pal` |
| Bertalan | `Bertalan` |
| Balázs | `Balasch` |
| Tibor | `Tibor` |
| Attila | `Attila` |
| Alexandra | `Alexandra` |
| Erzsébet | `Erschebet` |
| István | `Ischtwan` |
| Zsolt | `Scholt` |
| Olivér | `Oliwer` |
| Ildikó | `Ildiko` |
| Melinda | `Melinda` |
| Flórián | `Florian` |
| Dániel | `Daniel` |
| Hubert | `Hubert` |
| Anna | `Anna` |
| Katalin | `Katalin` |
| Endre | `Endre` |
| Márton | `Marton` |
| Róza | `Rosa` |
| András | `Andrasch` |

### Orte

| Original | Cue |
|---|---|
| Paks | `Paks` |
| Budapest | `Budapest` |
| Debrecen | `Debretzen` |
| Szeged | `Ssegged` |
| Győr | `Djör` |
| Pécs | `Petsch` |
| Miskolc | `Mischkoltz` |
| Székesfehérvár | `Sekeschfeherwar` |
| Sándor-palota | `Schandor-Palast` |
| Duna | `Donau` — übersetzen |
| Tisza (Fluss) | `Theiß` — übersetzen, **nicht** mit der Partei verwechseln |
| Balaton | `Balaton` |
| Sopron | `Schopron` |
| Kaposvár | `Kaposchwar` |
| Szolnok | `Ssolnok` |
| Mohács | `Mohatsch` |
| Zugló | `Suglo` |
| Észak-Macedónia | `Nordmazedonien` — übersetzen |
| Dunaszentbenedek | `Dunaschentbenedek` |
| Dunakiliti | `Dunakiliti` |
| Tass | `Tasch` |
| Ráckevei-Soroksári Duna-ág | `Ratzkewei-Schorokschari-Donauarm` |
| Csernavoda (rumän. Cernavodă) | `Tschernawoda` |
| Zala | `Sala` |
| Zalaegerszeg | `Salaegerseg` |
| Nyíregyháza | `Njiredjhasa` |
| Eger | `Eger` |
| Terézváros | `Tereswarosch` |
| Ferencváros | `Ferentzwarosch` |
| Rákóczi tér | `Rakotzi-Platz` |
| Blaha Lujza tér | `Blaha-Lujsa-Platz` |
| Nyugati tér | `Njugati-Platz` |
| Bacsó Béla utca | `Batscho-Bela-Straße` |
| Kincsem Park | `Kintschem Park` |
| Göd | `Göhd` — das Dehnungs-h ist noetig, ohne es kam die Silbe als „Goethe" zurueck |
| Bábolna | `Babolna` |
| Ceuta | `Seuta` |
| Bosnyák tér | `Boschnjak-Platz` |
| Bicske | `Bitschke` |
| Baranya (Komitat) | `Baranja` |
| Buda | `Buda` |
| Muhi | `Muhi` |
| Világos | `Wilagosch` |
| Erdély | `Siebenbürgen` — übersetzen |
| Felvidék | `Oberungarn` — übersetzen |
| Vajdaság | `Wojwodina` — übersetzen |
| Kárpátalja | `Transkarpatien` — übersetzen |
| Muraköz | `Murinsel` — übersetzen |
| busójárás | `Buschojarasch` — ein deutsches Wort davor („der Umzug Buschojarasch") |
| sokác | `Schokatzen` — übersetzen, deutscher Volksgruppenname |
| bunyevác | `Bunjewatzen` — übersetzen, deutscher Volksgruppenname |
| sváb | `Schwaben` — übersetzen |
| tatárjárás | `Mongolensturm` — übersetzen |

## Namenskollisionen

Einige Umschriften fallen mit deutschen Wörtern zusammen. Stell dort ein
deutsches Wort voran, damit der Hörer die Grenze erkennt — die Schreibweise
selbst zu ändern hilft nicht, weil sie lautlich richtig ist.

| Cue | kollidiert mit | Abhilfe |
|---|---|---|
| `Toht` | tot | „Herrn Toht", „der Jurist Toht" |
| `Ungar` (Ungár) | Ungar | „der Abgeordnete Ungar" |
| `Warga` (Varga) | Warge | „Frau Warga" |
