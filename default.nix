{ sources ? import ./nix/sources.nix, nixpkgs ? sources.nixpkgs }:

let
  pkgs = import nixpkgs {};

  pisek-exe = pkgs.poetry2nix.mkPoetryApplication {
    projectDir = ./.;
  };

  pisek-env = pkgs.poetry2nix.mkPoetryEnv {
    projectDir = ./.;
    #editablePackageSources = {
    #  pisek = ./.;
    #};
  };

  shell = pkgs.mkShell {
    buildInputs = with pkgs; [
      niv
      nixpkgs-fmt

      poetry
      pisek-env
      mypy
      python3Packages.black

      # Nainstaluje i GCC/G++ pokud jej uživatel nemá v Nixu.
      # Tohle by možná chtělo za-featureflag-ovat jen pro NixOSaře.
      gcc
    ];
  };
in
{
  inherit pisek-exe pisek-env shell;

}
