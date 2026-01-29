# Domyślne zadanie, wyświetla pomoc
help:
	@echo "Dostępne komendy:"
	@echo "  make scrape        - Uruchamia proces scrapowania i zapisywania leadów do bazy danych."
	@echo "  make send-messages - Wysyła wiadomości do leadów z ostatniego dnia."
	@echo "  make list-messages - Wyświetla listę wiadomości wysłanych w ostatnim dniu."
	@echo "  make setup         - Instaluje zależności projektu."

# Uruchamia skrypt do scrapowania
scrape:
	@echo "Uruchamianie skryptu scrapującego..."
	uv run src/scrape.py

# Uruchamia skrypt do wysyłania wiadomości
send-messages:
	@echo "Uruchamianie skryptu do wysyłania wiadomości..."
	uv run src/send_messages.py

# Uruchamia skrypt do listowania wiadomości
list:
	@echo "Uruchamianie skryptu do listowania wiadomości..."
	uv run src/list_posts.py

# Instaluje zależności
setup:
	@echo "Instalowanie zależności..."
	uv sync

.PHONY: help scrape send-messages list-messages setup
