{ pkgs ? import <nixpkgs> { }, stdenv ? pkgs.stdenv, lib ? pkgs.lib
, python3 ? pkgs.python3, python3Packages ? pkgs.python3Packages }:
let
  pythonPackage = name:
    python3Packages."${lib.replaceStrings [ "_" ] [ "-" ] name}";
in stdenv.mkDerivation {
  name = "bellows2mqtt";
  propagatedBuildInputs = map pythonPackage
    (lib.splitString "\n" (builtins.readFile ./requirements.txt));
  nativeBuildInputs = with python3Packages; [ pylint ];
}
