from database.DB_connect import DBConnect
from model.circuito import Circuit
from dataclasses import dataclass

# =========================================================================
# DATA TRANSFER OBJECTS (DATACLASS DI TRASPORTO PER L'ESAME)
# =========================================================================

@dataclass
class CoppiaCircuiti:
    """
    Rappresenta la connessione grezza tra due nodi del grafo.
    Mappa la relazione: 'Entrambi i circuiti hanno ospitato la F1 nel range'.
    """
    id1: int
    id2: int

@dataclass
class StatisticaFiniti:
    """
    Rappresenta la componente fondamentale per il calcolo del peso dell'arco.
    Memorizza quanti piloti hanno completato la gara in un circuito nel range di anni.
    """
    circuitId: int
    n_finiti: int


class DAO():
    def __init__(self):
        pass

    @staticmethod
    def get_all_years():
        """
        Mappa la consegna: PUNTO 1.1 -> 'I menù dovranno essere riempiti interrogando
        il database per ottenere gli anni in cui è stato disputato il campionato.'

        COSA FA: Estrae l'elenco cronologico di tutti gli anni dei campionati di F1.
        """
        conn = DBConnect.get_connection()
        result = []
        # dictionary=True trasforma ogni riga restituita da SQL in un comodo dict di Python
        cursor = conn.cursor(dictionary=True)

        # SPIEGAZIONE QUERY: Selezioniamo gli anni senza duplicati (DISTINCT) dalla tabella races
        # e li ordiniamo in senso decrescente (dal più recente al più vecchio) per la UI.
        query = "SELECT DISTINCT year FROM races ORDER BY year DESC"

        cursor.execute(query)
        for row in cursor:
            # row["year"] accede direttamente alla colonna 'year' del record SQL
            result.append(row["year"])

        cursor.close()
        conn.close()
        return result

    @staticmethod
    def get_tutti_circuiti():
        """
        Mappa la consegna: PUNTO 1.2.a -> 'I nodi sono costituiti da tutti i circuiti
        su cui è mai stato disputato un gran premio di F1 indipendentemente dagli anni.'

        COSA FA: Estrae le anagrafiche complete dei 73 circuiti storici della Formula 1.
        """
        conn = DBConnect.get_connection()
        result = []
        cursor = conn.cursor(dictionary=True)

        # SPIEGAZIONE QUERY: Colleghiamo la tabella 'circuits' (c) alla tabella 'races' (r)
        # tramite la chiave circuitId. Usiamo DISTINCT per evitare che un circuito che ha ospitato
        # 50 gare venga estratto 50 volte. Estraiamo solo i circuiti che hanno almeno una gara associata.
        query = """
            SELECT DISTINCT c.* FROM circuits c, races r 
            WHERE c.circuitId = r.circuitId
        """

        cursor.execute(query)
        for row in cursor:
            # CREAZIONE DELL'OGGETTO CIRCUITO (Mappatura ER a Specchio):
            # Inseriamo una protezione per il campo 'alt' (altitude) che potrebbe essere NULL nel DB.
            altitudine_sicura = int(row["alt"]) if row["alt"] is not None else 0

            circuito = Circuit(
                circuitId=row["circuitId"],
                circuitRef=row["circuitRef"],
                name=row["name"],
                location=row["location"],
                country=row["country"],
                lat=row["lat"],
                lng=row["lng"],
                alt=altitudine_sicura,
                url=row["url"],
                gare_dettaglio={}  # Inizializzato vuoto, verrà popolato nel secondo step dal Model
            )
            result.append(circuito)

        cursor.close()
        conn.close()
        return result

    @staticmethod
    def get_piazzamenti_circuito(circuit_id, year_start, year_end):
        """
        Mappa la consegna: PUNTO 1.2.a.ii -> 'Soluzione in due step: query (per nodo)
        per ottenere i dettagli dei piazzamenti (campi driverId e position) nel range selezionato.'

        COSA FA: Per un singolo circuito specifico, scarica l'anno, l'id del pilota e il suo piazzamento.
        """
        conn = DBConnect.get_connection()
        result = []
        cursor = conn.cursor(dictionary=True)

        # SPIEGAZIONE QUERY: Uniamo le gare (races) ai loro risultati dettagliati (results)
        # tramite la chiave primaria/esterna raceId.
        # Applichiamo tre filtri cruciali nella clausola WHERE:
        # 1. Filtriamo per il circuito specifico richiesto dal ciclo (%s) -> r.circuitId = %s
        # 2. Isolianto il range temporale richiesto dall'utente (estremi inclusi) -> BETWEEN %s AND %s
        query = """
            SELECT r.year, res.driverId, res.position
            FROM races r, results res
            WHERE r.raceId = res.raceId
            AND r.circuitId = %s
            AND r.year BETWEEN %s AND %s
            ORDER BY r.year ASC, res.position ASC
        """

        # Passiamo la tupla dei parametri nell'ordine esatto dei segnaposto %s
        cursor.execute(query, (circuit_id, year_start, year_end))
        for row in cursor:
            # Restituiamo un dizionario leggero con i dati pronti per essere trasformati
            # in oggetti di tipo 'Piazzamento' all'interno del Model.
            # Nota: row["position"] viene estratto così com'è (sarà None se il pilota si è ritirato/squalificato)
            result.append({
                "year": row["year"],
                "driverId": row["driverId"],
                "position": row["position"]
            })

        cursor.close()
        conn.close()
        return result

    # =========================================================================
    # NUOVI METODI IMPLEMENTATI PER GLI ARCHI ED I PESI (PUNTO 1.2.b)
    # =========================================================================

    @staticmethod
    def get_coppie_circuiti(year_start, year_end):
        """
        CONSEGNA: PUNTO 1.2.b -> 'Due nodi sono connessi se ed solo se entrambi
        i circuiti hanno ospitato la F1 almeno per un anno nel range selezionato.'

        COSA FA: Trova matematicamente le coppie uniche di circuiti che soddisfano il vincolo.
        """
        conn = DBConnect.get_connection()
        result = []
        cursor = conn.cursor(dictionary=True)

        # SINTASSI SQL SPIEGATA:
        # Facciamo un Self-Join sdoppiando la tabella 'races' in due alias r1 ed r2.
        # Vincoliamo entrambe le tabelle a cercare gare comprese nel range stabilito.
        # Il filtro r1.circuitId > r2.circuitId evita le auto-connessioni (Monza con Monza)
        # e garantisce l'anti-doppione simmetrico (se estraggo A-B, scarto B-A).
        query = """
                SELECT DISTINCT r1.circuitId AS id1, r2.circuitId AS id2
                FROM races r1, races r2
                WHERE r1.year BETWEEN %s AND %s
                AND r2.year BETWEEN %s AND %s
                AND r1.circuitId > r2.circuitId
            """

        cursor.execute(query, (year_start, year_end, year_start, year_end))
        for row in cursor:
            # Incapsuliamo i due ID estratti nella nostra dataclass di trasporto
            result.append(CoppiaCircuiti(
                id1=row["id1"],
                id2=row["id2"]
            ))

        cursor.close()
        conn.close()
        return result

    @staticmethod
    def get_piloti_finiti_per_circuito(year_start, year_end):
        """
        CONSEGNA: PUNTO 1.2.b -> 'Il peso è pari alla somma del numero di piloti che
        hanno correttamente tagliato il traguardo nei vari anni... Se tale valore è Null,
        vuol dire che si è ritirato/squalificato e non va considerato'.

        COSA FA: Calcola preventivamente per ogni circuito quanti piloti hanno concluso la gara.
        """
        conn = DBConnect.get_connection()
        result = {}  # Usiamo un dizionario { circuitId: numero_finiti } per un accesso fulmineo
        cursor = conn.cursor(dictionary=True)

        # SINTASSI SQL SPIEGATA:
        # Colleghiamo le gare ('races' r) ai risultati ('results' res) tramite la chiave raceId.
        # Applichiamo il filtro temporale richiesto dall'utente (BETWEEN).
        # APPLICHIAMO LO SCUDO PER I RITIRATI: res.position IS NOT NULL esclude automaticamente
        # tutti i piloti che non hanno concluso la gara, rispettando alla lettera il testo.
        # GROUP BY r.circuitId raggruppa i dati per circuito e COUNT(res.driverId) conta le righe promosse.
        query = """
                SELECT r.circuitId, COUNT(res.driverId) AS numero_finiti
                FROM races r, results res
                WHERE r.raceId = res.raceId
                AND res.position IS NOT NULL
                AND r.year BETWEEN %s AND %s
                GROUP BY r.circuitId
            """

        cursor.execute(query, (year_start, year_end))
        for row in cursor:
            # Salviamo nel dizionario: come chiave l'ID del circuito, come valore il conteggio numerico
            result[row["circuitId"]] = int(row["numero_finiti"])

        cursor.close()
        conn.close()
        return result

