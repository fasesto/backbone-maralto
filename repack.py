# -*- coding: utf-8 -*-
"""Reempacota o .docx do python-docx com o mínimo de partes.

O estilo da nota vai inline em cada run, então a biblioteca de estilos padrão
(cerca de 30 KB) não é usada. Sem ela o arquivo cai de ~39 KB para ~5 KB e passa
em base64 na chamada de envio do Gmail. O word/document.xml é copiado sem tocar.

Uso: python repack.py entrada.docx saida.docx
"""
import sys, zipfile

CT = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
      '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
      '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
      '<Default Extension="xml" ContentType="application/xml"/>'
      '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
      '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
      '</Types>')
RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        '</Relationships>')
DOC_RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            '</Relationships>')
STYLES = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
          '<w:docDefaults><w:rPrDefault><w:rPr>'
          '<w:rFonts w:ascii="Georgia" w:hAnsi="Georgia" w:cs="Georgia" w:eastAsia="Georgia"/>'
          '<w:sz w:val="19"/><w:szCs w:val="19"/><w:lang w:val="pt-BR"/>'
          '</w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="120"/></w:pPr></w:pPrDefault></w:docDefaults>'
          '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>'
          '<w:style w:type="table" w:default="1" w:styleId="TableNormal"><w:name w:val="Normal Table"/>'
          '<w:tblPr><w:tblCellMar><w:left w:type="dxa" w:w="108"/><w:right w:type="dxa" w:w="108"/></w:tblCellMar></w:tblPr></w:style>'
          '</w:styles>')

def repack(entrada, saida):
    with zipfile.ZipFile(entrada) as z:
        document = z.read("word/document.xml")
    with zipfile.ZipFile(saida, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CT)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/_rels/document.xml.rels", DOC_RELS)
        z.writestr("word/styles.xml", STYLES)
        z.writestr("word/document.xml", document)
    return saida

def conferir(entrada, saida):
    """True se o document.xml dos dois arquivos é byte a byte igual."""
    with zipfile.ZipFile(entrada) as a, zipfile.ZipFile(saida) as b:
        return a.read("word/document.xml") == b.read("word/document.xml")

if __name__ == "__main__":
    e, s = sys.argv[1], sys.argv[2]
    repack(e, s)
    print("ok" if conferir(e, s) else "DIVERGE", s)
