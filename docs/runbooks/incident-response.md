# Runbook: raspuns general la incident

## Activare

Foloseste acest runbook pentru SEV-1/SEV-2 sau cand componenta afectata nu este
inca identificata. Pentru compromitere continua cu
[security-incident.md](security-incident.md).

## Primele actiuni

1. Noteaza ora UTC, simptomele, commitul si serviciile afectate.
2. Opreste actiunea daunatoare: import, cron, deploy, checkout sau upload, dupa caz.
3. Pastreaza logurile si identificatorii tehnici; nu copia secrete sau date personale.
4. Stabileste un singur coordonator si un canal privat.
5. Alege runbookul specific din [operations.md](../operations.md).

## Comunicare

Comunica doar impactul confirmat si intervalul urmatoarei actualizari. Nu publica
cauze presupuse, date personale sau promisiuni juridice. Incidentele de date pot
necesita evaluare GDPR de catre persoana responsabila.

## Inchidere

Inchiderea cere revenirea metricilor, un test al fluxului afectat, monitorizare
30 minute si un follow-up cu proprietar si termen. Pastreaza jurnalul privat.
