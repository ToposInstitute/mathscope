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
			conllu = pkgs.python3Packages.buildPythonPackage rec {
				pname = "conllu";
				version = "6.0.0";
				format = "pyproject";

				nativeBuildInputs = [
					pkgs.python3Packages.setuptools
					pkgs.python3Packages.wheel
				];
				src = pkgs.python3Packages.fetchPypi {
					inherit pname version;
					sha256 = "sha256-vGBy1J0A539EVAOVGRGMBQD6+g0OtQn1N5MIEIT1Cro=";
				};
				doCheck = false;
			};
			pyenv = pkgs.python3.withPackages (ps: with ps; [
				conllu
				django
				django-bootstrap5
				django-widget-tweaks
				gunicorn
				pip
				requests
				tqdm
			]);
		in
		{
			devShells.default = with pkgs; mkShell {
				buildInputs = [
					pyenv
					python3
				];
			};
			packages = {
				default = pkgs.python3Packages.buildPythonApplication {
					pname = "mathoscope";
					version = "0.1.0";
					format = "pyproject";
					src = ./.;
					nativeBuildInputs = [
						pkgs.python3Packages.setuptools
						pkgs.python3Packages.wheel
					];
					propagatedBuildInputs = with pkgs.python3Packages; [
						conllu
						django
						django-bootstrap5
						django-widget-tweaks
						gunicorn
						pip
						requests
						tqdm
					];
					postInstall = ''
						export DJANGO_SETTINGS_MODULE=mathoscope.settings
						export SECRET_KEY=dummy
						python manage.py collectstatic --noinput
						mkdir -p $out/share/static
						cp -r static_root/* $out/share/static/.
					'';
					doCheck=false;
				};
			};
		}
	);
}
