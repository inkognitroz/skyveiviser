"""Bygg en liten ZIP fra en eksplisitt liste; ingen Git-historikk eller lokaldata."""
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
import hashlib

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    "README.md", "LICENSE", "app.py", "engine.py", "corpus.json", "vm.json", "customers.py",
    "web/index.html", "web/app.js", "web/style.css", "docs/KILDER.md",
)


def build():
    output = ROOT / "downloads" / "Skyveiviser-delingspakke.zip"
    output.parent.mkdir(exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for name in sorted(FILES):
            path = ROOT / name
            if path.is_symlink() or not path.is_file():
                raise ValueError("Manglende eller utrygg fil: " + name)
            content = path.read_bytes()
            if name == "README.md":
                content = content.split("## For den som vil forstå eller tilpasse".encode())[0]
                content += "## Mer informasjon\n\n[Kildeliste](docs/KILDER.md) · [MIT-lisens](LICENSE). Kodeforklaring og tester finnes i prosjektets GitHub-repo. Eksterne kilder og modeller har egne vilkår.\n".encode()
                content = content.replace(
                    b"**[Last ned siste Skyveiviser som ZIP](https://github.com/inkognitroz/skyveiviser/archive/refs/heads/main.zip)**",
                    b"**Last ned ZIP-pakken fra prosjektets GitHub-side**",
                )
                content = content.replace(b"$HOME/Downloads/skyveiviser-main", b"$HOME/Downloads/Skyveiviser-delingspakke/skyveiviser")
                content = content.replace(b"**skyveiviser-main**", b"**Skyveiviser-delingspakke/skyveiviser**")
            info = ZipInfo("Skyveiviser-delingspakke/skyveiviser/" + name, (2026, 9, 26, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)
    checksum = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_name("SHA256SUMS.txt").write_text(checksum + "  " + output.name + "\n")
    print(output.name, checksum)


if __name__ == "__main__":
    build()
