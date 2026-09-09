import re
import copy
import urllib.request
import xml.etree.ElementTree as ET

M3U = "CanaisBR01-EPG-V3.m3u8"
SAIDA = "claro-CanaisBR01-V3.xml"

URL_EPG = (
    "https://raw.githubusercontent.com/"
    "limaalef/BrazilTVEPG/main/claro.xml"
)

# Lê nossa playlist
with open(M3U, "r", encoding="utf-8") as f:
    linhas = f.readlines()

# novo_id -> nome exibido
canais = {}

for linha in linhas:
    if linha.startswith("#EXTINF"):
        m_id = re.search(r'tvg-id="([^"]+)"', linha)
        if not m_id:
            continue

        novo_id = m_id.group(1)
        nome = linha.split(",", 1)[1].strip()

        canais[novo_id] = nome

# Mapeamento criado na V3:
# precisamos descobrir de qual canal original cada variante veio.
# Nomes/IDs especiais são tratados aqui.
aliases = {
    "AMCSD": "AMC HD",
    "AEFHDH265": "A&E",
    "AEHD": "A&E",
    "AESD": "A&E",
}

def normalizar(s):
    return re.sub(r"[^A-Z0-9]", "", s.upper())

print("Baixando EPG atualizado...")

urllib.request.urlretrieve(URL_EPG, "claro-atual.xml")

tree = ET.parse("claro-atual.xml")
root = tree.getroot()

originais = {
    normalizar(c.attrib["id"]): c.attrib["id"]
    for c in root.findall("channel")
}

# Tenta encontrar o canal original para cada variante
mapa = {}

for novo_id, nome in canais.items():

    if novo_id in aliases:
        mapa[novo_id] = aliases[novo_id]
        continue

    teste = normalizar(nome)

    # remove indicadores de qualidade
    for termo in [
        "FHDH265", "H265", "FHD",
        "4K", "HD", "SD"
    ]:
        teste = teste.replace(termo, "")

    candidatos = []

    for norm, original in originais.items():
        base = norm

        for termo in ["HD", "FHD", "SD", "4K"]:
            base = base.replace(termo, "")

        if teste == base:
            candidatos.append(original)

    if candidatos:
        mapa[novo_id] = candidatos[0]

print(f"{len(mapa)} variantes associadas.")

channels = {
    c.attrib["id"]: c
    for c in root.findall("channel")
}

programas = {}

for p in root.findall("programme"):
    programas.setdefault(
        p.attrib["channel"], []
    ).append(p)

novo_root = ET.Element("tv", root.attrib)

# Canais
for novo_id, original in mapa.items():

    if original not in channels:
        continue

    canal = copy.deepcopy(channels[original])
    canal.set("id", novo_id)

    display = canal.find("display-name")

    if display is not None:
        display.text = canais[novo_id]

    novo_root.append(canal)

# Programação
contador = 0

for novo_id, original in mapa.items():

    for programa in programas.get(original, []):

        p = copy.deepcopy(programa)
        p.set("channel", novo_id)

        novo_root.append(p)
        contador += 1

tree_saida = ET.ElementTree(novo_root)
ET.indent(tree_saida, space="  ")

tree_saida.write(
    SAIDA,
    encoding="utf-8",
    xml_declaration=True
)

print(f"EPG criado: {SAIDA}")
print(f"Programas: {contador}")
