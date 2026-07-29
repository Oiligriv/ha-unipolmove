# Unipolmove per Home Assistant

Integrazione **non ufficiale** per leggere in Home Assistant fatture e costi (pedaggi, Area C, parcheggi, traghetti) del
tuo dispositivo Unipolmove (Telepass-style, UnipolSai/Utech).

> ⚠️ Non affiliata/approvata da UnipolSai o Unipolmove. Usa endpoint non documentati di `www.unipolmove.it`, che
> possono cambiare senza preavviso. Nessuna garanzia di funzionamento continuo.

## Come funziona

A differenza di ACEA (bloccata da reCAPTCHA), il login di Unipolmove è un semplice form username/password **senza
CAPTCHA**: questa integrazione esegue davvero il login al posto tuo, periodicamente, e si ri-autentica da sola se la
sessione scade.

## Sensori esposti

| Sensore | Descrizione |
|---|---|
| Importo Fattura | Importo dell'ultima fattura (numero fattura e merchant negli attributi) |
| Data Fattura | Data di emissione dell'ultima fattura |
| Stato | Stato pagamento (es. `ADDEBITATO`) |
| Costo Transiti | Spesa pedaggi autostradali nel periodo corrente |
| Costo Area C | Spesa Area C Milano nel periodo corrente |
| Costo Parcheggi | Spesa parcheggi (prenotazioni negli attributi) |
| Costo Traghetti | Spesa traghetti nel periodo corrente |

## Installazione

1. Copia `custom_components/unipolmove` in `config/custom_components/` della tua installazione Home Assistant
2. Riavvia Home Assistant

## Configurazione

**Impostazioni → Dispositivi e Servizi → Aggiungi Integrazione → "Unipolmove"**

Ti verranno chiesti:

| Campo | Note |
|---|---|
| Email | La tua email di accesso a www.unipolmove.it |
| Password | La tua password |
| Numero contratto | Formato `P` + 9 cifre, es. `P000012345` |

### Dove trovare il numero di contratto

Non compare in nessuna pagina visibile del sito con un'etichetta chiara - il modo più semplice è aprire (o scaricare)
il **PDF di una qualsiasi fattura** dalla tua area clienti: il numero contratto è stampato nell'intestazione del
documento. In alternativa puoi cercarlo nel contratto originale ricevuto all'attivazione o nelle email di benvenuto
Unipolmove.

## Limiti noti

- Dipende dal formato delle risposte JSON del sito: un cambiamento lato Unipolmove può rompere il parsing senza preavviso
- Il codice usa un header `x-ibm-client-id`/`x-ibm-client-secret` che non è un segreto personale: è una credenziale
  pubblica incorporata nel bundle JS del sito stesso, inviata da ogni visitatore - estratta qui allo stesso modo in
  cui la vedresti tu aprendo gli Strumenti Sviluppatore del browser
- Nessun supporto per più contratti sullo stesso account

## Licenza

MIT
