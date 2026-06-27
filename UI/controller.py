import flet as ft
from database.DAO import DAO  # Necessario per la funzione iniziale di popolamento degli anni


class Controller:
    def __init__(self, view, model):
        """
        COSTRUTTORE DEL CONTROLLER: Collega i tre pilastri dell'architettura MVC.
        - self._view: Riferimento all'interfaccia grafica per leggere e scrivere.
        - self._model: Riferimento al motore logico (grafo e algoritmi ricorsivi).
        """
        self._view = view
        self._model = model

    # =========================================================================
    # PATTERN LOGICO 1: INIZIALIZZAZIONE INTERFACCIA (fillDDsYear)
    # CONSEGNA: PUNTO 1.1 -> 'I menù dovranno essere riempiti interrogando il database'
    # =========================================================================
    def fillDDsYear(self):
        """
        Viene chiamato all'avvio dell'applicazione (nel main.py dopo l'inizializzazione).
        Scarica gli anni dal DB e popola simmetricamente i dropdown della View.
        """
        # 1. Chiamata diretta al DAO per ottenere la lista di anni interi unici
        anni_campionato = DAO.get_all_years()

        # 2. SVUOTAMENTO DI SICUREZZA: Previene duplicazioni in caso di chiamate multiple
        self._view._ddYear1.options.clear()
        self._view._ddYear2.options.clear()

        # 3. POPOLAMENTO: Iteriamo sugli anni e creiamo gli oggetti ft.dropdown.Option
        for anno in anni_campionato:
            # Nota d'esame: Flet richiede obbligatoriamente che la 'key' sia una stringa (str)
            opzione = ft.dropdown.Option(key=str(anno), text=f"Anno {anno}")

            # Aggiungiamo la stessa opzione a entrambi i menu (Inizio e Fine range)
            self._view._ddYear1.options.append(opzione)
            # Creiamo un duplicato per la seconda tendina per evitare conflitti di puntamento in memoria
            self._view._ddYear2.options.append(ft.dropdown.Option(key=str(anno), text=f"Anno {anno}"))

        # 4. AGGIORNAMENTO GRAFICO: Rende visibili le opzioni appena inserite
        self._view.update_page()

    # =========================================================================
    # PATTERN LOGICO 2: GESTIONE CREAZIONE GRAFO (handleBuildGraph)
    # CONSEGNA: PUNTO 1.2 -> Click sul tasto 'Crea grafo'
    # =========================================================================
    def handleBuildGraph(self, e):
        """
        Metodo attivato dal click su self._btnBuildGraph.
        Prende gli anni inseriti, valida il range, comanda il Model e stampa i dati statici.
        """
        # --- STEP 1: PULIZIA COMPLETA DELL'AREA DI STAMPA 1 ---
        self._view._txtGraphDetails.controls.clear()

        # --- STEP 2: SCUDO DIFENSIVO E VALIDAZIONE INPUT (TENDINE) ---
        anno1_str = self._view._ddYear1.value
        anno2_str = self._view._ddYear2.value

        # Controllo bloccante salvavita: l'utente ha saltato una o entrambe le tendine?
        if anno1_str is None or anno2_str is None:
            self._view.create_alert("Attenzione: Selezionare sia l'anno di inizio che l'anno di fine range.")
            return  # Blocca l'esecuzione ed evita un crash nel casting a int

        # --- STEP 3: CALCOLO DEI LIMITI DEL RANGE (A prova di distrazione dell'utente) ---
        anno1_int = int(anno1_str)
        anno2_int = int(anno2_str)

        # Utilizziamo min() e max() in modo che, anche se l'utente inverte l'ordine nelle tendine,
        # year_start sarà sempre il più piccolo e year_end il più grande, raddrizzando l'input.
        year_start = min(anno1_int, anno2_int)
        year_end = max(anno1_int, anno2_int)

        # --- STEP 4: DELEGA LOGICA AL MODEL ---
        # Ordiniamo al cervello dell'app di costruire il grafo NetworkX nella RAM
        self._model.crea_grafo(year_start, year_end)

        # --- STEP 5: ESTRAZIONE RISULTATI E STAMPA A SCHERMO ---
        tot_nodi = self._model.get_num_nodi()
        tot_archi = self._model.get_num_archi()

        # Prepariamo i controlli di testo da visualizzare nella ListView corretta (_txtGraphDetails)
        self._view._txtGraphDetails.controls.append(
            ft.Text("Grafo correttamente creato.", color="green", weight="bold", size=16)
        )
        self._view._txtGraphDetails.controls.append(
            ft.Text(f"Il grafo contiene {tot_nodi} nodi e {tot_archi} archi.")
        )

        # --- STEP 6: AGGIORNAMENTO DELLA PAGINA ---
        self._view.update_page()

    # =========================================================================
    # PATTERN LOGICO 3: DETTAGLI COMPONENTE CONNESSA (handlePrintDetails)
    # CONSEGNA: PUNTO 1.3 -> Click sul tasto 'Stampa dettagli'
    # =========================================================================
    def handlePrintDetails(self, e):
        """
        Metodo attivato dal click su self._btnPrintDetails.
        Estrae la componente connessa maggiore dal Model e la stampa ordinata secondo i vincoli.
        """
        # --- STEP 1: PULIZIA INIZIALE ---
        self._view._txtGraphDetails.controls.clear()

        # --- STEP 2: SCUDO DIFENSIVO SULLA PRESENZA DEL GRAFO ---
        # Se l'utente clicca 'Stampa dettagli' prima di aver creato il grafo, l'app fallirebbe.
        if self._model.get_num_nodi() == 0:
            self._view.create_alert("Errore: Generare prima il grafo cliccando su 'Crea grafo'.")
            return

        # --- STEP 3: DELEGA LOGICA AL MODEL ---
        # Riceviamo una lista di oggetti Circuit ordinati in modo decrescente per peso massimo incidente
        nodi_ordinati_componente = self._model.get_dettagli_componente_maggiore()

        # --- STEP 4: IMPAGINAZIONE GRAFICA DEI RISULTATI ---
        self._view._txtGraphDetails.controls.append(
            ft.Text(
                f"Componente connessa di dimensione maggiore rilevata! Contiene {len(nodi_ordinati_componente)} circuiti.",
                color="blue", weight="bold")
        )
        self._view._txtGraphDetails.controls.append(
            ft.Text("Elenco dei circuiti (ordinati per peso massimo degli archi incidenti decrescente):", italic=True)
        )

        # Scorriamo la lista di oggetti promossi e stampiamo i dettagli richiesti
        for circuito in nodi_ordinati_componente:
            # Calcoliamo al volo il peso massimo incidente per questo circuito richiamando la funzione del Model
            peso_max_incidente = self._model._get_peso_massimo_incidente(circuito)

            # Stampiamo il nome del circuito e il suo peso massimo associato, rispettando gli screen d'esempio
            self._view._txtGraphDetails.controls.append(
                ft.Text(f"- {circuito.name} | Peso max arco incidente: {peso_max_incidente}")
            )

        # --- STEP 5: AGGIORNAMENTO DELLA PAGINA ---
        self._view.update_page()

    # =========================================================================
    # PATTERN LOGICO 4: RICORSIONE E SOLUZIONE OTTIMA (handleCercaDreamChampionship)
    # CONSEGNA: PUNTO 2 -> Click sul tasto 'Cerca Dream Championship'
    # =========================================================================
    def handleCercaDreamChampionship(self, e):
        """
        Metodo attivato dal click su self._btnCalcolaSoluzione.
        Prende i valori testuali di K ed M, li valida difensivamente, lancia il backtracking e stampa nella ListView 2.
        """
        # --- STEP 1: PULIZIA DELLA SECONDA LISTVIEW IN FONDO ---
        self._view._txt_result.controls.clear()

        # --- STEP 2: SCUDO DIFENSIVO PREVENTIVO SUL GRAFO ---
        if self._model.get_num_nodi() == 0:
            self._view.create_alert(
                "Errore: È necessario creare il grafo e stampare i dettagli prima di cercare il Dream Championship.")
            return

        # --- STEP 3: ACQUISIZIONE E VALIDAZIONE NUMERICA ROBUSTA (TRY-EXCEPT) ---
        soglia_K_str = self._view._txtInSoglia.value
        edizioni_M_str = self._view._txtInNumDiEdizioni.value

        # Scudo contro i campi lasciati totalmente bianchi
        if not soglia_K_str or not edizioni_M_str:
            self._view.create_alert("Errore: Inserire sia il valore della Soglia (K) sia il Num di Edizioni (M).")
            return

        try:
            # Proviamo a convertire i testi dei TextField in numeri interi puri
            K = int(soglia_K_str)
            M = int(edizioni_M_str)

            # Controllo di buon senso matematico: l'utente ha inserito numeri positivi o sensati?
            if K <= 0 or M <= 0:
                self._view.create_alert(
                    "Errore: I valori di K ed M devono essere numeri interi strettamente maggiori di zero.")
                return
        except ValueError:
            # Se l'utente ha inserito lettere o caratteri speciali (es. "abc"), il casting fallisce.
            # Il blocco catch cattura l'eccezione impedendo il crash dell'app e informando l'utente.
            self._view.create_alert(
                "Errore di inserimento: I campi 'Soglia' e 'Num di Edizioni' accettano solo numeri interi.")
            return

        # --- STEP 4: MESSAGGIO DI ATTESA USER EXPERIENCE ---
        self._view._txt_result.controls.append(
            ft.Text("Elaborazione ricorsiva esaustiva in corso... Attendere.", color="orange", italic=True)
        )
        self._view.update_page()

        # --- STEP 5: DELEGA LOGICA AL MOTORE DI BACKTRACKING ---
        # Eseguiamo la ricerca globale delle combinazioni ottime.
        # Il metodo restituisce la lista di oggetti Circuit e il float dell'imprevedibilità massima.
        cammino_ottimo, max_imprevedibilita = self._model.cerca_dream_championship(K, M)

        # --- STEP 6: IMPAGINAZIONE FINALE NELLA LISTVIEW RISULTATI ---
        self._view._txt_result.controls.clear()  # Cancelliamo la scritta provvisoria "In corso..."

        # Validazione del risultato ritornato: l'algoritmo ha trovato combinazioni ammissibili?
        if not cammino_ottimo:
            self._view._txt_result.controls.append(
                ft.Text(
                    "Nessun sotto-campionato ammissibile trovato per i criteri di K ed M inseriti. Provare a ridurre M.",
                    color="red", weight="bold")
            )
        else:
            self._view._txt_result.controls.append(
                ft.Text(f"Sotto-campionato ideale individuato con successo!", color="green", weight="bold", size=16)
            )
            # Arrotondiamo il valore dell'indice complessivo a 4 cifre decimali per pulizia visiva
            self._view._txt_result.controls.append(
                ft.Text(f"Indice complessivo di imprevedibilità totale: {round(max_imprevedibilita, 4)}",
                        weight="bold", color="blue")
            )
            self._view._txt_result.controls.append(
                ft.Text(f"Elenco delle {len(cammino_ottimo)} gare che compongono il Dream Championship:"))

            # Scorriamo la lista di oggetti Circuit della soluzione ottima ed impaginiamo i nomi delle tappe
            for indice, circuito in enumerate(cammino_ottimo):
                # calcoliamo al volo l'indice I specifico per questo singolo circuito per arricchire la stampa
                # Passiamo una lista contenente il singolo circuito alla funzione del model per isolarne il punteggio
                indice_singolo = self._model._calcola_imprevedibilita_totale([circuito])

                self._view._txt_result.controls.append(
                    ft.Text(
                        f"  Gara {indice + 1}: {circuito.name} ({circuito.location}, {circuito.country}) | Imprevedibilità locale: {round(indice_singolo, 4)}")
                )

        # --- STEP 7: AGGIORNAMENTO CONCLUSIVO DELLO SCHERMO ---
        self._view.update_page()


