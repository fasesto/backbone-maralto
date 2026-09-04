# -*- coding: utf-8 -*-
"""Leitura e gravação do estado da rotina Backbone (backbone-estado.json).

É o único módulo que toca o JSON. Expõe P, PROVENTOS, ALVO_* e datas-base no
formato que engine.py e nota.py esperam (chaves datetime.date).
"""
import json, os
from datetime import date, datetime

ARQ = os.environ.get("BACKBONE_ESTADO", os.path.join(os.path.dirname(os.path.abspath(__file__)), "backbone-estado.json"))
CAMPOS = ["LFTB11","B5P211","B5MB11","WRLD11","SPXR11","GOLD11","SMAL11",
          "GOVT","TLT","KMLM","SMH","URA","PTAX","CDI","IBOV"]

def _d(s): return datetime.strptime(s, "%Y-%m-%d").date()
def _s(d): return d.strftime("%Y-%m-%d")

def carregar(arq=ARQ):
    with open(arq, encoding="utf-8") as f:
        return json.load(f)

def _linha(v):
    return json.dumps(v, ensure_ascii=False)

def serializar(est):
    """JSON legível: uma linha por pregão, resto indentado."""
    est["precos"] = dict(sorted(est["precos"].items()))
    est["proventos"] = dict(sorted(est.get("proventos", {}).items()))
    est["procedencia"] = dict(sorted(est.get("procedencia", {}).items()))
    partes = []
    for k, v in est.items():
        if k in ("precos", "proventos", "procedencia"):
            corpo = ",\n".join(f'  {json.dumps(d)}: {_linha(x)}' for d, x in v.items())
            partes.append(f'{json.dumps(k)}: {{\n{corpo}\n }}')
        elif k == "politica":
            corpo = ",\n".join(f'  {json.dumps(a)}: {_linha(b)}' for a, b in v.items())
            partes.append(f'{json.dumps(k)}: {{\n{corpo}\n }}')
        else:
            partes.append(f'{json.dumps(k)}: {_linha(v)}')
    return "{\n " + ",\n ".join(partes) + "\n}\n"

def gravar(est, arq=ARQ):
    tmp = arq + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(serializar(est))
    json.loads(open(tmp, encoding="utf-8").read())   # garante JSON válido antes de trocar
    os.replace(tmp, arq)

def ultima_data(est):
    return _d(max(est["precos"]))

# --- calendário B3 ---------------------------------------------------------
def dia_util_b3(est, d):
    return d.weekday() < 5 and _s(d) not in est.get("feriados_b3", [])

def pregao_anterior(est, d):
    """Último dia útil B3 estritamente anterior a d."""
    from datetime import timedelta
    x = d - timedelta(days=1)
    while not dia_util_b3(est, x):
        x -= timedelta(days=1)
    return x

def tem_data(est, d):
    return _s(d) in est["precos"]

def adicionar_pregao(est, d, precos, procedencia, cdi_provisorio=False, proventos=None):
    """Grava a linha de um pregão. Recusa linha incompleta ou data repetida."""
    faltam = [c for c in CAMPOS if c not in precos]
    if faltam:
        raise ValueError(f"linha de {_s(d)} incompleta: faltam {faltam}")
    if tem_data(est, d):
        raise ValueError(f"{_s(d)} já está no estado; não sobrescrever")
    est["precos"][_s(d)] = {c: float(precos[c]) for c in CAMPOS}
    est["procedencia"][_s(d)] = procedencia
    if cdi_provisorio:
        est.setdefault("cdi_provisorio", []).append(_s(d))
    if proventos:
        est.setdefault("proventos", {})[_s(d)] = {k: float(v) for k, v in proventos.items()}

def corrigir_cdi(est, d, cdi):
    """Substitui o CDI provisório pela taxa definitiva e tira a data da lista."""
    k = _s(d)
    est["precos"][k]["CDI"] = float(cdi)
    if k in est.get("cdi_provisorio", []):
        est["cdi_provisorio"].remove(k)

def marcar_nota_enviada(est, d):
    if _s(d) not in est["notas_enviadas"]:
        est["notas_enviadas"].append(_s(d))
        est["notas_enviadas"].sort()

def nota_ja_enviada(est, d):
    return _s(d) in est["notas_enviadas"]

# --- vista no formato do motor -------------------------------------------
_E = carregar()
P = {_d(k): dict(v) for k, v in _E["precos"].items()}
PROVENTOS = {_d(k): dict(v) for k, v in _E.get("proventos", {}).items()}
ALVO_COMPLETA = _E["politica"]["alvo_completa"]
ALVO_ESSENCIAL = _E["politica"]["alvo_essencial"]
BASE_COMPLETA = _d(_E["politica"]["base_completa"])
ANCORA_COMPLETA = (_d(_E["politica"]["ancora_completa"]["data"]), _E["politica"]["ancora_completa"]["cota"])
BASE_ESSENCIAL = _d(_E["politica"]["base_essencial"])
