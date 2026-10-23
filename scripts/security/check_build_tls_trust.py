"""Check the actual OS/pip CA stores and the executing uv security release."""

import argparse
import json
import re
import ssl
import subprocess

REVOKED_ROOTS = {"emSign ECC Root CA - G3", "AAA Certificate Services"}
REQUIRED_ROOTS = {"emSign Root CA - G1", "ISRG Root X1"}


def check_store(context, source):
    names = {
        value
        for certificate in context.get_ca_certs()
        for rdn in certificate["subject"]
        for attribute, value in rdn
        if attribute == "commonName"
    }
    assert not names & REVOKED_ROOTS, f"{source}: compromised CA remains trusted"
    assert REQUIRED_ROOTS <= names, f"{source}: unaffected roots are missing"
    return {"source": source, "trusted_roots": len(names), "compromised_roots": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="+", choices=("system", "pip", "uv"))
    args = parser.parse_args()
    checks = []
    for source in args.sources:
        if source == "system":
            checks.append(check_store(ssl.create_default_context(), "OS OpenSSL store"))
        elif source == "pip":
            import pip
            from pip._vendor import certifi

            assert pip.__version__ == "26.2.2", "unexpected pip bootstrap version"
            checks.append(check_store(
                ssl.create_default_context(cafile=certifi.where()),
                f"pip {pip.__version__} vendored certifi",
            ))
        else:
            version = subprocess.check_output(["uv", "--version"], text=True).strip()
            match = re.match(r"uv (\d+)\.(\d+)\.(\d+)\b", version)
            assert match and tuple(map(int, match.groups())) >= (0, 13, 4), (
                "uv predates the GHSA-hq85-5cpj-mr62 CA fix"
            )
            checks.append({"source": version, "official_ca_fix_release": True})
    print(json.dumps(checks))


if __name__ == "__main__":
    main()
