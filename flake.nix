{
	description = "Reproducible Python environment for Mathoscope.";

	inputs = {
		nixkpgs.url = "github:NixOS/nixpkgs/nixos-unstable";
		flake-utils.url = "github:numtide/flake-utils";
	};

	outputs = { self, nixpkgs, flake-utils, ... }:
	flake-utils.lib.eachDefaultSystem (system:
		let
			pkgs = import nixpkgs {
				inherit system;
			};
			pyenv = pkgs.python3.withPackages (ps: with ps; [
				pip
				django
			]);
		in
		{
			devShells.default = with pkgs; mkShell {
				buildInputs = [
					pyenv
					python3
				]
			};
		}
	);
}
