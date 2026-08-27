# -*- coding: utf-8 -*-
"""Gera os SVGs de metricas do perfil a partir da API publica do GitHub.

Existe porque os servicos publicos de badge (github-readme-stats, activity-graph,
trophy) vivem fora do ar por estouro de cota. Gerando aqui, o perfil nao depende
da disponibilidade de terceiro: o SVG fica versionado no proprio repositorio.
"""
import json
import os
import sys
import urllib.error
import urllib.request

USUARIO = "GuilhermeOliveira337"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
SAIDA = "metrics"

# cores oficiais do GitHub por linguagem
COR_LINGUAGEM = {
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "Python": "#3572A5",
    "Java": "#b07219",
    "Shell": "#89e051",
    "SCSS": "#c6538c",
    "Vue": "#41b883",
    "PHP": "#4F5D95",
}
COR_PADRAO = "#8b949e"


def api(caminho):
    req = urllib.request.Request(f"https://api.github.com{caminho}")
    req.add_header("Accept", "application/vnd.github+json")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def graphql(consulta):
    dados = json.dumps({"query": consulta}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=dados)
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def coletar():
    repos, pagina = [], 1
    while True:
        lote = api(f"/users/{USUARIO}/repos?per_page=100&page={pagina}")
        if not lote:
            break
        repos.extend(lote)
        pagina += 1
        if len(lote) < 100:
            break

    proprios = [r for r in repos if not r["fork"]]

    linguagens = {}
    no_ar = 0
    for r in proprios:
        if r.get("has_pages"):
            no_ar += 1
        try:
            for nome, bytes_ in api(f"/repos/{USUARIO}/{r['name']}/languages").items():
                linguagens[nome] = linguagens.get(nome, 0) + bytes_
        except urllib.error.HTTPError:
            pass

    contribuicoes = 0
    if TOKEN:
        try:
            r = graphql(
                '{ user(login: "%s") { contributionsCollection '
                "{ contributionCalendar { totalContributions } } } }" % USUARIO
            )
            contribuicoes = r["data"]["user"]["contributionsCollection"][
                "contributionCalendar"
            ]["totalContributions"]
        except Exception:
            contribuicoes = 0

    return {
        "repositorios": len(proprios),
        "no_ar": no_ar,
        "contribuicoes": contribuicoes,
        "estrelas": sum(r["stargazers_count"] for r in proprios),
        "linguagens": dict(
            sorted(linguagens.items(), key=lambda kv: kv[1], reverse=True)[:6]
        ),
    }


DEFS = """
  <defs>
    <linearGradient id="neon" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#00d8ff"/>
      <stop offset="55%" stop-color="#7b5cff"/>
      <stop offset="100%" stop-color="#ff2e97"/>
    </linearGradient>
    <pattern id="grid" width="28" height="28" patternUnits="userSpaceOnUse">
      <path d="M28 0H0V28" fill="none" stroke="#00d8ff" stroke-opacity=".06" stroke-width="1"/>
    </pattern>
  </defs>
"""

MONO = "'JetBrains Mono','SFMono-Regular',Consolas,'Liberation Mono',monospace"


def moldura(largura, altura, titulo):
    return f"""  <rect x="1" y="1" width="{largura-2}" height="{altura-2}" rx="10"
        fill="#0d1117" stroke="url(#neon)" stroke-width="1.6"/>
  <rect x="1" y="1" width="{largura-2}" height="{altura-2}" rx="10" fill="url(#grid)"/>
  <text x="24" y="34" font-family="{MONO}" font-size="13" font-weight="700"
        letter-spacing="2.5" fill="#00d8ff">{titulo}</text>
  <rect x="24" y="44" width="{largura-48}" height="1.5" fill="url(#neon)" opacity=".55"/>
"""


def svg_estatisticas(d):
    largura, altura = 480, 210
    linhas = [
        ("Repositorios publicos", str(d["repositorios"])),
        ("Projetos publicados no ar", str(d["no_ar"])),
        ("Contribuicoes (12 meses)", str(d["contribuicoes"])),
        ("Linguagem principal", next(iter(d["linguagens"]), "-")),
    ]
    corpo = ""
    y = 80
    for rotulo, valor in linhas:
        corpo += (
            f'  <text x="24" y="{y}" font-family="{MONO}" font-size="13" '
            f'fill="#8b9dc3">{rotulo}</text>\n'
            f'  <text x="{largura-24}" y="{y}" text-anchor="end" font-family="{MONO}" '
            f'font-size="16" font-weight="700" fill="#e6f7ff">{valor}</text>\n'
        )
        y += 34
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {largura} {altura}" '
        f'width="{largura}" height="{altura}" role="img" aria-label="Estatisticas do perfil">\n'
        f"  <title>Estatisticas do perfil de {USUARIO}</title>\n{DEFS}"
        f'{moldura(largura, altura, "METRICAS DO PERFIL")}{corpo}</svg>\n'
    )


def svg_linguagens(d):
    largura, altura = 480, 210
    total = sum(d["linguagens"].values()) or 1
    itens = list(d["linguagens"].items())

    barra, x = "", 24.0
    disponivel = largura - 48
    for nome, bytes_ in itens:
        w = disponivel * bytes_ / total
        cor = COR_LINGUAGEM.get(nome, COR_PADRAO)
        barra += (
            f'  <rect x="{x:.1f}" y="66" width="{w:.1f}" height="13" fill="{cor}"/>\n'
        )
        x += w

    legenda, y = "", 112
    for i, (nome, bytes_) in enumerate(itens):
        col = i % 2
        cx = 24 + col * (disponivel / 2)
        if col == 0 and i:
            y += 30
        pct = 100.0 * bytes_ / total
        cor = COR_LINGUAGEM.get(nome, COR_PADRAO)
        legenda += (
            f'  <circle cx="{cx+5}" cy="{y-4}" r="5" fill="{cor}"/>\n'
            f'  <text x="{cx+18}" y="{y}" font-family="{MONO}" font-size="12.5" '
            f'fill="#c9d1d9">{nome}</text>\n'
            f'  <text x="{cx+(disponivel/2)-14}" y="{y}" text-anchor="end" '
            f'font-family="{MONO}" font-size="12.5" font-weight="700" '
            f'fill="#7fdcff">{pct:.1f}%</text>\n'
        )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {largura} {altura}" '
        f'width="{largura}" height="{altura}" role="img" aria-label="Linguagens mais usadas">\n'
        f"  <title>Linguagens mais usadas por {USUARIO}</title>\n{DEFS}"
        f'{moldura(largura, altura, "LINGUAGENS MAIS USADAS")}'
        f'  <clipPath id="r"><rect x="24" y="66" width="{disponivel}" height="13" rx="6.5"/></clipPath>\n'
        f'  <g clip-path="url(#r)">\n{barra}  </g>\n{legenda}</svg>\n'
    )


if __name__ == "__main__":
    try:
        dados = coletar()
    except Exception as e:  # falha de rede/API nao deve gerar SVG vazio
        print(f"ERRO ao coletar dados: {e}", file=sys.stderr)
        sys.exit(1)

    if not dados["linguagens"]:
        print("ERRO: nenhuma linguagem retornada — abortando", file=sys.stderr)
        sys.exit(1)

    os.makedirs(SAIDA, exist_ok=True)
    with open(f"{SAIDA}/stats.svg", "w", encoding="utf-8") as f:
        f.write(svg_estatisticas(dados))
    with open(f"{SAIDA}/languages.svg", "w", encoding="utf-8") as f:
        f.write(svg_linguagens(dados))

    print(json.dumps(dados, indent=2, ensure_ascii=False))
