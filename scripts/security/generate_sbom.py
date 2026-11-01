#!/usr/bin/env python3
"""
PRAXIS InterviewOS — Software Bill of Materials (SBOM) Generator
Generates a consolidated CycloneDX / SPDX compatible JSON inventory of all dependencies.
"""
import json

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def collect_python_dependencies():
    packages = []
    pyproject_path = ROOT / "backend" / "pyproject.toml"
    if pyproject_path.exists():
        content = pyproject_path.read_text(encoding="utf-8")
        in_deps = False
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("dependencies = ["):
                in_deps = True
                continue
            if in_deps:
                if line.endswith("]"):
                    break
                dep = line.strip('", ').strip("'")
                if dep:
                    packages.append({
                        "ecosystem": "PyPI",
                        "name": dep.split(">=")[0].split("==")[0].split("<")[0].split("~=")[0].strip(),
                        "spec": dep,
                    })
    return packages


def collect_js_dependencies():
    packages = []
    for pkg_json_path in [
        ROOT / "package.json",
        ROOT / "apps" / "web" / "package.json",
        ROOT / "apps" / "desktop" / "package.json",
        ROOT / "packages" / "ui" / "package.json",
        ROOT / "packages" / "types" / "package.json",
    ]:
        if pkg_json_path.exists():
            try:
                data = json.loads(pkg_json_path.read_text(encoding="utf-8"))
                for section in ["dependencies", "devDependencies"]:
                    deps = data.get(section, {})
                    for name, version in deps.items():
                        packages.append({
                            "ecosystem": "npm",
                            "name": name,
                            "version": str(version),
                            "scope": section,
                            "manifest": str(pkg_json_path.relative_to(ROOT)),
                        })
            except Exception as e:
                print(f"Warning parsing {pkg_json_path}: {e}", file=sys.stderr)
    return packages


def main():
    print("Generating Software Bill of Materials (SBOM)...")
    py_deps = collect_python_dependencies()
    js_deps = collect_js_dependencies()

    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:praxis-sbom-{int(datetime.now().timestamp())}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "component": {
                "name": "praxis-interviewOS",
                "version": "1.0.0",
                "type": "application",
            },
            "summary": {
                "python_dependencies_count": len(py_deps),
                "javascript_dependencies_count": len(js_deps),
                "total_components": len(py_deps) + len(js_deps),
            }
        },
        "components": py_deps + js_deps,
    }

    out_path = ROOT / "docs" / "security" / "sbom.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(sbom, indent=2), encoding="utf-8")

    print(f"[OK] SBOM successfully generated with {len(py_deps)} Python and {len(js_deps)} npm components.")
    print(f"Saved to: {out_path}")


if __name__ == "__main__":
    main()
