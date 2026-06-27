from dataclasses import dataclass, field
from model.piazzamento import Piazzamento


@dataclass
class Circuit:
    circuitId: int
    circuitRef: str
    name: str
    location: str
    country: str
    lat: float
    lng: float
    alt: int
    url: str

    # CONSEGNA ii): Dizionario { anno: [Piazzamento1, Piazzamento2, ...] }
    # Inizializzato vuoto in modo sicuro per le dataclass
    #B. Il custode della memoria (field(default_factory=dict))
    #Questa è una regola fondamentale di Python che devi memorizzare per l'esame.
    # Nelle @dataclass, non è permesso impostare un valore di default mutabile direttamente con le parentesi graffe (es. gare_dettaglio: dict = {}).
    #Se lo facessi, Python commetterebbe un errore gravissimo chiamato Shared Mutable Default:
    # creerebbe un unico dizionario nella memoria e tutti i circuiti del tuo programma condividerebbero lo stesso identico dizionario. Inserendo i dati di Monza, ti ritroveresti gli stessi dati anche dentro Silverstone!
    #Scrivendo field(default_factory=dict), ordini a Python:
    # "Ogni volta che istanzio un nuovo circuito dal database, chiama la funzione costruttrice dict() e assegna a quel circuito un dizionario nuovo, vuoto e totalmente indipendente dagli altri".

    gare_dettaglio: dict[int, list[Piazzamento]] = field(default_factory=dict)

    def __eq__(self, other):
        if not isinstance(other, Circuit):
            return False
        return self.circuitId == other.circuitId

    def __hash__(self):
        return hash(self.circuitId)

    def __str__(self):
        return f"{self.name} ({self.location})"