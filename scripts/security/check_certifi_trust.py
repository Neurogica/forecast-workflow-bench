"""外向き HTTPS の信頼ストアを実際に OpenSSL へ読み込んで検証する。"""

import ssl

import certifi


def test_漏えいした中間CAのルートを信頼せず影響のないルートは維持する():
    # requests / httpx が既定で使う certifi の実配布物を検証する。
    # GHSA-6q48-6c7w-9gw2: 2026.10.18 は全 emSign を削除したが、
    # 2026.10.19 は無関係なルートを復元しているため、そこまで確認する。
    context = ssl.create_default_context(cafile=certifi.where())
    common_names = {
        value
        for certificate in context.get_ca_certs()
        for rdn in certificate["subject"]
        for attribute, value in rdn
        if attribute == "commonName"
    }

    assert "emSign ECC Root CA - G3" not in common_names
    assert "emSign Root CA - G1" in common_names
    assert "ISRG Root X1" in common_names

if __name__ == "__main__":
    test_漏えいした中間CAのルートを信頼せず影響のないルートは維持する()
    print(
        "Actual OpenSSL certifi trust bundle: compromised G3 absent; "
        "unaffected G1 / ISRG X1 retained"
    )
