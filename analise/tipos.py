"""Normalização da tipologia do imóvel.

A Caixa escreve o tipo como primeira palavra da descrição, e a grafia varia:
"Apartamento", "Casa", "Terreno", "Loja", "Comercial", "Sala", "Gleba",
"Imóvel rural". Aqui tudo isso cai em cinco categorias que o resto do
sistema entende.
"""

from __future__ import annotations

CATEGORIAS = ("Apartamento", "Casa", "Sala comercial", "Loja", "Terreno")


def normalizar_tipo(texto: str) -> str:
    t = (texto or "").strip().lower()
    if any(p in t for p in ("apart", "flat", "kitnet", "studio", "loft")):
        return "Apartamento"
    if any(p in t for p in ("casa", "sobrado", "condomin")):
        return "Casa"
    if any(p in t for p in ("sala", "conjunto", "escrit", "comercial")):
        return "Sala comercial"
    if any(p in t for p in ("loja", "ponto", "galp")):
        return "Loja"
    if any(p in t for p in ("terreno", "lote", "gleba", "rural", "area")):
        return "Terreno"
    return "Apartamento"
