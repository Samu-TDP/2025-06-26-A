import networkx as nx
from database.DAO import DAO
from model.piazzamento import Piazzamento


class Model:
    def __init__(self):
        """
        COSTRUTTORE DEL MODEL: Inizializza le strutture dati fondamentali nella RAM.
        - self._grafo: Contenitore del grafo semplice, pesato e NON orientato (nx.Graph).
        - self._idMap: Dizionario di supporto per recuperare un oggetto Circuito partendo dal suo ID.
        """
        # CONSEGNA PUNTO 1.2: 'costruire un grafo semplice e pesato' (non orientato)
        self._grafo = nx.Graph()

        # Struttura di indicizzazione rapida { circuitId: Oggetto_Circuit }
        self._idMap = {}

        # VARIABILI DI STATO PER LA RICORSIONE (PUNTO 2)
        self._best_soluzione = []  # Conterrà la lista ottima di oggetti Circuit del Dream Championship
        self._best_imprevedibilita = 0.0  # Conterrà il punteggio massimo di imprevedibilità totale

    def crea_grafo(self, year_start, year_end):
        """
        Nel motore principale si applica il pattern a 5 step per l'allestimento del sistema.
        Mappa le consegne: PUNTO 1.2.a (Nodi in 2 step) e PUNTO 1.2.b (Archi e pesi).
        """
        # --- STEP 1: RESET DELLE STRUTTURE ---
        # Pulisce la memoria per consentire più click consecutivi con anni differenti
        self._grafo.clear()
        self._idMap.clear()

        # --- STEP 2: CARICAMENTO NODI ED ESECUZIONE SECONDO STEP (Query per Nodo) ---
        # Chiamiamo la prima query del DAO: estrae tutti i 73 circuiti storici
        circuiti_totali = DAO.get_tutti_circuiti()

        for circuito in circuiti_totali:
            # Memorizziamo il circuito nella mappa per la traduzione degli ID
            self._idMap[circuito.circuitId] = circuito

            # CONSEGNA ii): 'soluzione in due step: query (per nodo) per ottenere i dettagli'
            # Interroghiamo la seconda query passando l'ID di questo circuito e il range di anni scelto
            righe_piazzamenti = DAO.get_piazzamenti_circuito(circuito.circuitId, year_start, year_end)

            for riga in righe_piazzamenti:
                anno_gara = riga["year"]
                # Istanziamo l'oggetto Piazzamento preferibile richiesto dalla traccia
                nuovo_piazzamento = Piazzamento(driverId=riga["driverId"], position=riga["position"])

                # PATTERN DI INNESTAMENTO: Se l'anno non esiste nel dizionario del circuito, lo creiamo
                if anno_gara not in circuito.gare_dettaglio:
                    circuito.gare_dettaglio[anno_gara] = []

                # Appendiamo l'oggetto alla lista dei piazzamenti di quell'anno specifico
                circuito.gare_dettaglio[anno_gara].append(nuovo_piazzamento)

            # Aggiungiamo ufficialmente il circuito come vertice indipendente nel grafo
            self._grafo.add_node(circuito)

        # --- STEP 3 & 4: ESTRAZIONE DELLE RELAZIONI E DELLE STATISTICHE ---
        # Chiediamo al DAO le coppie uniche che hanno corso nel range e la mappa dei piloti finiti
        coppie_valide = DAO.get_coppie_circuiti(year_start, year_end)
        mappa_piloti_finiti = DAO.get_piloti_finiti_per_circuito(year_start, year_end)

        # --- STEP 5: LOGICA DI BUSINESS PER LA CREAZIONE DEGLI ARCHI ---
        for coppia in coppie_valide:
            # Controllo difensivo: verifichiamo che entrambi i circuiti esistano nella nostra mappa
            if coppia.id1 in self._idMap and coppia.id2 in self._idMap:
                nodo_A = self._idMap[coppia.id1]
                nodo_B = self._idMap[coppia.id2]

                # CONSEGNA PUNTO 1.2.b: 'Il peso è la somma del numero di piloti che hanno tagliato il traguardo'
                # Recuperiamo dal dizionario quanti piloti sono arrivati alla fine per entrambi i circuiti
                finiti_A = mappa_piloti_finiti.get(coppia.id1, 0)
                finiti_B = mappa_piloti_finiti.get(coppia.id2, 0)

                peso_arco = finiti_A + finiti_B

                # Creiamo la connessione fisica nel grafo non orientato impostando il parametro weight
                self._grafo.add_edge(nodo_A, nodo_B, weight=peso_arco)

    # =========================================================================
    # METODI DI INTERROGAZIONE GRAFO (PUNTO 1.3)
    # =========================================================================

    def get_num_nodi(self):
        """Ritorna il conteggio totale dei vertici inseriti nel grafo."""
        return self._grafo.number_of_nodes()

    def get_num_archi(self):
        """Ritorna il conteggio totale delle connessioni generate."""
        return self._grafo.number_of_edges()

    def get_dettagli_componente_maggiore(self):
        """
        CONSEGNA PUNTO 1.3: 'identificare la componente connessa di dimensione maggiore,
        e stamparne tutti i nodi, ordinati in senso decrescente di peso massimo degli archi incidenti.'
        """
        # 1. Estraiamo tutte le componenti connesse del grafo come lista di insiemi (set)
        componenti = list(nx.connected_components(self._grafo))

        if not componenti:
            return []

        # 2. Individuiamo l'insieme più grande applicando la funzione max basata sulla lunghezza (len)
        comp_maggiore_set = max(componenti, key=len)

        # 3. Trasformiamo il set in una lista modificabile per poter applicare l'ordinamento personalizzato
        lista_nodi_ordinati = list(comp_maggiore_set)

        # 4. Ordiniamo la lista applicando una funzione lambda basata sul peso massimo degli archi incidenti
        lista_nodi_ordinati.sort(key=lambda nodo: self._get_peso_massimo_incidente(nodo), reverse=True)

        return lista_nodi_ordinati

    def _get_peso_massimo_incidente(self, nodo):
        """
        FUNZIONE DI SUPPORTO: Calcola il valore massimo del peso tra tutti gli archi che toccano il nodo.
        """
        peso_massimo = 0
        # self._grafo.edges(nodo, data=True) estrae tutti gli archi collegati direttamente a questo vertice
        for u, v, attributi in self._grafo.edges(nodo, data=True):
            valore_peso = attributi['weight']
            if valore_peso > peso_massimo:
                peso_massimo = valore_peso
        return peso_massimo

    # =========================================================================
    # ALGORITMO DI RICORSIONE / BACKTRACKING (PUNTO 2)
    # =========================================================================

    def cerca_dream_championship(self, K, M):
        """
        FUNZIONE INTERRUTTORE: Filtra i nodi ammissibili, resetta i record e avvia la ricorsione.
        Mappa le consegne del PUNTO 2 (Sotto-campionato di K gare ed M edizioni).
        """
        # 1. RESET DEI RECORD GLOBALI
        self._best_soluzione = []
        self._best_imprevedibilita = 0.0

        # 2. INDIVIDUAZIONE DEI CIRCUITI VALIDI
        # Recuperiamo la componente connessa maggiore (lista di nodi) dal punto precedente
        nodi_comp_maggiore = self.get_dettagli_componente_maggiore()
        circuiti_ammissibili = []

        for circuito in nodi_comp_maggiore:
            # CONSEGNA: 'nei quali si è corso almeno M volte nel range di anni selezionato'
            # Il numero di edizioni corse corrisponde al numero di chiavi (anni) presenti in gare_dettaglio
            edizioni_corse = len(circuito.gare_dettaglio)

            if edizioni_corse >= M:
                circuiti_ammissibili.append(circuito)

        # 3. AVVIO MOTORE RICORSIVO (Combinazioni semplici di dimensione K)
        # Passiamo la lista parziale vuota, i candidati validi, la dimensione K e l'indice di partenza (0)
        self._backtracking(parziale=[], candidati=circuiti_ammissibili, K=K, start_index=0)

        return self._best_soluzione, self._best_imprevedibilita

    def _backtracking(self, parziale, candidati, K, start_index):
        """
        IL MOTORE RICORSIVO: Esplora in profondità tutte le combinazioni di dimensione K.
        Usa lo start_index per evitare di calcolare permutazioni ridondanti (es. [A, B] e [B, A]).
        """
        # BASE CASE (CONDIZIONE DI TERMINAZIONE): Abbiamo raggiunto la dimensione K di gare richiesta?
        if len(parziale) == K:
            # Calcoliamo l'indice di imprevedibilità complessivo della combinazione attuale
            imprevedibilita_attuale = self._calcola_imprevedibilita_totale(parziale)

            # Se è migliore del record precedente, aggiorniamo il medagliere
            if imprevedibilita_attuale > self._best_imprevedibilita:
                self._best_imprevedibilita = imprevedibilita_attuale
                # Facciamo una copia fisica della lista per metterla in cassaforte (Fotografia)
                self._best_soluzione = list(parziale)
            return  # Interrompe questo ramo e torna indietro

        # CICLO DI ESPLORAZIONE: Scorriamo i candidati partendo da start_index per evitare doppioni strutturali
        for i in range(start_index, len(candidati)):
            scelta = candidati[i]

            # LA SACRA TRINITÀ DELLA RICORSIONE
            parziale.append(scelta)  # 1. DO: Inserisco la gara in valigia
            self._backtracking(parziale, candidati, K,
                               start_index=i + 1)  # 2. RECURSION: Avanzo passando i + 1 come prossimo inizio
            parziale.pop()  # 3. UNDO: Tolgo la gara per testare le altre combinazioni

    def _calcola_imprevedibilita_totale(self, lista_circuiti):
        """
        Calcola la somma degli indici di imprevedibilità dei circuiti inseriti nella lista.
        Mappa la formula del testo: I = 1 - nP / nP_tot
        """
        somma_indici = 0.0

        for circuito in lista_circuiti:
            nP = 0  # Contatore piloti che hanno correttamente tagliato il traguardo
            nP_tot = 0  # Contatore totale degli iscritti indipendentemente dai ritiri

            # Esaminiamo la struttura nidificata del circuito per gli anni considerati
            for anno in circuito.gare_dettaglio:
                lista_piazzamenti = circuito.gare_dettaglio[anno]

                # nP_tot accumula la lunghezza totale di tutte le liste di posizionamento
                nP_tot += len(lista_piazzamenti)

                # nP conta quanti oggetti Piazzamento hanno un valore di 'position' valido (non Null)
                for p in lista_piazzamenti:
                    if p.position is not None:
                        nP += 1

            # Applicazione rigorosa della formula matematica descritta al Punto 2
            if nP_tot > 0:
                indice_I = 1.0 - (nP / nP_tot)
                somma_indici += indice_I

        return somma_indici