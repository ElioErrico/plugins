# 🧠 Plugin Remember

Plugin per Cheshire Cat che memorizza informazioni nella memoria dichiarativa usando il comando `ricorda:` nella chat.

## 🎯 Caratteristiche

- **Comando naturale**: `ricorda: [testo]`
- **Titolo auto-generato**: L'LLM crea un titolo descrittivo per ogni memoria
- **Risposta immediata**: Usa `fast_reply` hook
- **Integrazione filter_and_upload**: Applica automaticamente i tag attivi
- **Notifiche real-time**: Feedback via WebSocket

## 🚀 Utilizzo

```
ricorda: il mio compleanno è il 15 marzo
```

Risposta:
```
✅ Ho memorizzato:

Compleanno 15 marzo

"il mio compleanno è il 15 marzo"

Questa informazione è stata salvata con i tuoi tag attivi.
```

## 🔧 Come Funziona

1. Intercetta comando `ricorda:`
2. L'LLM genera un titolo descrittivo (5 parole max)
3. Usa il chunker standard del Rabbit Hole sul testo della memoria
4. `rabbit_hole.store_documents()` salva i chunk risultanti
5. `filter_and_upload.py` applica tag attivi
6. Salvataggio in Qdrant con metadata completi
7. Risposta immediata all'utente

## 📊 Metadata Salvati

- `source`: Titolo auto-generato dall'LLM
- `type`: "manual_memory"
- `user_input`: true
- `created_at`: timestamp
- `file_path`: percorso del file `.txt` generato
- Tag attivi + user_id (da filter_and_upload)

## 🐛 Debug

```bash
tail -f logs/cat.log | grep "\[Remember Plugin\]"
```

---
