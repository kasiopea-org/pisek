# pisek

Nástroj na přípravu úloh do programátorských soutěží

## Instalace

Nainstalujte Python 3.6+ a použijte nástroj _pip_:
```
pip3 install --user  git+https://github.com/kasiopea-org/pisek
```

## Použití 

### Otestovat úlohu
Ve složce úlohy spusť jednoduše
```
pisek
```

### Spouštění jednotlivých řešení
Může se hodit třeba když chcete při vývoji spustit své řešení jen na konkrétním vstupu.
Pokud chceš spustit `solve.cpp` na vstupu `foo.in`, použij
```
pisek run solve.cpp < foo.in
```
Příponu `.cpp` není potřeba psát.

## Testování

Písek má i testy pro vývojáře, kterými se testuje samotný Písek.
Ty se po instalaci dají spustit takto:
```
python3 -m pisek.self_tests
```
