# -*- coding: utf-8 -*-
"""Gera a nota de performance no formato exato do modelo de 27/08/2026. Estilo inline em cada run; não depende de template."""
from xml.sax.saxutils import escape

F = '<w:rFonts w:ascii="Georgia" w:cs="Georgia" w:eastAsia="Georgia" w:hAnsi="Georgia"/>'

def run(t, sz=19, bold=False, color="1A1A1A"):
    rpr = F + ('<w:b/><w:bCs/>' if bold else '') + f'<w:color w:val="{color}"/><w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>'
    return f'<w:r><w:rPr>{rpr}</w:rPr><w:t xml:space="preserve">{escape(t)}</w:t></w:r>'

def par(runs, after=120, before=None, just=False, border=False):
    ppr = '<w:pPr>'
    if border: ppr += '<w:pBdr><w:bottom w:val="single" w:color="1A1A1A" w:sz="6"/></w:pBdr>'
    ppr += '<w:spacing w:after="%d"%s/>' % (after, (' w:before="%d"' % before) if before else '')
    if just: ppr += '<w:jc w:val="both"/>'
    ppr += '</w:pPr>'
    if isinstance(runs, str): runs = [run(runs)]
    return '<w:p>' + ppr + ''.join(runs) + '</w:p>'

def secao(txt):
    return par([run(txt, sz=20, bold=True)], after=80, before=120)

def _cell(txt, bold=False, header=False, align="left"):
    shd = '<w:shd w:fill="F2F2F2" w:val="clear"/>' if header else ''
    tcpr = ('<w:tcPr>' + shd +
            '<w:tcMar><w:top w:type="dxa" w:w="20"/><w:left w:type="dxa" w:w="80"/>'
            '<w:bottom w:type="dxa" w:w="20"/><w:right w:type="dxa" w:w="80"/></w:tcMar>'
            '<w:vAlign w:val="center"/></w:tcPr>')
    p = ('<w:p><w:pPr><w:spacing w:after="20" w:before="20"/>'
         f'<w:jc w:val="{align}"/></w:pPr>' + run(txt, sz=17, bold=(bold or header)) + '</w:p>')
    return '<w:tc>' + tcpr + p + '</w:tc>'

def tabela(header, linhas, largura="62%", alinhamentos=None):
    n = len(header)
    al = alinhamentos or ["left"]*n
    x = ('<w:tbl><w:tblPr><w:tblW w:type="pct" w:w="%s"/><w:jc w:val="left"/>'
         '<w:tblBorders><w:top w:val="single" w:color="CCCCCC" w:sz="2"/><w:left w:val="none"/>'
         '<w:bottom w:val="single" w:color="CCCCCC" w:sz="2"/><w:right w:val="none"/>'
         '<w:insideH w:val="single" w:color="DDDDDD" w:sz="2"/><w:insideV w:val="none"/>'
         '</w:tblBorders></w:tblPr><w:tblGrid>' % largura)
    x += '<w:gridCol w:w="100"/>'*n + '</w:tblGrid>'
    x += '<w:tr><w:trPr><w:tblHeader/></w:trPr>' + ''.join(_cell(h, header=True, align=al[i]) for i,h in enumerate(header)) + '</w:tr>'
    for ln in linhas:
        x += '<w:tr>' + ''.join(_cell(c, align=al[i]) for i,c in enumerate(ln)) + '</w:tr>'
    return x + '</w:tbl>'

def cabecalho(referencia):
    return (par([run("MARALTO CAPITAL", sz=26, bold=True)], after=40) +
            par([run("Estratégia Backbone  |  Nota de Performance", sz=21, bold=True, color="1F6E43")], after=40) +
            par([run(referencia, sz=18, color="666666")], after=160, border=True))

def rodape(txt):
    return par([run(txt, sz=15, color="666666")], after=0, before=200, just=True)

def montar(blocos, destino):
    """Monta o .docx com python-docx só para a casca; o conteúdo é o XML acima."""
    import docx
    from docx.oxml.ns import qn
    from docx.oxml import parse_xml
    from docx.shared import Twips
    d = docx.Document()
    sec = d.sections[0]
    sec.page_width, sec.page_height = Twips(11906), Twips(16838)
    sec.top_margin, sec.bottom_margin = Twips(850), Twips(850)
    sec.left_margin, sec.right_margin = Twips(1000), Twips(1000)
    body = d.element.body
    for ch in list(body):
        if ch.tag != qn('w:sectPr'):
            body.remove(ch)
    sectpr = body.find(qn('w:sectPr'))
    NS = ' xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    for bloco in blocos:
        for frag in _split_top(bloco):
            if frag.startswith('<w:p>'):
                frag = frag.replace('<w:p>', '<w:p'+NS+'>', 1)
            elif frag.startswith('<w:tbl>'):
                frag = frag.replace('<w:tbl>', '<w:tbl'+NS+'>', 1)
            sectpr.addprevious(parse_xml(frag))
    d.save(destino)
    return destino

def _split_top(x):
    """Separa parágrafos e tabelas de nível superior concatenados numa string."""
    out, i = [], 0
    while i < len(x):
        if x.startswith('<w:p>', i):
            j = x.index('</w:p>', i) + len('</w:p>')
        elif x.startswith('<w:tbl>', i):
            j = x.index('</w:tbl>', i) + len('</w:tbl>')
        else:
            break
        out.append(x[i:j]); i = j
    return out
