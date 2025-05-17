

# Movella DOT Recorder

Script Python per la registrazione di dati dai sensori **Movella DOT**, utilizzando il Movella DOT PC SDK. Permette di configurare, sincronizzare, loggare e visualizzare in tempo reale i dati di orientamento (Roll, Pitch, Yaw).

---

## PREREQUISITI

- Trovarsi su ambiente Ubuntu 22.04 LTS 64-bit

- Installare una versione Python compreso tra 3.7 e 3.10 (Per lo sviluppo è stata utilizzata la versione 3.10.12)

- Installare ed unzippare la SDK di movella da https://www.movella.com/supportsoftware-documentationhsCtaTracking=39d661fa-2ea8-4478-955e-01d0d8885f14%7C3ad1c7d6-9c3a-42e9-b424-5b15b9d0924e

- (opzionale) alcuni comandi potrebbero non funzionare quindi eseguire il comando:

        sudo apt update && sudo apt upgrade -y

---

## ISTRUZIONI INSTALLAZIONE

Istruzioni:
1. creare un virtual enviroment con il comando:  python3 -m venv nome_ambiente
	a) se non è installato il comando venv eseguire:
	  sudo apt update
	  sudo apt install python3-venv

2. attivare il virtual enviroment con il comando:
source nome_ambiente/bin/activate

3. una volta che ci si trova nel virtual enviroment installare il file movelladotpcsdk_linux-x64_2023.6.sh che si trova nella cartella dell’SDK installata all’inizio ed eseguire il comando:

        sudo “percorso_alla_cartella_dove_si_trova_il_file_unzippato/Movella DOT SDK_Linux/movelladot_pc_sdk_linux-x64_2023.6_b345_r124108/movelladot_pc_sdk_linux-x64_2023.6/movelladotpcsdk_linux-x64_2023.6.sh"

	a) potrebbe venire restituito l’errore “ 'uudecode' could not be found. It is usually installed with the 'sharutils' package”, allora eseguire il comando:
    
        sudo apt update && sudo apt install sharutils -y

	b) a questo punto verrà chiesta la cartella di installazione, se si preme invio senza inserire niente verrà installata nella cartella di default

	c) se l’installazione è andata a buon fine un messaggio simile a questo dovrebbe apparire:
	  
            #8-Ubuntu SMP PREEMPT_DYNAMIC Mon Sep 16 13:41:20 UTC 2024 Start using by 	  adding -L/usr/local/movella to your linker options Or register systemwide using 	  	  ldconfig /usr/local/movella

4. la guida consiglia di utilizzare il comando:

        sudo apt-get install build-essential curl cmake libgfortran4 libxcb-xkb-dev libcurl4-openssl-dev libbluetooth-dev 

ma questa versione non è più disponibile, quindi utilizzare i comandi:

    sudo apt-get install libgfortran5

    sudo apt-get install build-essential curl cmake libgfortran5 libxcb-xkb-dev libcurl4-openssl-dev libbluetooth-dev

5. a questo punto bisogna spostarsi all’ interno della cartella dove è stata scaricata l'sdk e successivamente nella cartella python, questi sono i file .whl che bisogna installare, a questo punto si può eseguire il comando per installare il .whl corrispondente alla versione di python utilizzata (nel nostro caso Python 3.10)
pip install movelladot_pc_sdk-2023.6.0-cp310-none-linux_x86_64.whl

6. a questo punto ci si può spostare nella cartella sdk/examples/xdpcsdk/python ed eseguire gli esempi.

	a) è consigliato eseguire il comando: 
    
        pip install -r requirements.txt


	b) per una migliore compatibilità tra le librerie e la sdk consiglio di installare queste versioni di pynput e numpy, con questi comandi:

	    pip install numpy==1.24.0
	    pip install pynput==1.7.3
---

## COMANDI DI BASE

Clona o posizionati nella cartella degli esempi Python

    cd sdk/examples/xdpcsdk/python/

Attiva il virtual env

    source nome_ambiente/bin/activate

Installa le dipendenze

    pip install -r requirements.txt

Esegui lo script

    python3 registration.py <filter_profile> <payload_mode> <duration> <output_rate> [show|noshow]

---
## ESEMPI
Con visualizzazione real-time

    python3 registration.py General custom4 10 30 show

Solo registrazione su file

    python3 registration.py Dynamic dq 15 20

---
## PARAMETRI

| Parametro        | Valori possibili                                                                                                                                                       | Descrizione                                                    |
|------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------|
| `filter_profile` | `General`, `Dynamic`                                                                                                                                                   | Profilo filtro da applicare                                    |
| `payload_mode`   | `custom1`, `custom2`, `custom3`, `custom4`, `custom5`,<br>`orientQuat`, `completeQuat`, `extQuat`,<br>`orientEul`, `completeEul`, `extEul`,<br>`freeAcc`,<br>`highFid`, `highFidMag`,<br>`dq`, `dqMag`,<br>`rq`, `rqMag`,<br>`mfm` | Modalità di payload dei dati                                   |
| `duration`       | intero ≥ 1                                                                                                                                                              | Durata della registrazione (secondi)                            |
| `output_rate`    | `1`, `4`, `10`, `12`, `15`, `20`, `30`, `60`, `120`                                                                                                                     | Frequenza di output dei dati (Hz)                              |
| `show`           | `show`, `noshow`                                                                                                                                                       | Se `show`, stampa roll/pitch/yaw in tempo reale; altrimenti silenzioso |

---

## FUNZIONALITA' IMPLEMENTATE

- Parsing dei parametri da linea di comando  
- Inizializzazione e connessione ai dispositivi Movella DOT via Bluetooth  
- Configurazione di filtro, output rate e opzioni di logging  
- Creazione automatica di cartella `logs/` e file CSV con nome `<device>_<timestamp>.csv`  
- Sincronizzazione multi-sensore (retry automatico, skip se un solo dispositivo)  
- Avvio e arresto della misura, disable logging al termine  
- Visualizzazione live di Roll, Pitch e Yaw durante la registrazione (`show`)  
- Logging su file CSV in background (`noshow`)  
- Loop interattivo per ripetere o modificare parametri senza riavviare lo script  
- Reset dell’heading e pulizia delle risorse garantiti in ogni condizione (try/finally)

---

## MODALITA' INTERATTIVA

Al termine di ogni ciclo di registrazione, lo script richiede all’utente:

- **`r`** → Ripetere la registrazione con gli stessi parametri  
- **`m`** → Modificare interattivamente  
  - `payload_mode`  
  - `duration`  
  - `output_rate`  
  - `show` / `noshow`  
- **`q`** → Uscire dallo script e avviare il reset e cleanup

---

## NOTE

- I file CSV generati vengono salvati in `logs/`, creata automaticamente all’avvio.  
- Se è connesso un solo dispositivo, la sincronizzazione viene saltata per evitare attese inutili.  
- In caso di fallimento del primo tentativo di sync viene eseguito un retry automatico.  
- Lo script esegue sempre il reset dell’heading e la `cleanup()` finale, anche in caso di interruzione o errore imprevisto.  
- Testato su Ubuntu 22.04, Python 3.10.12 e Movella DOT PC SDK 2023.6.0.  


