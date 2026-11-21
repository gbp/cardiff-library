{
  description = "Python dev shell";

  inputs = {
    nix-devshells.url = "github:gbp/nix-devshells";
  };

  outputs = {
    self,
    nix-devshells,
  }: let
    systems = ["aarch64-darwin" "aarch64-linux" "x86_64-darwin" "x86_64-linux"];
    forAllSystems = nix-devshells.inputs.nixpkgs.lib.genAttrs systems;
  in {
    devShells = forAllSystems (system: let
      pkgs = import nix-devshells.inputs.nixpkgs {
        inherit system;
        overlays = [nix-devshells.overlays.default];
      };
    in {
      default = nix-devshells.lib.mkDevShell {
        inherit pkgs;
        features = [
          (nix-devshells.lib.withPython {inherit pkgs;})
        ];
      };
    });
  };
}
