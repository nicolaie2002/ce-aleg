# Runbook: calitatea catalogului degradata

## Simptome

- scorul din Admin -> Catalog quality scade sub prag;
- cresc produsele `Altele`, duplicatele, imaginile lipsa sau datele nutritionale goale;
- cautarile fara rezultat si alternativele raportate cresc brusc.

## Diagnostic si remediere

1. Verifica raportul admin si distribuirea problemelor pe categorii/surse.
2. Opreste importul care a introdus regresia; nu sterge in masa produse.
3. Ruleaza recategorizarea in dry-run si inspecteaza esantionul.
4. Aplica doar dupa backup recent si dupa confirmarea regulilor.
5. Prioritizeaza contributiile cu barcode valid, fotografii si nutritie verificabila.
6. Recalculeaza raportul si compara scorul, duplicatele si categoriile.

Importul Open Food Facts si contributiile comunitatii raman gratuite. Nu activa
surse comerciale sau AI platit pentru a masca lipsa datelor.

Vezi si [catalog-import.md](catalog-import.md).
