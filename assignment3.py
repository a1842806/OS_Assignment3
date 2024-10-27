#!/usr/bin/env python3

import socket
import threading
import sys
import select
import time
import argparse
from typing import Dict, List, Optional

class Node:
    def __init__(self, data: str):
        self.data = data
        self.next: Optional[Node] = None  # Link to the next node in the shared list
        self.book_next: Optional[Node] = None  # Link to the next node in the same book
        self.next_frequent_search: Optional[Node] = None  # Link to the next node containing the search pattern

class Server:
    def __init__(self, port: int, pattern: str, interval: int):
        self.port = port
        self.pattern = pattern
        self.interval = interval
        
        # Shared list pointers
        self.shared_list_head: Optional[Node] = None
        self.shared_list_tail: Optional[Node] = None
        
        # Thread synchronization
        self.shared_list_lock = threading.Lock()
        self.print_lock = threading.Lock()
        self.stop_event = threading.Event()
        
        # Book tracking
        self.book_heads: Dict[int, Node] = {}  # book_number -> head of book list
        self.book_tails: Dict[int, Node] = {}  # book_number -> tail of book list
        self.book_titles: Dict[int, str] = {}  # book_number -> title
        self.book_search_counts: Dict[int, int] = {}  # book_number -> count of search pattern occurrences
        self.book_order: List[int] = []  # list of book numbers in order
        
        # Search pattern tracking
        self.search_pattern_head: Optional[Node] = None
        self.search_pattern_tail: Optional[Node] = None
        
        # Server state
        self.connection_counter = 0
        self.server_socket: Optional[socket.socket] = None
        self.analysis_threads: List[threading.Thread] = []

    def run(self):
        try:
            # Set up the server socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('', self.port))
            self.server_socket.listen(10)  # Increased backlog for more connections
            print(f"Server listening on port {self.port}")

            # Start analysis threads
            for i in range(2):
                t = threading.Thread(target=self.analysis_thread_func, args=(i,))
                t.daemon = True
                t.start()
                self.analysis_threads.append(t)

            while not self.stop_event.is_set():
                # Accept new connections with timeout
                self.server_socket.settimeout(1.0)
                try:
                    client_socket, addr = self.server_socket.accept()
                    self.connection_counter += 1
                    conn_number = self.connection_counter
                    print(f"Accepted connection {conn_number} from {addr}")

                    # Start a new thread to handle the client
                    t = threading.Thread(target=self.client_thread_func, args=(client_socket, conn_number))
                    t.daemon = True
                    t.start()
                except socket.timeout:
                    continue
                except OSError as e:
                    if self.stop_event.is_set():
                        break
                    print(f"Socket error: {e}")

        except KeyboardInterrupt:
            print("\nServer shutting down...")
            self.shutdown()

    def client_thread_func(self, client_socket: socket.socket, conn_number: int):
        client_socket.setblocking(0)  # Non-blocking mode
        buffer = ''
        data_received = False
        book_number = conn_number
        book_title = ''

        try:
            while not self.stop_event.is_set():
                # Use select to check if data is available
                ready_to_read, _, _ = select.select([client_socket], [], [], 0.5)
                
                if ready_to_read:
                    try:
                        data = client_socket.recv(1024).decode('utf-8', errors='replace')
                        if not data:
                            break  # Connection closed
                        
                        buffer += data
                        while '\n' in buffer:
                            line, buffer = buffer.split('\n', 1)
                            line = line.strip()
                            if not line:
                                continue
                                
                            data_received = True
                            node = Node(line + '\n')

                            if not book_title:
                                # First line is the book title
                                book_title = line
                                self.book_titles[book_number] = book_title
                                self.book_heads[book_number] = node
                                self.book_tails[book_number] = node
                                self.book_search_counts[book_number] = 0
                                with self.shared_list_lock:
                                    self.book_order.append(book_number)
                            else:
                                # Update book_next pointer
                                with self.shared_list_lock:
                                    self.book_tails[book_number].book_next = node
                                    self.book_tails[book_number] = node

                            # Update shared list
                            with self.shared_list_lock:
                                if self.shared_list_tail:
                                    self.shared_list_tail.next = node
                                    self.shared_list_tail = node
                                else:
                                    self.shared_list_head = node
                                    self.shared_list_tail = node

                            count = line.count(self.pattern)
                            if count > 0:
                                with self.shared_list_lock:
                                    self.book_search_counts[book_number] += count
                                    if self.search_pattern_tail:
                                        self.search_pattern_tail.next_frequent_search = node
                                        self.search_pattern_tail = node
                                    else:
                                        self.search_pattern_head = node
                                        self.search_pattern_tail = node

                            # Log the addition of the node
                            with self.print_lock:
                                print(f"Added node from connection {conn_number}: {line}")

                    except ConnectionResetError:
                        print(f"Connection {conn_number} was reset by peer")
                        break
                    except socket.error as e:
                        print(f"Socket error in connection {conn_number}: {e}")
                        break

        finally:
            # Connection cleanup
            client_socket.close()
            if data_received:
                # Write the book to a file
                filename = f"book_{conn_number:02d}.txt"
                try:
                    with open(filename, 'w') as f:
                        node = self.book_heads[book_number]
                        while node:
                            f.write(node.data)
                            node = node.book_next
                    with self.print_lock:
                        print(f"Connection {conn_number} closed, book written to {filename}")
                except IOError as e:
                    print(f"Error writing book file for connection {conn_number}: {e}")
            else:
                with self.print_lock:
                    print(f"Connection {conn_number} closed with no data received")

    def analysis_thread_func(self, thread_id: int):
        last_output_time = 0
        
        while not self.stop_event.is_set():
            current_time = time.time()
            
            if current_time - last_output_time >= self.interval:
                acquired_lock = self.print_lock.acquire(blocking=False)
                if acquired_lock:
                    try:
                        self.perform_analysis()
                    finally:
                        self.print_lock.release()
                    last_output_time = current_time  # Move this outside the lock acquisition check
            
            time.sleep(0.1)

    def perform_analysis(self):
        """Analyzes and prints pattern frequency in books"""
        with self.shared_list_lock:
            # Create a list of (count, title, book_number)
            book_info = []
            for book_number in self.book_order:
                count = self.book_search_counts.get(book_number, 0)
                title = self.book_titles.get(book_number, 'Unknown Title')
                book_info.append((count, title, book_number))
            
            # Sort by count descending
            book_info.sort(key=lambda x: x[0], reverse=True)
            
            # Output the results
            print(f"\nAnalysis at {time.strftime('%Y-%m-%d %H:%M:%S')}:")
            print(f"Search pattern: '{self.pattern}'")
            for count, title, book_number in book_info:
                print(f"Book {book_number}: '{title}' - {count} occurrences of '{self.pattern}'")
            print("-" * 40)

    def shutdown(self):
        """Safely shutdown the server"""
        self.stop_event.set()
        if self.server_socket:
            self.server_socket.close()
        
        # Wait for analysis threads to finish
        for thread in self.analysis_threads:
            thread.join(timeout=5.0)
        
        print("Server shutdown complete")

    def __del__(self):
        """Ensure proper cleanup of resources"""
        self.shutdown()

def main():
    parser = argparse.ArgumentParser(description='Multi-Threaded Network Server for Pattern Analysis')
    parser.add_argument('-l', '--listen_port', type=int, required=True, help='Port to listen on')
    parser.add_argument('-p', '--pattern', type=str, required=True, help='Search pattern')
    parser.add_argument('-i', '--interval', type=int, default=5, help='Analysis interval in seconds')
    args = parser.parse_args()

    # Start the server
    server = Server(args.listen_port, args.pattern, args.interval)
    server.run()

if __name__ == '__main__':
    main()