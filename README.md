# justifactu
Software to automate billing justification at ICIQ

## Goal
Merge bills with payments and archive them into Sharepoint. 

### Algorithm for cards

```pseudocode
si current.month <= 3:
  years = [current.year, current.year - 1]
else
  years = [current.year]

excels = years_to_excels(years)
  
per excel en excels:
  per fila en excel:
    si col_J està ple i col_J es numero i col_K es buida:
      mes = col_B
      justificant = col_J + "_P.pdf"
      nom_pdf_targeta = 

```

### Algorithm for merging bills and payments
```pseudocode
per factura a carpeta_factura:
  justificant = factura.nom.substitute("F", "P")
  si justificant existeix:
    juntar_pdfs(factura, justificant, dst=factura_mes_pagament(factura, pagament))
    borrar(factura)
    borrar(pagament)

```