from dataclasses import dataclass

@dataclass
class Piazzamento:
    """
    Rappresenta il singolo piazzamento di un pilota in una gara.
    Mappa i campi driverId e position della tabella 'results' come richiesto dal PDF.
    """
    driverId: int
    position: int

    def __str__(self):
        return f"Pilota: {self.driverId} -> Posizione: {self.position}"