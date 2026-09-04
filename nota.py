# -*- coding: utf-8 -*-
"""Gera as duas notas (.docx) a partir do estado. Uso: python nota.py AAAA-MM-DD"""
import sys
from datetime import date
from estado import P, PROVENTOS, ALVO_COMPLETA, ALVO_ESSENCIAL, BASE_COMPLETA, ANCORA_COMPLETA, BASE_ESSENCIAL
from engine import *
import docxgen as G

def serie_completa(ate):
    datas = [d for d in sorted(P) if d <= ate]
    unid, caixa = unidades(ALVO_COMPLETA, P[BASE_COMPLETA], P[BASE_COMPLETA]["PTAX"])
    _, v0 = valor(unid, P[BASE_COMPLETA], P[BASE_COMPLETA]["PTAX"], caixa)
    V = {BASE_COMPLETA: v0}; cx = caixa; hist = {}
    for i in range(1, len(datas)):
        d, a = datas[i], datas[i-1]
        var, cont, pes, cx, unid, va, vn = avanca(unid, cx, P[a], P[a]["PTAX"], P[d], P[d]["PTAX"], P[d]["CDI"], PROVENTOS.get(d))
        V[d] = vn; hist[d] = (var, cont, pes)
    da, ca = ANCORA_COMPLETA
    cotas = {d: ca*V[d]/V[da] for d in V}
    return cotas, hist

def serie_essencial(ate):
    datas = [d for d in sorted(P) if BASE_ESSENCIAL <= d <= ate]
    if not datas: return {}, {}
    unid, caixa = unidades(ALVO_ESSENCIAL, P[datas[0]], P[datas[0]]["PTAX"])
    _, v0 = valor(unid, P[datas[0]], P[datas[0]]["PTAX"], caixa)
    V = {datas[0]: v0}; cx = 0.0; hist = {}
    for i in range(1, len(datas)):
        d, a = datas[i], datas[i-1]
        var, cont, pes, cx, unid, va, vn = avanca(unid, cx, P[a], P[a]["PTAX"], P[d], P[d]["PTAX"], P[d]["CDI"], PROVENTOS.get(d))
        V[d] = vn; hist[d] = (var, cont, pes)
    cotas = {d: 100.0*V[d]/V[datas[0]] for d in V}
    return cotas, hist

def acumulado_cdi(d0, d1):
    f = 1.0
    for d in sorted(P):
        if d0 < d <= d1: f *= (1 + P[d]["CDI"]/100)**(1/252)
    return (f-1)*100

def _linhas_serie(cotas, desde, ate, rotulo_base):
    ds = [d for d in sorted(cotas) if desde <= d <= ate]
    linhas = []
    for i, d in enumerate(ds):
        rot = d.strftime("%d/%m/%Y") + (f" ({rotulo_base})" if i == 0 and rotulo_base else "")
        var = "" if i == 0 else pct((cotas[d]/cotas[ds[i-1]]-1)*100)
        linhas.append([rot, num(cotas[d], 3), var, pct(cotas[d]-100)])
    return linhas

def _top(cont, var, n, excluir=("CAIXA",)):
    positivo = var >= 0
    cand = [t for t in cont if t not in excluir and ((cont[t] > 0) if positivo else (cont[t] < 0))]
    top = sorted(cand, key=lambda t: -abs(cont[t]))[:n] or sorted([t for t in cont if t not in excluir], key=lambda t: -abs(cont[t]))[:n]
    palavra = "As maiores contribuições" if positivo else "As maiores detrações"
    if len(top) == 1:
        txt = f"{top[0]} ({pct(cont[top[0]])[:-1]} p.p.)"
    else:
        txt = ", ".join(f"{t} ({pct(cont[t])[:-1]} p.p.)" for t in top[:-1]) + f" e {top[-1]} ({pct(cont[top[-1]])[:-1]} p.p.)"
    return palavra, txt

def nota_completa(ref, destino):
    cotas, hist = serie_completa(ref)
    ds = sorted(cotas); ant = ds[ds.index(ref)-1]
    var, cont, pes = hist[ref]
    cdi = acumulado_cdi(BASE_COMPLETA, ref)
    ibov = (P[ref]["IBOV"]/P[BASE_COMPLETA]["IBOV"]-1)*100
    ibov_dia = (P[ref]["IBOV"]/P[ant]["IBOV"]-1)*100
    ptax_dia = (P[ref]["PTAX"]/P[ant]["PTAX"]-1)*100
    b = [G.cabecalho(data_referencia(ref)), G.secao("Resultado da estratégia")]
    b.append(G.par([
        G.run("A cota de referência da estratégia Backbone encerrou o pregão de "+data_extenso(ref)+" em "),
        G.run(num(cotas[ref],3), bold=True), G.run(", variação de "),
        G.run(pct(var), bold=True), G.run(" no dia. Desde 12 de agosto de 2026, a estratégia acumula "),
        G.run(pct(cotas[ref]-100), bold=True), G.run(f", contra {pct(cdi)} do CDI e {pct(ibov)} do Ibovespa no mesmo período."),
    ], just=True))
    b.append(G.par("A cota de referência tem base 100,000 em 12 de agosto de 2026 e reflete a evolução da carteira nos pesos da política de investimento, marcada a fechamentos oficiais de mercado e PTAX de venda. O resultado individual de cada investidor depende da data de entrada e dos preços de execução; a relação entre as cotas de duas datas fornece o retorno da estratégia no período correspondente. Rentabilidade bruta de impostos e custos de transação.", just=True))
    b.append(G.tabela(["Data","Cota de referência","Variação no dia","Acumulado"],
                      _linhas_serie(cotas, ANCORA_COMPLETA[0], ref, None), "62%"))
    b.append(G.secao("O pregão"))
    b.append(G.par(
        f"O Ibovespa {'subiu' if ibov_dia>=0 else 'caiu'} {pct(abs(ibov_dia),2,False)}, a {num(P[ref]['IBOV'],0)} pontos, "
        f"e o dólar PTAX de venda fechou em R$ {num(P[ref]['PTAX'],4)}, {'alta' if ptax_dia>=0 else 'queda'} de {pct(abs(ptax_dia),2,False)}.", just=True))
    palavra, txt_top = _top(cont, var, 5)
    b.append(G.secao("Carteira"))
    b.append(G.par(
        "Nas posições listadas em dólar, a variação em reais combina o preço do ativo e o câmbio do dia. "
        f"{palavra} do pregão vieram de {txt_top}, com o restante da carteira somando o complemento até a variação de {pct(var)} do dia. "
        f"A exposição cambial aberta da carteira encerrou em {pct(cambial_aberta(pes),1,False)} do total.", just=True))
    linhas = []
    for t in ALVO_COMPLETA:
        if t == "CAIXA":
            rdia = ((1+P[ref]["CDI"]/100)**(1/252)-1)*100
            linhas.append(["Caixa", FUNCAO[t], "", "", pct(rdia), pct(pes[t],1,False)]); continue
        loc, tot = var_ativo(t, P[ant], P[ref], P[ant]["PTAX"], P[ref]["PTAX"])
        preco = (f"US$ {num(P[ref][t],2)}" if t in USD_TICKERS else f"R$ {num(P[ref][t],2)}")
        linhas.append([t, FUNCAO[t], preco, pct(loc), pct(tot), pct(pes[t],1,False)])
    b.append(G.tabela(["Posição","Função na carteira","Fechamento","Var. pregão (moeda local)","Var. em R$ (com câmbio)","Peso"],
                      linhas, "100%"))
    fora = [t for t in ALVO_COMPLETA if abs(pes[t]-ALVO_COMPLETA[t]) > BANDAS[t]]
    he = hedge_efetivo(pes)
    b.append(G.secao("Posicionamento"))
    if fora:
        b.append(G.par("Fora das bandas da política: " + ", ".join(f"{t} em {pct(pes[t],1,False)} contra alvo de {pct(ALVO_COMPLETA[t],1,False)}" for t in fora) +
                       f". O hedge cambial efetivo da parcela de ações internacionais está em {pct(he,1,False)}, para um alvo de 35% e banda de 25% a 45%. Ordem de rebalanceamento a ser apresentada.", just=True))
    else:
        b.append(G.par("Todas as posições encerraram o pregão dentro das bandas da política de investimento. "
                       f"O hedge cambial efetivo da parcela de ações internacionais está em {pct(he,1,False)}, para um alvo de 35% e banda de 25% a 45%. "
                       "Não realizamos alterações na carteira e não há rebalanceamento indicado.", just=True))
    b.append(G.rodape("Material informativo destinado a investidores posicionados na estratégia Backbone. Não constitui oferta, recomendação individualizada ou garantia de resultado. Rentabilidade passada não é garantia de rentabilidade futura. Fontes: B3 e provedores de cotações (fechamentos de "+ref.strftime("%d/%m/%Y")+"), Banco Central do Brasil (PTAX de venda e CDI)."))
    return G.montar(b, destino)

def nota_essencial(ref, destino):
    cotas, hist = serie_essencial(ref)
    ds = sorted(cotas)
    primeira = (len(ds) == 1)
    cdi = acumulado_cdi(BASE_ESSENCIAL, ref)
    ibov = (P[ref]["IBOV"]/P[BASE_ESSENCIAL]["IBOV"]-1)*100 if not primeira else 0.0
    b = [G.cabecalho(data_referencia(ref)),
         G.par([G.run("Backbone Essencial  |  carteiras de R$ 200 mil a R$ 500 mil", sz=18, color="666666")], after=120),
         G.secao("Resultado da estratégia")]
    if primeira:
        b.append(G.par([
            G.run("A estratégia Backbone Essencial passa a ser acompanhada por uma cota de referência com base "),
            G.run("100,000", bold=True),
            G.run(" no fechamento de "+data_extenso(ref)+". Este é o primeiro pregão da série, e por isso não há variação a reportar."),
        ], just=True))
    else:
        ant = ds[ds.index(ref)-1]
        var = hist[ref][0]
        b.append(G.par([
            G.run("A cota de referência da estratégia Backbone Essencial encerrou o pregão de "+data_extenso(ref)+" em "),
            G.run(num(cotas[ref],3), bold=True), G.run(", variação de "),
            G.run(pct(var), bold=True), G.run(f" no dia. Desde {data_extenso(BASE_ESSENCIAL)}, a estratégia acumula "),
            G.run(pct(cotas[ref]-100), bold=True), G.run(f", contra {pct(cdi)} do CDI e {pct(ibov)} do Ibovespa no mesmo período."),
        ], just=True))
    b.append(G.par("A Essencial reproduz as funções econômicas da carteira completa em seis posições, sem exposição cambial aberta e sem as convicções setoriais de menor peso. A cota tem base 100,000 em "+data_extenso(BASE_ESSENCIAL)+", marcada a fechamentos oficiais de mercado. Rentabilidade bruta de impostos e custos de transação.", just=True))
    if not primeira:
        b.append(G.tabela(["Data","Cota de referência","Variação no dia","Acumulado"],
                          _linhas_serie(cotas, BASE_ESSENCIAL, ref, "base"), "62%"))
        ant = ds[ds.index(ref)-1]
        ibov_dia = (P[ref]["IBOV"]/P[ant]["IBOV"]-1)*100
        b.append(G.secao("O pregão"))
        b.append(G.par(f"O Ibovespa {'subiu' if ibov_dia>=0 else 'caiu'} {pct(abs(ibov_dia),2,False)}, a {num(P[ref]['IBOV'],0)} pontos.", just=True))
    b.append(G.secao("Carteira"))
    if primeira:
        pes = {t: ALVO_ESSENCIAL[t] for t in ALVO_ESSENCIAL}
        linhas = [[t, FUNCAO[t], f"R$ {num(P[ref][t],2)}", "", pct(pes[t],1,False)] for t in ALVO_ESSENCIAL]
        b.append(G.par("Quadro de abertura da carteira, nos pesos-alvo da política e nos fechamentos da data-base.", just=True))
        b.append(G.tabela(["Posição","Função na carteira","Fechamento","Var. pregão","Peso"], linhas, "100%"))
    else:
        ant = ds[ds.index(ref)-1]
        var, cont, pes = hist[ref]
        palavra, txt = _top(cont, var, 4)
        b.append(G.par(f"{palavra} do pregão vieram de {txt}, com o restante da carteira somando o complemento até a variação de {pct(var)} do dia.", just=True))
        linhas = [[t, FUNCAO[t], f"R$ {num(P[ref][t],2)}", pct(var_ativo(t,P[ant],P[ref],P[ant]['PTAX'],P[ref]['PTAX'])[0]), pct(pes[t],1,False)] for t in ALVO_ESSENCIAL]
        b.append(G.tabela(["Posição","Função na carteira","Fechamento","Var. pregão","Peso"], linhas, "100%"))
    b.append(G.secao("Posicionamento"))
    fora = [t for t in ALVO_ESSENCIAL if abs(pes[t]-ALVO_ESSENCIAL[t]) > BANDAS[t]]
    if fora:
        b.append(G.par("Fora das bandas da política: " + ", ".join(f"{t} em {pct(pes[t],1,False)} contra alvo de {pct(ALVO_ESSENCIAL[t],1,False)}" for t in fora) + ". Ordem de rebalanceamento a ser apresentada.", just=True))
    else:
        b.append(G.par("Todas as posições encerraram o pregão dentro das bandas da política de investimento. Não realizamos alterações na carteira e não há rebalanceamento indicado.", just=True))
    b.append(G.rodape("Material informativo destinado a investidores posicionados na estratégia Backbone. Não constitui oferta, recomendação individualizada ou garantia de resultado. Rentabilidade passada não é garantia de rentabilidade futura. Fontes: B3 e provedores de cotações (fechamentos de "+ref.strftime("%d/%m/%Y")+"), Banco Central do Brasil (CDI)."))
    return G.montar(b, destino)

def gerar(ref):
    """Gera os dois .docx reempacotados. Devolve os dois caminhos."""
    import repack
    tag = ref.strftime("%d%m%Y")
    saidas = []
    for fn, nome in ((nota_completa, "Completa"), (nota_essencial, "Essencial")):
        bruto = f"_bruto_{nome}_{tag}.docx"
        final = f"Maralto_Backbone_{nome}_{tag}.docx"
        fn(ref, bruto)
        repack.repack(bruto, final)
        saidas.append(final)
    return saidas

if __name__ == "__main__":
    ref = date.fromisoformat(sys.argv[1])
    for s in gerar(ref):
        print(s)
