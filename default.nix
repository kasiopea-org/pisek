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
    ];
  };
in
{
  inherit pisek-exe pisek-env shell;

}
