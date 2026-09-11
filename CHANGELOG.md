# Változásnapló

Az FVG Story Editor összes jelentősebb változását ez a fájl tartalmazza.

## [0.2.0] - Következő kiadás

### Hozzáadva

- Önálló Node.js/React webes szerkesztő `.fvgscript` megnyitással, letöltéssel és helyi mentéssel.
- Indításkori választó a desktop és a helyben futó webes felület között.
- WYSIWYG eszköztár félkövér, dőlt, aláhúzott és igazított formázással; a formázás a projektben megmarad.
- Jelenetállapotok: vázlat, írás alatt, javítás és kész.
- Nyomtatási előnézet, projekt-szintű keresés és projektkonzisztencia-ellenőrzés.
- Időbélyeges automatikus mentési előzmények (az utolsó tíz projektmentés visszaállítható).
- Beat Sheet- és kamera-beállítási lista CSV export az exportcsomagban.
- Beat Sheet a történet fordulópontjainak sorrendezhető listájával.
- Jelenethez köthető kamera-beállítási lista képkivágással, mozgással és technikai jegyzetekkel.
- Magyar és angol alkalmazásnyelv-választó.
- Háttérben futó GitHub Release verzióellenőrzés és frissítés-letöltési felajánlás.
- Idővonal, produkciós összesítő, referenciaképek és moodboard-kezelés.
- Fountain- és Final Draft (`.fdx`) import.
- Hunspell-alapú magyar helyesírás-ellenőrzési integráció.
- GitHub Actions CI és automatikus Windows `.exe` kiadásépítés.

## [0.1.0] - 2026-09-11

### Hozzáadva

- Magyar nyelvű, Python/Tkinter alapú forgatókönyvíró felület.
- Jelenet-, karakter-, karakterlap- és jelenetkártya-kezelés.
- Akció-, karakter-, párbeszéd- és zárójeles instrukcióblokkok.
- Verzióelőzmények, visszaállítás és változat-összehasonlítás.
- Keresés és csere, statisztikák, dialóguselemzés, írási cél és fókuszmód.
- Jelenetkártya-tábla, dramaturgiai ív, projekt-navigátor és produkciós bontás.
- Automatikus mentés és induláskori, projekt-specifikus visszaállítás.
- PDF-, Fountain- és CSV-alapú exportcsomag.
- `.fvgscript` natív projektformátum, Windows- és Ubuntu-fájltársítás.
- Windows- és Linux-indítók, virtuális környezet telepítők és Debian-csomagépítő.
- GitHub Actions kiadásfolyamat `.deb` csomagok automatikus előállításához.

### Módosítva

- A felület egységes, sötét, üvegszerű íróstúdió stílust kapott.
- A jelenetek fogd-és-ejtsd módszerrel is átrendezhetők.
