{
  description = "TreeCheck / 3-30-300 Brasil development environment";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
    in
    {
      devShells = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
          python = pkgs.python312.withPackages (ps: [
            ps.fastapi
            ps.httpx
            ps.pytest
            ps.uvicorn
          ]);
        in
        {
          default = pkgs.mkShell {
            packages = [
              pkgs.cacert
              pkgs.nodejs_22
              pkgs.uv
              python
            ];

            shellHook = ''
              export SSL_CERT_FILE="${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt"
              export REQUESTS_CA_BUNDLE="$SSL_CERT_FILE"
              export PYTHONPATH="$PWD/backend/src:$PYTHONPATH"
              echo "TreeCheck dev shell"
              echo "Backend: python -m uvicorn treecheck_api.main:app --app-dir backend/src --reload"
              echo "Frontend: cd frontend && npm install && npm run dev"
            '';
          };
        });

      checks = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
          python = pkgs.python312.withPackages (ps: [
            ps.fastapi
            ps.httpx
            ps.pytest
            ps.uvicorn
          ]);
        in
        {
          backend-tests = pkgs.runCommand "treecheck-backend-tests"
            {
              nativeBuildInputs = [ python ];
              src = self;
            }
            ''
              cp -R "$src" repo
              cd repo
              export PYTHONPATH="$PWD/backend/src"
              pytest backend/tests
              touch "$out"
            '';
        });
    };
}
