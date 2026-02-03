# Domyślne zadanie, wyświetla pomoc
help:
	@echo "Dostępne komendy:"
	@echo "  make scrape        - Uruchamia proces scrapowania i zapisywania leadów do bazy danych."
	@echo "  make sync-status   - Wyświetla czas od ostatniej synchronizacji dla każdej grupy."
	@echo "  make send-messages - Wysyła wiadomości do leadów z ostatniego dnia."
	@echo "  make list-messages - Wyświetla listę wiadomości wysłanych w ostatnim dniu."
	@echo "  make setup         - Instaluje zależności projektu."

# Uruchamia skrypt do scrapowania
scrape:
	@echo "Uruchamianie skryptu scrapującego..."
	uv run src/scripts/scrape_posts.py

# Uruchamia skrypt do wysyłania wiadomości
send-messages:
	@echo "Uruchamianie skryptu do wysyłania wiadomości..."
	uv run src/scripts/send_messages.py

# Uruchamia skrypt do listowania wiadomości
list:
	@echo "Uruchamianie skryptu do listowania wiadomości..."
	uv run src/scripts/list_posts.py

# Instaluje zależności
setup:
	@echo "Instalowanie zależności..."
	uv sync

.PHONY: help scrape send-messages list-messages setup classify sync-status

# Uruchamia skrypt do klasyfikacji postów
classify:
	@echo "Uruchamianie skryptu do klasyfikacji postów..."
	uv run src/scripts/classify_posts.py

# Uruchamia skrypt do sprawdzania czasu od ostatniej synchronizacji
sync-status:
	@echo "Sprawdzanie czasu od ostatniej synchronizacji grup..."
	uv run src/scripts/sync_time_checker.py
