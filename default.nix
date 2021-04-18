{ pkgs ? import <nixpkgs> { }, stdenv ? pkgs.stdenv, lib ? pkgs.lib
, python3 ? pkgs.python3, python3Packages ? pkgs.python3Packages }:
let
  pythonPackage = name:
    python3Packages."${lib.replaceStrings [ "_" ] [ "-" ] name}";
    gitignoreSrc = pkgs.fetchFromGitHub { 
    owner = "hercules-ci";
    repo = "gitignore.nix";
    rev = "211907489e9f198594c0eb0ca9256a1949c9d412";
    sha256 = "sha256:06j7wpvj54khw0z10fjyi31kpafkr6hi1k0di13k1xp8kywvfyx8";
  };
  inherit (import gitignoreSrc { inherit (pkgs) lib; }) gitignoreSource;
in stdenv.mkDerivation {
  name = "bellows2mqtt";
  src = gitignoreSource ./.;
  propagatedBuildInputs = map pythonPackage
    (lib.splitString "\n" (builtins.readFile ./requirements.txt));
  nativeBuildInputs = with python3Packages; [ pylint ];

  installPhase = ''
    cp -R $src $out
  '';
}
