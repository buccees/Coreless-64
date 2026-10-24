"""
Enhanced Battleship Game
Copyright (C) [year] [your name]

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import os
import socket
import json
import threading
import time
from typing import Dict, List, Tuple, Optional, Set

class Ship:
    """Represents a ship with its coordinates and status."""
    def __init__(self, name: str, size: int, coordinates: List[Tuple[int, int]]):
        self.name = name
        self.size = size
        self.coordinates = set(coordinates)  # Set of (row, col) tuples
        self.hits = set()  # Track which parts have been hit
    
    def is_hit(self, row: int, col: int) -> bool:
        """Check if this coordinate hits this ship."""
        return (row, col) in self.coordinates
    
    def hit(self, row: int, col: int) -> bool:
        """Register a hit on this ship. Returns True if hit, False if miss."""
        if (row, col) in self.coordinates:
            self.hits.add((row, col))
            return True
        return False
    
    def is_sunk(self) -> bool:
        """Check if this ship is completely sunk."""
        return len(self.hits) == self.size
    
    def get_remaining_coordinates(self) -> Set[Tuple[int, int]]:
        """Get coordinates that haven't been hit yet."""
        return self.coordinates - self.hits
    
    def to_dict(self) -> dict:
        """Convert ship to dictionary for network transmission."""
        return {
            'name': self.name,
            'size': self.size,
            'coordinates': list(self.coordinates),
            'hits': list(self.hits)
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Ship':
        """Create ship from dictionary."""
        ship = cls(data['name'], data['size'], data['coordinates'])
        ship.hits = set(data['hits'])
        return ship

class NetworkManager:
    """Handles network communication for multiplayer games."""
    
    def __init__(self, socket_obj: socket.socket):
        self.socket = socket_obj
        self.connected = True
    
    def send_data(self, data: dict) -> bool:
        """Send data over the network."""
        try:
            message = json.dumps(data).encode('utf-8')
            # Send message length first, then the message
            length = len(message)
            self.socket.sendall(length.to_bytes(4, byteorder='big'))
            self.socket.sendall(message)
            return True
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            self.connected = False
            return False
    
    def receive_data(self) -> Optional[dict]:
        """Receive data from the network."""
        try:
            # First, receive the message length
            length_bytes = self._receive_all(4)
            if not length_bytes:
                return None
            length = int.from_bytes(length_bytes, byteorder='big')
            
            # Then receive the message
            message_bytes = self._receive_all(length)
            if not message_bytes:
                return None
                
            return json.loads(message_bytes.decode('utf-8'))
        except (json.JSONDecodeError, ConnectionResetError, BrokenPipeError, 
                ConnectionAbortedError, OSError, socket.timeout):
            self.connected = False
            return None
    
    def _receive_all(self, length: int) -> Optional[bytes]:
        """Helper to receive exact number of bytes."""
        data = b''
        while len(data) < length:
            try:
                packet = self.socket.recv(length - len(data))
                if not packet:
                    return None
                data += packet
            except socket.timeout:
                return None
        return data
    
    def close(self):
        """Close the network connection."""
        self.connected = False
        try:
            self.socket.close()
        except:
            pass

class BattleshipGame:
    """Enhanced Battleship game with local and network play."""
    
    def __init__(self):
        self.ships_config = {
            "Carrier": 5,
            "Battleship": 4,
            "Cruiser": 3,
            "Submarine": 3,
            "Destroyer": 2,
        }
        self.board_size = 10
        
    def clear_screen(self):
        """Clear the console screen."""
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_banner(self):
        """Print game banner."""
        print("=" * 50)
        print("🚢 ENHANCED BATTLESHIP GAME 🚢")
        print("=" * 50)

    def create_board(self) -> List[List[str]]:
        """Create a 10x10 game board."""
        return [['~' for _ in range(self.board_size)] for _ in range(self.board_size)]

    def print_board(self, board: List[List[str]], show_ships: bool = True, title: str = ""):
        """Print the game board with coordinates."""
        if title:
            print(f"\n{title}")
        print("  A B C D E F G H I J")
        for i, row in enumerate(board):
            display_row = []
            for cell in row:
                if not show_ships and cell == 'S':
                    display_row.append('~')  # Hide ships from opponent
                else:
                    display_row.append(cell)
            print(f"{i+1:2} {' '.join(display_row)}")

    def get_coordinates(self, targeted_cells: Optional[Set[Tuple[int, int]]] = None) -> Tuple:
        """Get valid coordinates from player input."""
        if targeted_cells is None:
            targeted_cells = set()
            
        while True:
            try:
                coord = input("Enter coordinates (e.g., A5, or Q to quit): ").upper().strip()
                if coord == 'Q':
                    return 'Q', 'Q'
                    
                if len(coord) < 2 or len(coord) > 3:
                    print("Invalid format. Please enter coordinates like A5.")
                    continue
                    
                col_char = coord[0]
                row_str = coord[1:]
                
                if not col_char.isalpha() or not row_str.isdigit():
                    print("Invalid format. Use letter-number format (e.g., A5).")
                    continue
                    
                col = ord(col_char) - ord('A')
                row = int(row_str) - 1
                
                if not (0 <= col < self.board_size and 0 <= row < self.board_size):
                    print(f"Coordinates out of range. Use A1 to {chr(ord('A') + self.board_size - 1)}{self.board_size}.")
                    continue
                    
                if (row, col) in targeted_cells:
                    print("You've already targeted these coordinates. Choose again.")
                    continue
                    
                return row, col
                
            except ValueError:
                print("Invalid input. Please enter coordinates like A5 or Q to quit.")

    def can_place_ship(self, board: List[List[str]], row: int, col: int, 
                      size: int, orientation: str) -> bool:
        """Check if a ship can be placed at the given position."""
        if orientation == 'H':
            if col + size > self.board_size:
                return False
            for i in range(size):
                if board[row][col + i] != '~':
                    return False
        elif orientation == 'V':
            if row + size > self.board_size:
                return False
            for i in range(size):
                if board[row + i][col] != '~':
                    return False
        else:
            return False
        return True

    def place_ship_on_board(self, board: List[List[str]], row: int, col: int, 
                           size: int, orientation: str) -> List[Tuple[int, int]]:
        """Place a ship on the board and return its coordinates."""
        coordinates = []
        if orientation == 'H':
            for i in range(size):
                board[row][col + i] = 'S'
                coordinates.append((row, col + i))
        else:  # orientation == 'V'
            for i in range(size):
                board[row + i][col] = 'S'
                coordinates.append((row + i, col))
        return coordinates

    def get_valid_placements(self, board: List[List[str]], size: int) -> List[str]:
        """Get all valid placement options for a ship of given size."""
        placements = []
        for row in range(self.board_size):
            for col in range(self.board_size):
                # Check horizontal placement
                if self.can_place_ship(board, row, col, size, 'H'):
                    placements.append(f"{chr(col + ord('A'))}{row + 1} H")
                # Check vertical placement
                if self.can_place_ship(board, row, col, size, 'V'):
                    placements.append(f"{chr(col + ord('A'))}{row + 1} V")
        return placements

    def place_ships(self, board: List[List[str]], player_name: str) -> Optional[List[Ship]]:
        """Handle ship placement for a player."""
        ships = []
        print(f"\n{player_name}, place your ships:")
        
        for ship_name, ship_size in self.ships_config.items():
            print(f"\nPlace your {ship_name} (size {ship_size}).")
            
            while True:
                valid_placements = self.get_valid_placements(board, ship_size)
                if not valid_placements:
                    print("No valid placements available for this ship!")
                    return None
                    
                print("Available placements:")
                for placement in valid_placements[:10]:  # Show first 10 options
                    print(f"  {placement}")
                if len(valid_placements) > 10:
                    print(f"  ... and {len(valid_placements) - 10} more options")
                
                self.print_board(board, title="Your board:")
                row, col = self.get_coordinates()
                
                if row == 'Q':
                    return None
                
                orientation = input("Enter orientation (H for horizontal, V for vertical): ").upper().strip()
                
                if self.can_place_ship(board, row, col, ship_size, orientation):
                    coordinates = self.place_ship_on_board(board, row, col, ship_size, orientation)
                    ship = Ship(ship_name, ship_size, coordinates)
                    ships.append(ship)
                    print(f"✅ {ship_name} placed successfully!")
                    break
                else:
                    print("❌ Invalid placement. Try again.")
        
        input("Ship placement complete! Press Enter to continue...")
        self.clear_screen()
        return ships

    def take_shot(self, shot_board: List[List[str]], ships: List[Ship], 
                 targeted_cells: Set[Tuple[int, int]]) -> Tuple[str, Optional[str]]:
        """Handle a player taking a shot."""
        row, col = self.get_coordinates(targeted_cells)
        
        if row == 'Q':
            return 'quit', None
            
        targeted_cells.add((row, col))
        
        # Check for hits against all ships
        for ship in ships:
            if ship.hit(row, col):
                shot_board[row][col] = 'X'
                print("💥 Hit!")
                
                if ship.is_sunk():
                    print(f"🎯 You sunk the {ship.name}!")
                    return 'sunk', ship.name
                else:
                    return 'hit', None
        
        # Miss
        shot_board[row][col] = 'O'
        print("💧 Miss!")
        return 'miss', None

    def check_game_over(self, ships: List[Ship]) -> bool:
        """Check if all ships are sunk."""
        return all(ship.is_sunk() for ship in ships)

    def show_main_menu(self) -> str:
        """Display main menu and get user choice."""
        while True:
            self.clear_screen()
            self.print_banner()
            print("\n🎮 GAME MODES:")
            print("1. Local Two-Player Game")
            print("2. Network Multiplayer (Host)")
            print("3. Network Multiplayer (Join)")
            print("4. Exit")
            
            choice = input("\nSelect an option (1-4): ").strip()
            
            if choice in ['1', '2', '3', '4']:
                return choice
            else:
                print("Invalid choice. Please select 1, 2, 3, or 4.")
                input("Press Enter to continue...")

    def play_local_game(self):
        """Play a local two-player game."""
        self.clear_screen()
        print("🏠 LOCAL TWO-PLAYER MODE")
        print("Players will take turns on the same computer.\n")
        
        # Create boards
        player1_board = self.create_board()
        player2_board = self.create_board()
        player1_shot_board = self.create_board()
        player2_shot_board = self.create_board()
        
        # Place ships
        player1_ships = self.place_ships(player1_board, "Player 1")
        if not player1_ships:
            print("Player 1 quit during ship placement.")
            return
            
        player2_ships = self.place_ships(player2_board, "Player 2")
        if not player2_ships:
            print("Player 2 quit during ship placement.")
            return
        
        # Game loop
        current_player = 1
        player1_targeted = set()
        player2_targeted = set()
        
        print("\n⚔️ BATTLE BEGINS! ⚔️")
        
        while True:
            if current_player == 1:
                print(f"\n--- 🔴 Player 1's Turn ---")
                self.print_board(player1_shot_board, show_ships=False, title="Your shots:")
                
                result, ship_name = self.take_shot(player1_shot_board, player2_ships, player1_targeted)
                
                if result == 'quit':
                    print("Player 1 quit the game.")
                    break
                elif result == 'hit' or result == 'sunk':
                    if self.check_game_over(player2_ships):
                        print("\n🎉 PLAYER 1 WINS! 🎉")
                        break
                    # Player continues on hit
                    continue
                else:  # miss
                    current_player = 2
                    
            else:  # Player 2's turn
                print(f"\n--- 🔵 Player 2's Turn ---")
                self.print_board(player2_shot_board, show_ships=False, title="Your shots:")
                
                result, ship_name = self.take_shot(player2_shot_board, player1_ships, player2_targeted)
                
                if result == 'quit':
                    print("Player 2 quit the game.")
                    break
                elif result == 'hit' or result == 'sunk':
                    if self.check_game_over(player1_ships):
                        print("\n🎉 PLAYER 2 WINS! 🎉")
                        break
                    # Player continues on hit
                    continue
                else:  # miss
                    current_player = 1
            
            input("Press Enter to continue...")
            self.clear_screen()
        
        input("\nPress Enter to return to main menu...")

    def start_server(self) -> Optional[NetworkManager]:
        """Start a server and wait for client connection."""
        try:
            # Get local IP address
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            port = 12345
            
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((local_ip, port))
            server_socket.listen(1)
            
            print(f"🌐 Server started on {local_ip}:{port}")
            print("Waiting for opponent to connect...")
            print("(Press Ctrl+C to cancel)")
            
            try:
                client_socket, address = server_socket.accept()
                print(f"✅ Connected to opponent from {address[0]}")
                client_socket.settimeout(30)  # 30 second timeout
                
                network_manager = NetworkManager(client_socket)
                server_socket.close()  # Close the server socket, keep client connection
                return network_manager
                
            except KeyboardInterrupt:
                print("\n❌ Connection cancelled.")
                server_socket.close()
                return None
                
        except OSError as e:
            print(f"❌ Failed to start server: {e}")
            return None

    def connect_to_server(self) -> Optional[NetworkManager]:
        """Connect to a server."""
        while True:
            try:
                server_ip = input("Enter server IP address (or 'back' to return): ").strip()
                if server_ip.lower() == 'back':
                    return None
                    
                port = 12345
                print(f"🌐 Connecting to {server_ip}:{port}...")
                
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.settimeout(10)  # 10 second connection timeout
                client_socket.connect((server_ip, port))
                client_socket.settimeout(30)  # 30 second game timeout
                
                print("✅ Connected to server!")
                return NetworkManager(client_socket)
                
            except socket.timeout:
                print("❌ Connection timed out. Please check the IP address and try again.")
            except socket.error as e:
                print(f"❌ Connection failed: {e}")
            except KeyboardInterrupt:
                print("\n❌ Connection cancelled.")
                return None

    def play_network_game(self, is_host: bool):
        """Play a networked multiplayer game."""
        self.clear_screen()
        
        if is_host:
            print("🏠 NETWORK HOST MODE")
            network_manager = self.start_server()
        else:
            print("🌐 NETWORK CLIENT MODE") 
            network_manager = self.connect_to_server()
        
        if not network_manager:
            input("Press Enter to return to main menu...")
            return
        
        try:
            # Set up game boards
            my_board = self.create_board()
            opponent_board = self.create_board()
            my_shot_board = self.create_board()
            my_targeted = set()
            
            # Place ships
            my_ships = self.place_ships(my_board, "You")
            if not my_ships:
                network_manager.send_data({'type': 'quit', 'reason': 'ship_placement'})
                return
            
            print("Waiting for opponent to place ships...")
            
            # Notify opponent that we're ready
            if not network_manager.send_data({'type': 'ready'}):
                print("❌ Connection lost.")
                return
            
            # Wait for opponent to be ready
            response = network_manager.receive_data()
            if not response or response.get('type') != 'ready':
                print("❌ Opponent disconnected or had an error.")
                return
            
            print("✅ Both players ready! Game starting...")
            time.sleep(2)
            self.clear_screen()
            
            # Determine turn order (host goes first)
            my_turn = is_host
            
            print("⚔️ NETWORK BATTLE BEGINS! ⚔️")
            
            while True:
                if my_turn:
                    print("\n--- 🔴 Your Turn ---")
                    self.print_board(my_shot_board, show_ships=False, title="Your shots:")
                    
                    row, col = self.get_coordinates(my_targeted)
                    
                    if row == 'Q':
                        network_manager.send_data({'type': 'quit'})
                        print("You quit the game.")
                        break
                    
                    my_targeted.add((row, col))
                    
                    # Send shot to opponent
                    if not network_manager.send_data({'type': 'shot', 'row': row, 'col': col}):
                        print("❌ Connection lost.")
                        break
                    
                    # Get response
                    response = network_manager.receive_data()
                    if not response:
                        print("❌ Connection lost.")
                        break
                    
                    if response.get('type') == 'quit':
                        print("🏃 Opponent quit the game.")
                        break
                    
                    # Process shot result
                    if response.get('hit'):
                        my_shot_board[row][col] = 'X'
                        opponent_board[row][col] = 'X'
                        print("💥 Hit!")
                        
                        if response.get('sunk'):
                            print(f"🎯 You sunk the opponent's {response['sunk']}!")
                        
                        if response.get('game_over'):
                            print("\n🎉 YOU WIN! 🎉")
                            break
                        
                        # Continue turn on hit
                        continue
                    else:
                        my_shot_board[row][col] = 'O'
                        opponent_board[row][col] = 'O'
                        print("💧 Miss!")
                        my_turn = False
                
                else:
                    print("\n--- 🔵 Opponent's Turn ---")
                    print("Waiting for opponent's shot...")
                    
                    # Receive opponent's shot
                    shot_data = network_manager.receive_data()
                    if not shot_data:
                        print("❌ Connection lost.")
                        break
                    
                    if shot_data.get('type') == 'quit':
                        print("🏃 Opponent quit the game.")
                        break
                    
                    if shot_data.get('type') != 'shot':
                        continue
                    
                    row, col = shot_data['row'], shot_data['col']
                    coord_str = f"{chr(col + ord('A'))}{row + 1}"
                    print(f"Opponent shot at {coord_str}")
                    
                    # Check if shot hits any of our ships
                    hit = False
                    sunk_ship = None
                    
                    for ship in my_ships:
                        if ship.hit(row, col):
                            hit = True
                            my_board[row][col] = 'X'
                            
                            if ship.is_sunk():
                                sunk_ship = ship.name
                                print(f"💔 Your {ship.name} was sunk!")
                            else:
                                print("💥 Your ship was hit!")
                            break
                    
                    if not hit:
                        my_board[row][col] = 'O'
                        print("💧 Opponent missed!")
                    
                    # Check if game is over
                    game_over = self.check_game_over(my_ships)
                    
                    # Send response
                    response = {
                        'hit': hit,
                        'sunk': sunk_ship,
                        'game_over': game_over
                    }
                    
                    if not network_manager.send_data(response):
                        print("❌ Connection lost.")
                        break
                    
                    self.print_board(my_board, title="Your board:")
                    
                    if game_over:
                        print("\n💀 YOU LOST! 💀")
                        break
                    
                    if hit:
                        # Opponent continues on hit
                        continue
                    else:
                        my_turn = True
                
                input("Press Enter to continue...")
                self.clear_screen()
        
        finally:
            network_manager.close()
        
        input("\nPress Enter to return to main menu...")

    def run(self):
        """Main game loop with menu system."""
        while True:
            choice = self.show_main_menu()
            
            if choice == '1':
                self.play_local_game()
            elif choice == '2':
                self.play_network_game(is_host=True)
            elif choice == '3':
                self.play_network_game(is_host=False)
            elif choice == '4':
                self.clear_screen()
                print("👋 Thanks for playing Battleship!")
                break

def main():
    """Main function to run the game."""
    try:
        game = BattleshipGame()
        game.run()
    except KeyboardInterrupt:
        print("\n\n👋 Game interrupted. Thanks for playing!")
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")
        print("Please restart the game.")

if __name__ == "__main__":
    main()
