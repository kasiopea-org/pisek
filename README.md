# Písek ⌛

Nástroj na přípravu úloh do programátorských soutěží, primárně pro soutěž
[Kasiopea](https://kasiopea.matfyz.cz/).

## Instalace

Napřed nainstaluj Python 3.6+ a nástroj `pip`.
Pak otevři terminál (příkazovou řádku).
Na Windows můžeš terminál otevřít [takto](https://soubory.info/info/jak-otevrit-prikazovy-radek-windows-10-8-7-atd/).
Na Linuxu a Macu vyhledej program "Terminal".

Napiš následují příkaz do terminálu a zmáčkni Enter:
```
pip3 install --user git+https://github.com/kasiopea-org/pisek
```

Pokud dostaneš na Windows chybovou hlášku typu `'pip3' is not recognized as an internal or external command`,
mohlo by fungovat místo toho napsat
```
py -3 -m pip install --user git+https://github.com/kasiopea-org/pisek`
```
Pokud ani to nepomůže, [napiš nám issue](https://github.com/kasiopea-org/pisek/issues/new).


Pokud už Písek máš a chceš ho aktualizovat, přidej `--upgrade`:
```
pip3 install --user git+https://github.com/kasiopea-org/pisek --upgrade
```

## Použití

Všechny možnosti Písku vám vypíše také příkaz `pisek --help`.
Pokud si s něčím nevíš rady nebo něco nefunguje tak, jak má, dej nám vědět.
Můžeš například [vytvořit issue](https://github.com/kasiopea-org/pisek/issues/new).

Každá úloha má vlastní konfigurační soubor `config`, který určuje parametry úlohy,
jako třeba za jaké podúlohy je kolik bodů, jaká jsou řešení a jak se kontroluje správnost.
Zde je [příklad pro Kasiopeu](https://github.com/kasiopea-org/pisek/blob/master/fixtures/soucet_kasiopea/config)
a [příklad pro CMS (MO-P)](https://github.com/kasiopea-org/pisek/blob/master/fixtures/soucet_cms/config).
Kompletní funkčnost konfiguračního souboru je zdokumenotvaná [zde](https://github.com/kasiopea-org/pisek/blob/master/example-config).

### Testování úloh

Napřed vyplň konfigurační soubor `config`. Pak v terminálu přejdi do složky úlohy a spusť příkaz
```
pisek
```

Tento příkaz zkontroluje mimo jiné, že
- řešení uvedená v `config` a generátor jdou zkompilovat
- `sample.out` se shoduje s výstupem vzorového řešení spuštěného na `sample.in`
- řešení dostanou tolik bodů, kolik je uvedeno v názvu souboru; řešení `solve_4b.cpp` by mělo
    dostat 4 body, `solve.py` 10 bodů (když v názvu není uveden počet bodů)
- pro Kasiopeu: že je generátor deterministický (pro jeden seed generuje totéž), správně načítá hexadecimální seed
- 
### Spouštění jednotlivých programů

Může se hodit, třeba když chceš při vývoji spustit své řešení jen na konkrétním vstupu,
nebo generátorem vygenerovat jeden vstup.
Pokud chceš spustit `solve.cpp` na vstupu `foo.in`, použij
```
pisek run solve.cpp < foo.in
```
Příponu `.cpp` není potřeba psát.

Pokud chceš generátorem `gen.cpp` vygenerovat těžký vstup se seedem `123`, použij
```
pisek run gen 2 123
```

### Rychlé testování jednolivých programů

Pokud chceš jen rychle otestovat pouze své řešení `solve_cool.cpp`, abys ušetřil čas, použij
```
pisek test solution solve_cool
```
Příponu `.cpp` není potřeba psát.

Dokonce si můžeš řešení nechat otestovat na hodně seedech, třeba na 42 následovně
```
pisek test solution solve_cool -n 42
```

Podobně jdou také otestovat malé změny generátoru pomocí
```
pisek test generator
```

### Čištění

Písek při testování vytváří potenciálně hodně dat. Ve složce úlohy můžeš
spustit `pisek clean`, což smaže vygenerovaná data a zkompilovaná řešení.

## Vývoj

Vývoj má pár závislostí navíc. Po naklonování repa je můžeš nainstalovat tak,
že v této složce spustíš:
```
pip3 install -e .[dev]
```

Písek má i testy pro vývojáře, kterými se testuje samotný Písek.
Ty se po instalaci dají spustit takto:
```
./self_tests.sh
```

Naše CI kontroluje i [formátování kódu](https://github.com/psf/black))
a [typy](http://mypy-lang.org/). Abyste odchytili problémy s formátováním
a typy rovnou, nainstalujte si pre-commit hook, který vše zkontroluje
před tím, než něco commitnete:

```
ln -s ../../check_all.sh .git/hooks/pre-commit
```

Po instalaci hooku budou odmítnuty commity, které neprojdou kontrolami.
Pokud je z nějakého důvodu potřeba kontroly odignorovat, můžete použít
`git commit --no-verify`.

Pozor, nezapomeňte, že `check_all.sh` se dívá na soubory ve stavu, v jakém je
máte vy, a ne na to, co budete skutečně commitovat. Pokud tedy něco opravíte a
zapomenete změnu přidat do commitu, může skript seběhnout, ale pořád commitnete
něco, co nefunguje.
