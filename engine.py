# -*- coding: utf-8 -*-
"""Motor de cálculo da nota Backbone. Trabalha com um snapshot de preços por data."""
from datetime import date

FUNCAO = {
 "LFTB11":"Carry nominal (Tesouro Selic)","B5P211":"Juro real curto (IMA-B5)",
 "B5MB11":"Duration em juro real (IMA-B5+)","WRLD11":"Ações globais sem hedge",
 "SPXR11":"Ações EUA com hedge cambial","GOLD11":"Ouro","SMAL11":"Small caps Brasil",
 "GOVT":"Treasuries EUA","TLT":"Duration longa EUA","KMLM":"Managed futures",
 "SMH":"Semicondutores","URA":"Urânio","CAIXA":"Liquidez remunerada (CDI)"}
USD_TICKERS = {"GOVT","TLT","KMLM","SMH","URA"}
BANDAS = {"LFTB11":2.0,"B5P211":2.5,"B5MB11":1.0,"WRLD11":2.5,"SPXR11":1.5,"GOLD11":1.5,
          "SMAL11":0.7,"GOVT":1.0,"TLT":0.7,"KMLM":1.0,"SMH":0.7,"URA":0.5,"CAIXA":3.0}

def brl(t, px, ptax):
    return px[t]*ptax if t in USD_TICKERS else px[t]

def valor(unid, px, ptax, caixa):
    v = {t: unid[t]*brl(t, px, ptax) for t in unid}
    return v, sum(v.values()) + caixa

def unidades(alvo, px, ptax, nav=1_000_000.0):
    tk = [t for t in alvo if t != "CAIXA"]
    return ({t: nav*alvo[t]/100/brl(t, px, ptax) for t in tk}, nav*alvo.get("CAIXA", 0.0)/100)

def avanca(unid, caixa, px_ant, ptax_ant, px, ptax, cdi_aa, proventos=None):
    """Um pregão. Devolve (var_dia, contribuicoes, pesos, caixa_novo, unid, v_ant, v_novo)."""
    _, v_ant = valor(unid, px_ant, ptax_ant, caixa)
    caixa_n = caixa * (1 + cdi_aa/100)**(1/252)
    for t, d in (proventos or {}).items():
        if t in unid:
            recebido = unid[t]*d*ptax
            if caixa: caixa_n += recebido
            else: unid[t] += recebido/brl(t, px, ptax)
    v_i_ant, _ = valor(unid, px_ant, ptax_ant, caixa)
    v_i, v_novo = valor(unid, px, ptax, caixa_n)
    contrib = {t: 100*(v_i[t]-v_i_ant[t])/v_ant for t in unid}
    contrib["CAIXA"] = 100*(caixa_n-caixa)/v_ant if caixa else 0.0
    pesos = {t: 100*v_i[t]/v_novo for t in unid}
    if caixa: pesos["CAIXA"] = 100*caixa_n/v_novo
    return (v_novo/v_ant - 1)*100, contrib, pesos, caixa_n, unid, v_ant, v_novo

def var_ativo(t, px_ant, px, ptax_ant, ptax):
    loc = px[t]/px_ant[t] - 1
    tot = brl(t, px, ptax)/brl(t, px_ant, ptax_ant) - 1
    return loc*100, tot*100

def cambial_aberta(pesos):
    return sum(pesos.get(t, 0.0) for t in list(USD_TICKERS)+["WRLD11"])

def hedge_efetivo(pesos):
    a, b = pesos.get("SPXR11", 0.0), pesos.get("WRLD11", 0.0)
    return 100*a/(a+b) if (a+b) else None

def num(x, casas=2):
    return f"{x:,.{casas}f}".replace(",", "@").replace(".", ",").replace("@", ".")

def pct(x, casas=2, sinal=True):
    s = f"{x:+.{casas}f}" if sinal else f"{x:.{casas}f}"
    return s.replace(".", ",") + "%"

MESES = ["janeiro","fevereiro","março","abril","maio","junho","julho","agosto",
         "setembro","outubro","novembro","dezembro"]
DIAS = ["segunda-feira","terça-feira","quarta-feira","quinta-feira","sexta-feira","sábado","domingo"]

def data_extenso(d: date):
    return f"{d.day} de {MESES[d.month-1]} de {d.year}"

def data_referencia(d: date):
    return f"Referência: pregão de {DIAS[d.weekday()]}, {data_extenso(d)}"
