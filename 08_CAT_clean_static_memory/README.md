# 🧹 CAT Clean Static Memory

Plugin per il Cheshire Cat Framework che automatizza la pulizia giornaliera della cartella `cat/static/`, eliminando tutti i file tranne quelli `.json`.

## ✨ Caratteristiche

- **Pulizia automatica schedulata** all'orario configurabile
- **Preserva tutti i file `.json`** (configurazioni, settings)
- **Supporto multi-timezone** con conversione automatica UTC
- **Hot reload**: modifica l'orario senza riavviare il Cat

## ⚙️ Configurazione

Accedi ai Settings del plugin dall'interfaccia web e configura:

- `cleanup_hour`: Ora della pulizia (0-23, default: 17)
- `cleanup_minute`: Minuto della pulizia (0-59, default: 16)
- `timezone`: Fuso orario (default: Europe/Rome)

Il job viene schedulato automaticamente quando salvi i settings o attivi il plugin.

## 🎯 Cosa fa

**Elimina**: File Excel, CSV, PDF, immagini e qualsiasi altro file temporaneo  
**Preserva**: Tutti i file `.json` (tools_status.json, user_status.json, tags.json, ecc.)

## 📊 Logging

Tutte le operazioni sono tracciate nei log del Cat con dettagli su file eliminati, preservati ed eventuali errori.

---

**Autore**: Elio Errico | [GitHub](https://github.com/ElioErrico)  
