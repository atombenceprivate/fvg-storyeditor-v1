# FVG Story Editor

Magyar nyelvű, Python/Tkinter alapú asztali forgatókönyvíró prototípus. A natív projektformátum a `.fvgscript` (UTF-8-as JSON); minden mentés automatikusan visszaállítható verziót készít (legfeljebb 30 változat).

Az alkalmazás Beat Sheetet és jelenethez kötött kamera-beállítási listát is tárol a projektben. A Beállítások menüben választható a magyar vagy angol felület; induláskor az alkalmazás a GitHub Release-ekből ellenőrzi, elérhető-e újabb verzió, és a megfelelő telepítő kiadási oldalát ajánlja fel.

A v0.3 szerkesztői eszközei közé tartozik a WYSIWYG félkövér/dőlt/aláhúzott és igazító formázás, a jelenetállapotok, a nyomtatási előnézet, a projektszintű keresés és ellenőrzés, valamint a tíz időbélyeges automatikus mentést kezelő helyreállítási nézet. Az exportcsomag Beat Sheet- és shot-list CSV-t is tartalmaz.

## Webes felület

A `web-app` önálló Node.js alkalmazás. A desktop alkalmazás induláskor felajánlja a megnyitását; ehhez Node.js szükséges. A webes szerkesztő a böngészőben, helyben fut, `.fvgscript` fájlokat nyit meg és ment le, valamint helyi böngészőmentést is készít.

Licenc: [MIT](LICENSE). A kiadási változások a [CHANGELOG.md](CHANGELOG.md) fájlban találhatók.

## Funkciók

- jelenet-, karakter- és jelenetkártya-kezelés;
- karakterlapok céllal, konfliktussal, leírással és háttértörténettel;
- akció-, karakter-, párbeszéd- és instrukcióblokkok;
- jelenetek átrendezése, keresés és csere, statisztikák;
- jelenetduplikálás, élő szó-/karakterszámláló és Fountain-export;
- jelenetkártya-tábla, dramaturgiai ív és induláskori autosave-visszaállítás;
- projektvarázsló, navigátor, dialóguselemzés, fókuszmód, jelenetjegyzetek és exportcsomag.
- produkciós bontás és mentett változatok közötti szöveges összehasonlítás.
- jelenetek fogd-és-ejtsd átrendezése és projekt-specifikus autosave-visszaállítás.
- idővonal, produkciós összesítő, Fountain/FDX-import, referenciaképek és Hunspell-integráció.

## Ubuntu/Debian csomag

A telepíthető `.deb` csomag elkészítése:

```bash
./build_deb.sh
```

A csomag a `dist/fvg-story-editor_0.1.0_all.deb` útvonalon jön létre, telepítése pedig: `sudo apt install ./dist/fvg-story-editor_0.1.0_all.deb`.

## Automatikus GitHub kiadás

A `.github/workflows/release.yml` GitHub Actions munkafolyamat minden `v*` címkénél automatikusan elkészíti a `.deb` csomagot és GitHub Release-ként közzéteszi.

Ugyanez a kiadásfolyamat elkészíti a Windowsos önálló `FVGStoryEditor.exe` fájlt is. A `.github/workflows/ci.yml` minden `main` feltöltésnél és pull requestnél futtatja a szintaxis- és egységteszteket.

## Windows NSIS telepítő

Az NSIS telepítő forrása az `installer/fvg-story-editor.nsi`. A `build_nsis.sh` elkészíti a `dist/FVG-Story-Editor-Setup-0.2.0.exe` telepítőt, ha a `makensis` telepítve van. A GitHub kiadásfolyamat automatikusan felépíti és a Release-hez csatolja. A telepítő felhasználói szintre telepít, létrehozza a virtuális környezetet, felveszi a Start menübe, az Asztalra, valamint társítja a `.fvgscript` fájlokat. Python 3 szükséges hozzá; a telepítő ezt az induláskor ellenőrzi.
- automatikus mentés hárompercenként;
- verzióelőzmények és PDF-export;
- induláskori komponensellenőrzés (Tkinter, ideiglenes fájlkezelés, ReportLab).

## Indítás

### Első telepítés virtuális környezettel

Linux/macOS alatt:

```bash
./telepites_venv.sh
```

Ha Ubuntu/Debian alatt a telepítő az `ensurepip` vagy `venv` hiányára panaszkodik, előbb futtasd:

```bash
sudo apt install python3.14-venv
```

Windows alatt kattints duplán a `telepites_venv_windows.bat` fájlra. A telepítő létrehozza a projektmappában a `.venv` könyvtárat, majd telepíti a `requirements.txt` függőségeit. Ezt csak első indításkor, illetve a függőségek változásakor kell lefuttatni.

### Windowsos `.fvgscript` fájltársítás

A virtuális környezet telepítése után futtasd egyszer a `telepites_windows_fajltarsitas.bat` fájlt. Ez kizárólag az aktuális felhasználó Windows-fájltársításait módosítja; ezután a `.fvgscript` fájl dupla kattintással az FVG Story Editorban nyílik meg. A társítás a `eltavolitas_windows_fajltarsitas.bat` futtatásával visszavonható.

Linux/macOS:

```bash
python3 app.py
```

Windows alatt kattints duplán a `FVG Story Editor.bat` fájlra, vagy futtasd ezt a parancsot a projektmappában:

```powershell
py -3 app.py
```

Az alkalmazás jeleneteket és karaktereket kezel, a projektet pedig UTF-8-as JSON-fájlba menti (`.forgatokonyv.json`). A Tkinter a legtöbb Python 3 telepítés része, így nincs külön csomagtelepítés.

A PDF-exporthoz telepítsd a ReportLab csomagot:

```bash
python3 -m pip install -r requirements.txt
```

Vagy Ubuntu rendszeren: `sudo apt install python3-reportlab`.

Windows alatt a függőségek telepítése:

```powershell
py -3 -m pip install -r requirements.txt
```

Ubuntu/Debian rendszeren, ha a `tkinter` modul hiányzik:

```bash
sudo apt install python3-tk
```

## Ubuntu indítófájl

A projektmappában lévő `Forgatokonyviro.desktop` fájlra jobb gombbal kattintva válaszd az **Indítás engedélyezése** lehetőséget, majd nyisd meg. A fájl a fájlkezelőből vagy az Asztalról is használható.

Ha az alkalmazás mégsem indulna, a projektmappában automatikusan létrejövő `inditasi_hiba.log` tartalmazza a pontos hibát. Az indítást a `inditas.sh` végzi; ezt ne helyezd át a projektmappából.

Ha az Ubuntu nem futtatja közvetlenül a mappában lévő `.desktop` fájlt, indítsd el egyszer terminálból a `bash telepites_alkalmazasok_koze.sh` parancsot. Ez felveszi a programot az Alkalmazások menübe, rendszergazdai jogosultság nélkül.

## Következő logikus lépések

- dialógus- és akcióblokkok formázása;
- jelenetek átrendezése;
- PDF vagy Fountain export;
- automatikus mentés és szószám.
