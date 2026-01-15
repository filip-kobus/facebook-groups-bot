.PHONY: help install setup run clean clean-all test lint format check

# Default target
.DEFAULT_GOAL := help

# Colors for output
RED=\033[0;31m
GREEN=\033[0;32m
YELLOW=\033[1;33m
BLUE=\033[0;34m
NC=\033[0m # No Color

# Python and virtual environment
PYTHON := python3
VENV := .venv
VENV_BIN := $(VENV)/bin
PYTHON_VENV := $(VENV_BIN)/python
PIP := $(VENV_BIN)/pip

help: ## Show this help message
	@echo "$(BLUE)Facebook Groups Bot - Available Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Quick Start:$(NC)"
	@echo "  1. make setup     - First time setup"
	@echo "  2. make run       - Run the bot"
	@echo ""

setup: ## Complete first-time setup (venv + dependencies + playwright)
	@echo "$(BLUE)Setting up Facebook Groups Bot...$(NC)"
	@$(PYTHON) -m venv $(VENV)
	@echo "$(GREEN)✓ Virtual environment created$(NC)"
	@$(PIP) install --upgrade pip
	@$(PIP) install -e .
	@echo "$(GREEN)✓ Dependencies installed$(NC)"
	@$(VENV_BIN)/playwright install chromium
	@echo "$(GREEN)✓ Playwright browser installed$(NC)"
	@mkdir -p logs
	@echo "$(GREEN)✓ Logs directory created$(NC)"
	@echo ""
	@echo "$(GREEN)✓ Setup complete!$(NC)"
	@echo "$(YELLOW)Next step: Create .env file with your credentials$(NC)"
	@echo "  EMAIL=your_email@example.com"
	@echo "  PASSWORD=your_password"
	@echo ""
	@echo "Then run: $(GREEN)make run$(NC)"

install: ## Install/update dependencies only
	@echo "$(BLUE)Installing dependencies...$(NC)"
	@$(PIP) install --upgrade pip
	@$(PIP) install -e .
	@echo "$(GREEN)✓ Dependencies installed$(NC)"

playwright: ## Install/reinstall Playwright browsers
	@echo "$(BLUE)Installing Playwright browsers...$(NC)"
	@$(VENV_BIN)/playwright install chromium
	@echo "$(GREEN)✓ Playwright browsers installed$(NC)"

run: ## Run the Facebook groups bot
	@mkdir -p logs
	@echo "$(BLUE)Starting Facebook Groups Bot...$(NC)"
	@echo "$(YELLOW)Thinking time scale: Check config.py (THINKING_TIME_SCALE)$(NC)"
	@$(PYTHON_VENV) -m src.main

run-fast: ## Run with thinking time scale = 0 (fastest)
	@mkdir -p logs
	@echo "$(BLUE)Starting bot in FAST mode (no thinking delay)...$(NC)"
	@sed -i 's/THINKING_TIME_SCALE = .*/THINKING_TIME_SCALE = 0/' config.py
	@$(PYTHON_VENV) -m src.main

run-normal: ## Run with thinking time scale = 5 (balanced)
	@mkdir -p logs
	@echo "$(BLUE)Starting bot in NORMAL mode (2.5s thinking delay)...$(NC)"
	@sed -i 's/THINKING_TIME_SCALE = .*/THINKING_TIME_SCALE = 5/' config.py
	@$(PYTHON_VENV) -m src.main

run-safe: ## Run with thinking time scale = 10 (safest)
	@mkdir -p logs
	@echo "$(BLUE)Starting bot in SAFE mode (5s thinking delay)...$(NC)"
	@sed -i 's/THINKING_TIME_SCALE = .*/THINKING_TIME_SCALE = 10/' config.py
	@$(PYTHON_VENV) -m src.main

clean: ## Clean Python cache files
	@echo "$(BLUE)Cleaning cache files...$(NC)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@rm -f leads.csv 2>/dev/null || true
	@echo "$(GREEN)✓ Cache cleaned$(NC)"

clean-logs: ## Clean old log files (keeps last 7 days)
	@echo "$(BLUE)Cleaning old logs...$(NC)"
	@find logs -name "bot_*.log" -type f -mtime +7 -delete 2>/dev/null || true
	@echo "$(GREEN)✓ Old logs cleaned$(NC)"

clean-all: clean ## Clean everything including venv
	@echo "$(YELLOW)Removing virtual environment...$(NC)"
	@rm -rf $(VENV)
	@echo "$(GREEN)✓ Complete cleanup done$(NC)"

check-env: ## Check if .env file exists
	@if [ ! -f .env ]; then \
		echo "$(RED)✗ .env file not found!$(NC)"; \
		echo "$(YELLOW)Create .env with:$(NC)"; \
		echo "  EMAIL=your_email@example.com"; \
		echo "  PASSWORD=your_password"; \
		exit 1; \
	else \
		echo "$(GREEN)✓ .env file exists$(NC)"; \
	fi

check-cookies: ## Check if cookies.json exists
	@if [ -f cookies.json ]; then \
		echo "$(GREEN)✓ Saved cookies found (will skip login)$(NC)"; \
	else \
		echo "$(YELLOW)⚠ No saved cookies (will need to login)$(NC)"; \
	fi

status: check-env check-cookies ## Check bot status and configuration
	@echo ""
	@echo "$(BLUE)Current Configuration:$(NC)"
	@echo "  Thinking Time Scale: $$(grep 'THINKING_TIME_SCALE = ' config.py | awk '{print $$NF}')"
	@echo "  Days Back: $$(grep 'DAYS_BACK = ' config.py | awk '{print $$NF}')"
	@echo "  Max Scrolls: $$(grep 'MAX_SCROLLS = ' config.py | awk '{print $$NF}')"
	@echo ""

config: ## Open config.py for editing
	@$(EDITOR) config.py || nano config.py || vi config.py

logs: ## Show recent execution logs (if any)
	@echo "$(BLUE)Recent logs:$(NC)"
	@if [ -d logs ] && [ -n "$$(ls -A logs 2>/dev/null)" ]; then \
		tail -n 50 logs/bot_$$(date +%Y-%m-%d).log 2>/dev/null || \
		tail -n 50 logs/$$(ls -t logs/ | head -1) 2>/dev/null || \
		echo "$(YELLOW)No logs found$(NC)"; \
	else \
		echo "$(YELLOW)No logs directory or files found$(NC)"; \
	fi

logs-full: ## Show full today's log file
	@if [ -f logs/bot_$$(date +%Y-%m-%d).log ]; then \
		less logs/bot_$$(date +%Y-%m-%d).log; \
	else \
		echo "$(YELLOW)No log file for today$(NC)"; \
	fi

logs-errors: ## Show only ERROR level logs from today
	@if [ -f logs/bot_$$(date +%Y-%m-%d).log ]; then \
		grep "ERROR" logs/bot_$$(date +%Y-%m-%d).log || echo "$(GREEN)No errors found!$(NC)"; \
	else \
		echo "$(YELLOW)No log file for today$(NC)"; \
	fi

desktop: ## Open desktop folder where Excel files are saved
	@if [ -d "$$HOME/Desktop" ]; then \
		xdg-open "$$HOME/Desktop" 2>/dev/null || open "$$HOME/Desktop" 2>/dev/null || echo "Desktop: $$HOME/Desktop"; \
	else \
		echo "$(YELLOW)Desktop folder not found at $$HOME/Desktop$(NC)"; \
	fi

dev-install: ## Install development dependencies (if needed later)
	@$(PIP) install black pytest ruff
	@echo "$(GREEN)✓ Development dependencies installed$(NC)"

format: ## Format code with black (requires dev-install)
	@echo "$(BLUE)Formatting code...$(NC)"
	@$(VENV_BIN)/black src/ config.py
	@echo "$(GREEN)✓ Code formatted$(NC)"

lint: ## Lint code with ruff (requires dev-install)
	@echo "$(BLUE)Linting code...$(NC)"
	@$(VENV_BIN)/ruff check src/
	@echo "$(GREEN)✓ Linting complete$(NC)"

info: ## Show project information
	@echo "$(BLUE)Facebook Groups Lead Scraper$(NC)"
	@echo ""
	@echo "$(GREEN)Project Structure:$(NC)"
	@echo "  src/main.py           - Entry point"
	@echo "  src/scraper.py        - FacebookScraper class"
	@echo "  src/analyzer.py       - LeadAnalyzer class"
	@echo "  src/excel_exporter.py - ExcelExporter class"
	@echo "  src/group_processor.py - GroupProcessor class"
	@echo "  config.py             - Configuration"
	@echo ""
	@echo "$(GREEN)Documentation:$(NC)"
	@echo "  README.md             - Main documentation"
	@echo "  ARCHITECTURE.md       - Architecture details"
	@echo "  QUICKSTART.md         - Quick start guide"
	@echo ""
	@echo "$(GREEN)Output:$(NC)"
	@echo "  Desktop/leads_YYYY-MM-DD.xlsx - Exported leads"
	@echo ""

version: ## Show Python and dependency versions
	@echo "$(BLUE)Version Information:$(NC)"
	@echo "Python: $$($(PYTHON_VENV) --version)"
	@$(PIP) show playwright pandas pydantic-ai | grep -E '(Name|Version)'
