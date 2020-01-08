# Písek ⌛

Nástroj na přípravu úloh do programátorských soutěží, primárně pro soutěž
[Kasiopea](https://kasiopea.matfyz.cz/).

## Instalace

Nainstaluj Python 3.6+ a použij nástroj `pip`:
```
pip3 install --user  git+https://github.com/kasiopea-org/pisek
```

## Použití

### Testování úloh

Ve složce úlohy spusť jednoduše
```
pisek
```

Tento příkaz zkontroluje mimo jiné, že
- řešení uvedená v `config` a generátor jdou zkompilovat
- `sample.out` se shoduje s výstupem vzorového řešení spuštěného na `sample.in`
- generátor je deterministický (pro jeden seed generuje totéž), správně načítá hexadecimální seed
- řešení dostanou tolik bodů, kolik je uvedeno v názvu souboru; řešení `solve_4b.cpp` by mělo
    dostat 4 body, `solve.py` 10 bodů (když v názvu není uveden počet bodů)

### Spouštění jednotlivých programů

Může se hodit třeba když chcete při vývoji spustit své řešení jen na konkrétním vstupu,
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

## Testování

Písek má i testy pro vývojáře, kterými se testuje samotný Písek.
Ty se po instalaci dají spustit takto:
```
python3 -m pisek.self_tests
```
