# Multi-Threaded Network Server for Pattern Analysis

This is a Python-based multi-threaded network server that accepts text data (books) from multiple clients simultaneously, processes them for pattern analysis, and maintains synchronized data structures for efficient pattern searching and reporting.


## Requirements

- Python 3.6 or higher
- netcat (nc) command-line utility
- make (for running test scripts)
- Text files to analyze (e.g., books from Project Gutenberg)
<br>

## Server Setup and Usage

### Starting the Server

The server can be started using the following command:
```bash
python3 assignment3.py -l <port> -p <pattern> -i <interval>
```

Parameters:
- `-l, --listen_port`: Port number to listen on (required, must be > 1024)
- `-p, --pattern`: Search pattern to analyze in the incoming text (required)
- `-i, --interval`: Analysis output interval in seconds (optional, default: 5)

Example:
```bash
python3 assignment3.py -l 12345 -p "happy" -i 5
```

### Client Connection Using Netcat

To send a text file to the server, use the netcat (nc) command:
```bash
nc localhost <port> -i <delay> < <filename>
```

Parameters:
- `<port>`: Same port number specified when starting the server
- `<delay>`: Delay in seconds between sending each line (recommended: 1)
- `<filename>`: Path to the text file to send

Example:
```bash
nc localhost 12345 -i 1 < books/book1.txt
```
<br>

## Example Usage Sequence

1. Start the server:
```bash
python3 assignment3.py -l 12345 -p "happy" -i 5
```

2. In separate terminals, send multiple books:
```bash
nc localhost 12345 -i 1 < books/book1.txt
nc localhost 12345 -i 1 < books/book2.txt
nc localhost 12345 -i 1 < books/book3.txt
```
<br>

## Testing with Make

The provided Makefile includes several testing targets:

### Sequential Testing
Sends books one after another:
```bash
make test-sequential
```

### Parallel Testing
Sends multiple books simultaneously:
```bash
make test-parallel
```

### Run Both Tests
```bash
make test
```

