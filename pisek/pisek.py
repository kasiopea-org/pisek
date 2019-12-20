import argparse


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help="podpříkazy", dest="subcommand")
    parser_run = subparsers.add_parser("run", help="spusť řešení a ulož výstup")
    parser_gen = subparsers.add_parser("gen", help="vygeneruj vstupy")
    parser_gen = subparsers.add_parser("None", help="default")
    parser_run.add_argument("command", type=str)
    parser_run.add_argument(
        "--input",
        type=str,
        help="vstupní soubor (default: spustit na všech vstupech v ./data/)",
    )

    parser_gen.add_argument("bar", type=int, help="bar help 1")

    args = parser.parse_args()
    if args.subcommand == "run":
        print("Spoustim reseni: {}".format(args))
    elif args.subcommand == "gen":
        print("Generuji vstupy: {}".format(args))
    elif args.subcommand is None:
        print("Defaultni prikaz: {}".format(args))
    else:
        raise RuntimeError("Neznámý podpříkaz {}".format(args.subcommand))
    print(args)
