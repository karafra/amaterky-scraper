{ pkgs, ... }:
{
  packages = [
    pkgs.python314
    pkgs.uv
    pkgs.actionlint
  ];
}
