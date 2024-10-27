# Makefile for network server testing

PORT = 12345
PATTERN = "happy"
INTERVAL = 5
PYTHON = python3
SERVER = assignment3.py
DELAY = 1
BOOKS_DIR = books
NUM_BOOKS = 11

.PHONY: all clean test test-parallel test-sequential kill

all: clean test

# Clean generated book output files
clean:
	rm -f book_*.txt

# Run the server in background
start-server:
	$(PYTHON) $(SERVER) -l $(PORT) -p $(PATTERN) -i $(INTERVAL) &
	@echo "Server started on port $(PORT)"
	@sleep 2  # Give server time to start

# Kill the server
kill:
	@pkill -f "$(SERVER)" || true
	@echo "Server killed"

# Test sequentially (one book after another)
test-sequential: clean start-server
	@echo "Testing with sequential book transmission..."
	@for i in $$(seq 1 $(NUM_BOOKS)); do \
		echo "Sending book $$i.txt..."; \
		nc localhost $(PORT) -i $(DELAY) < $(BOOKS_DIR)/$$i.txt; \
		sleep 1; \
	done
	@echo "Sequential test complete"
	@$(MAKE) kill

# Test in parallel (all books simultaneously)
test-parallel: clean start-server
	@echo "Testing with parallel book transmission..."
	@for i in $$(seq 1 $(NUM_BOOKS)); do \
		(nc localhost $(PORT) -i $(DELAY) < $(BOOKS_DIR)/$$i.txt &); \
	done
	@echo "Parallel test initiated"
	@sleep $$(( $(NUM_BOOKS) * 5 ))  # Wait for transmission to complete
	@$(MAKE) kill

# Default test (runs both sequential and parallel)
test: test-sequential test-parallel

# Verify book files were created
verify:
	@echo "Verifying output files..."
	@for i in $$(seq 1 $(NUM_BOOKS)); do \
		if [ -f book_$$(printf "%02d" $$i).txt ]; then \
			echo "book_$$(printf "%02d" $$i).txt exists"; \
		else \
			echo "ERROR: book_$$(printf "%02d" $$i).txt missing"; \
		fi \
	done