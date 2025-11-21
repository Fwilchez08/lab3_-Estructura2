"""
Paint 3 - Juego de dibujo multijugador
Laboratorio 3 - Estructura de Datos II
Universidad del Norte

Este módulo implementa el juego principal con arquitectura peer-to-peer,
manejo de múltiples hilos y comunicación por sockets.
"""

import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
import socket
import threading
import json
import time
import random
from datetime import datetime

class Paint3:
    """
    Clase principal del juego Paint 3 con arquitectura P2P.
    Gestiona la interfaz gráfica, conexiones de red y lógica del juego.
    """
    
    def __init__(self, root):
        """Inicializa la aplicación y sus componentes."""
        self.root = root
        self.root.title("Paint 3")
        self.root.geometry("1200x700")
        self.root.resizable(False, False)
        
        # Variables de red
        self.peer_socket = None
        self.server_socket = None
        self.connected_peers = []  # Lista de sockets de peers conectados
        self.is_host = False
        self.my_port = None
        self.my_name = "Jugador"
        
        # Variables del juego
        self.game_active = False
        self.current_drawer = None  # Nombre del jugador que dibuja
        self.am_i_drawing = False
        self.current_word = ""
        self.time_left = 0
        self.round_number = 0
        self.max_rounds = 3
        
        # Palabras para el juego
        self.word_bank = [
            "casa", "perro", "árbol", "carro", "sol", "luna", "estrella",
            "computadora", "teléfono", "libro", "lápiz", "montaña", "río",
            "avión", "barco", "pizza", "helado", "guitarra", "piano", "reloj"
        ]
        
        # Puntuaciones de jugadores
        self.scores = {}  # {nombre: puntos}
        
        # Variables de dibujo
        self.old_x = None
        self.old_y = None
        self.color = "black"
        self.brush_size = 3
        
        # Control de hilos
        self.running = True
        self.timer_thread = None
        
        # Construir interfaz
        self.setup_ui()
        
    def setup_ui(self):
        """Construye la interfaz gráfica de usuario."""
        # Frame principal dividido en tres secciones
        self.main_frame = tk.Frame(self.root, bg="#2C3E50")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Panel izquierdo - Jugadores y puntuaciones
        self.left_panel = tk.Frame(self.main_frame, bg="#34495E", width=200)
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        self.left_panel.pack_propagate(False)
        
        tk.Label(self.left_panel, text="JUGADORES", bg="#34495E", 
                fg="white", font=("Arial", 12, "bold")).pack(pady=10)
        
        self.players_listbox = tk.Listbox(self.left_panel, bg="#2C3E50", 
                                          fg="white", font=("Arial", 10),
                                          selectmode=tk.SINGLE)
        self.players_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Panel central - Canvas de dibujo
        self.center_panel = tk.Frame(self.main_frame, bg="#ECF0F1")
        self.center_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Info del juego
        self.info_frame = tk.Frame(self.center_panel, bg="#3498DB", height=60)
        self.info_frame.pack(fill=tk.X)
        self.info_frame.pack_propagate(False)
        
        self.word_label = tk.Label(self.info_frame, text="Esperando jugadores...", 
                                   bg="#3498DB", fg="white", 
                                   font=("Arial", 18, "bold"))
        self.word_label.pack(side=tk.LEFT, padx=20, pady=10)
        
        self.timer_label = tk.Label(self.info_frame, text="⏱️ --", 
                                    bg="#3498DB", fg="white", 
                                    font=("Arial", 16, "bold"))
        self.timer_label.pack(side=tk.RIGHT, padx=20, pady=10)
        
        # Canvas de dibujo
        self.canvas = tk.Canvas(self.center_panel, bg="white", cursor="cross")
        self.canvas.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Herramientas de dibujo
        self.tools_frame = tk.Frame(self.center_panel, bg="#ECF0F1", height=50)
        self.tools_frame.pack(fill=tk.X)
        self.tools_frame.pack_propagate(False)
        
        tk.Button(self.tools_frame, text="🎨 Color", command=self.choose_color,
                 bg="#E74C3C", fg="white", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        
        tk.Label(self.tools_frame, text="Grosor:", bg="#ECF0F1").pack(side=tk.LEFT, padx=5)
        self.size_scale = tk.Scale(self.tools_frame, from_=1, to=10, orient=tk.HORIZONTAL,
                                   command=self.change_size, bg="#ECF0F1")
        self.size_scale.set(3)
        self.size_scale.pack(side=tk.LEFT, padx=5)
        
        tk.Button(self.tools_frame, text="🗑️ Limpiar", command=self.clear_canvas,
                 bg="#95A5A6", fg="white", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        
        # Eventos del canvas
        self.canvas.bind("<B1-Motion>", self.paint)
        self.canvas.bind("<ButtonRelease-1>", self.reset)
        
        # Panel derecho - Chat y conexión
        self.right_panel = tk.Frame(self.main_frame, bg="#34495E", width=300)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        self.right_panel.pack_propagate(False)
        
        # Sección de conexión
        connection_frame = tk.LabelFrame(self.right_panel, text="Conexión", 
                                        bg="#34495E", fg="white", font=("Arial", 10, "bold"))
        connection_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(connection_frame, text="Tu nombre:", bg="#34495E", fg="white").pack(anchor=tk.W, padx=5)
        self.name_entry = tk.Entry(connection_frame)
        self.name_entry.insert(0, "Jugador")
        self.name_entry.pack(fill=tk.X, padx=5, pady=2)
        
        tk.Button(connection_frame, text="🖥️ Crear Sala (Host)", 
                 command=self.start_host, bg="#27AE60", fg="white").pack(fill=tk.X, padx=5, pady=2)
        
        tk.Label(connection_frame, text="IP del Host:", bg="#34495E", fg="white").pack(anchor=tk.W, padx=5)
        self.host_ip_entry = tk.Entry(connection_frame)
        self.host_ip_entry.insert(0, "127.0.0.1")
        self.host_ip_entry.pack(fill=tk.X, padx=5, pady=2)
        
        tk.Label(connection_frame, text="Puerto:", bg="#34495E", fg="white").pack(anchor=tk.W, padx=5)
        self.port_entry = tk.Entry(connection_frame)
        self.port_entry.insert(0, "5555")
        self.port_entry.pack(fill=tk.X, padx=5, pady=2)
        
        tk.Button(connection_frame, text="🔗 Conectar como Cliente", 
                 command=self.connect_to_host, bg="#3498DB", fg="white").pack(fill=tk.X, padx=5, pady=2)
        
        # Botón para iniciar juego (solo host)
        self.start_game_btn = tk.Button(connection_frame, text="▶️ Iniciar Juego", 
                                       command=self.start_game, bg="#E67E22", 
                                       fg="white", state=tk.DISABLED)
        self.start_game_btn.pack(fill=tk.X, padx=5, pady=5)
        
        # Chat
        chat_frame = tk.LabelFrame(self.right_panel, text="Chat / Adivina", 
                                  bg="#34495E", fg="white", font=("Arial", 10, "bold"))
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.chat_display = tk.Text(chat_frame, bg="#2C3E50", fg="white", 
                                   font=("Arial", 9), state=tk.DISABLED, wrap=tk.WORD)
        self.chat_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.chat_entry = tk.Entry(chat_frame, font=("Arial", 10))
        self.chat_entry.pack(fill=tk.X, padx=5, pady=5)
        self.chat_entry.bind("<Return>", self.send_message)
        
    def start_host(self):
        """Inicia el servidor como host de la sala."""
        self.my_name = self.name_entry.get().strip()
        if not self.my_name:
            messagebox.showerror("Error", "Debes ingresar un nombre")
            return
            
        try:
            port = int(self.port_entry.get())
            self.my_port = port
            self.is_host = True
            
            # Crear socket servidor
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(("0.0.0.0", port))
            self.server_socket.listen(5)
            
            # Agregar a la lista de jugadores
            self.scores[self.my_name] = 0
            self.update_players_list()
            
            # Hilo para aceptar conexiones
            accept_thread = threading.Thread(target=self.accept_connections, daemon=True)
            accept_thread.start()
            
            # Obtener IP local
            local_ip = socket.gethostbyname(socket.gethostname())
            
            self.add_chat_message("SISTEMA", f"✅ Sala creada exitosamente")
            self.add_chat_message("SISTEMA", f"📍 IP Local: {local_ip}")
            self.add_chat_message("SISTEMA", f"🔌 Puerto: {port}")
            self.add_chat_message("SISTEMA", "-" * 30)
            self.add_chat_message("SISTEMA", "Comparte estos datos con otros jugadores:")
            self.add_chat_message("SISTEMA", f"IP: {local_ip}  |  Puerto: {port}")
            
            # Mostrar ventana emergente con la información
            self.show_connection_info(local_ip, port)
            
            self.start_game_btn.config(state=tk.NORMAL)
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo crear la sala: {e}")
    
    def show_connection_info(self, ip, port):
        """Muestra una ventana con la información de conexión del host."""
        info_window = tk.Toplevel(self.root)
        info_window.title("Información de Conexión")
        info_window.geometry("400x250")
        info_window.resizable(False, False)
        info_window.configure(bg="#2C3E50")
        
        # Centrar ventana
        info_window.transient(self.root)
        info_window.grab_set()
        
        tk.Label(info_window, text="🎮 Sala Creada", 
                bg="#2C3E50", fg="white", 
                font=("Arial", 16, "bold")).pack(pady=15)
        
        tk.Label(info_window, text="Comparte esta información con otros jugadores:", 
                bg="#2C3E50", fg="#ECF0F1", 
                font=("Arial", 10)).pack(pady=5)
        
        # Frame para la info
        info_frame = tk.Frame(info_window, bg="#34495E", relief=tk.RAISED, borderwidth=2)
        info_frame.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)
        
        tk.Label(info_frame, text="IP del Host:", 
                bg="#34495E", fg="#3498DB", 
                font=("Arial", 11, "bold")).pack(pady=(10, 2))
        
        ip_label = tk.Label(info_frame, text=ip, 
                           bg="#34495E", fg="white", 
                           font=("Courier", 14, "bold"))
        ip_label.pack(pady=2)
        
        tk.Label(info_frame, text="Puerto:", 
                bg="#34495E", fg="#3498DB", 
                font=("Arial", 11, "bold")).pack(pady=(10, 2))
        
        port_label = tk.Label(info_frame, text=str(port), 
                             bg="#34495E", fg="white", 
                             font=("Courier", 14, "bold"))
        port_label.pack(pady=2)
        
        # Botón para copiar (simulado con selección de texto)
        btn_frame = tk.Frame(info_window, bg="#2C3E50")
        btn_frame.pack(pady=10)
        
        def copy_info():
            info_text = f"IP: {ip}\nPuerto: {port}"
            self.root.clipboard_clear()
            self.root.clipboard_append(info_text)
            messagebox.showinfo("Copiado", "Información copiada al portapapeles")
        
        tk.Button(btn_frame, text="📋 Copiar Info", command=copy_info,
                 bg="#27AE60", fg="white", font=("Arial", 10, "bold"),
                 padx=20, pady=5).pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="✓ Entendido", command=info_window.destroy,
                 bg="#3498DB", fg="white", font=("Arial", 10, "bold"),
                 padx=20, pady=5).pack(side=tk.LEFT, padx=5)
    
    def accept_connections(self):
        """Hilo que acepta conexiones entrantes de nuevos peers."""
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                self.add_chat_message("SISTEMA", f"Nueva conexión desde {address}")
                
                # Añadir a la lista de peers
                self.connected_peers.append(client_socket)
                
                # Hilo para manejar este peer
                peer_thread = threading.Thread(target=self.handle_peer, 
                                              args=(client_socket,), daemon=True)
                peer_thread.start()
                
            except:
                break
    
    def connect_to_host(self):
        """Conecta al host como cliente."""
        self.my_name = self.name_entry.get().strip()
        if not self.my_name:
            messagebox.showerror("Error", "Debes ingresar un nombre")
            return
            
        try:
            host_ip = self.host_ip_entry.get()
            port = int(self.port_entry.get())
            
            self.peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.peer_socket.connect((host_ip, port))
            
            # Enviar nombre al host
            self.send_data({"type": "join", "name": self.my_name})
            
            # Hilo para recibir datos
            receive_thread = threading.Thread(target=self.receive_data, daemon=True)
            receive_thread.start()
            
            self.add_chat_message("SISTEMA", f"Conectado al host {host_ip}:{port}")
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo conectar: {e}")
    
    def handle_peer(self, peer_socket):
        """Maneja la comunicación con un peer conectado."""
        buffer = ""
        try:
            while self.running:
                data = peer_socket.recv(4096).decode('utf-8')
                if not data:
                    break
                    
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line:
                        try:
                            message = json.loads(line)
                            self.process_message(message, peer_socket)
                        except json.JSONDecodeError:
                            continue
                        
        except Exception as e:
            self.add_chat_message("SISTEMA", f"Error con peer: {e}")
        finally:
            if peer_socket in self.connected_peers:
                self.connected_peers.remove(peer_socket)
            peer_socket.close()
    
    def receive_data(self):
        """Hilo que recibe datos del host (para clientes)."""
        buffer = ""
        try:
            while self.running:
                data = self.peer_socket.recv(4096).decode('utf-8')
                if not data:
                    print("DEBUG: Cliente desconectado del host")
                    break
                    
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line:
                        try:
                            message = json.loads(line)
                            msg_type = message.get('type')
                            # Solo mostrar debug para mensajes importantes, no para "draw"
                            if msg_type != 'draw':
                                print(f"DEBUG receive_data: Cliente recibió {msg_type}")
                            self.process_message(message, None)
                        except json.JSONDecodeError as e:
                            print(f"DEBUG: Error JSON: {e}")
                            continue
                        
        except Exception as e:
            self.add_chat_message("SISTEMA", f"Desconectado del host: {e}")
            print(f"DEBUG receive_data error: {e}")
    
    def process_message(self, message, sender_socket):
        """Procesa mensajes recibidos de otros peers."""
        msg_type = message.get("type")
        
        if msg_type == "join":
            # Nuevo jugador se une
            name = message.get("name")
            self.scores[name] = 0
            self.update_players_list()
            self.add_chat_message("SISTEMA", f"{name} se ha unido al juego")
            
            # Si soy host, envío la lista actualizada a todos
            if self.is_host:
                self.broadcast_data({"type": "player_list", "players": self.scores})
                # Enviar la lista al nuevo jugador también
                self.send_data_to_peer(sender_socket, 
                    {"type": "player_list", "players": self.scores})
        
        elif msg_type == "player_list":
            # Actualizar lista de jugadores
            self.scores = message.get("players", {})
            self.update_players_list()
        
        elif msg_type == "start_game":
            # Iniciar el juego
            self.round_number = message.get("round", 1)
            self.current_drawer = message.get("drawer")
            self.am_i_drawing = (self.current_drawer == self.my_name)
            word = message.get("word", "")
            
            print(f"DEBUG start_game: drawer={self.current_drawer}, am_i_drawing={self.am_i_drawing}, word={word}")
            
            if self.am_i_drawing:
                self.current_word = word
                self.word_label.config(text=f"Dibuja: {self.current_word}")
                print(f"DEBUG: Soy el dibujante, palabra: {self.current_word}")
            else:
                # NO soy el dibujante, pero NECESITO conocer la palabra para verificar respuestas
                self.current_word = word
                hint = "_" * len(word)
                self.word_label.config(text=f"Adivina: {hint}")
                print(f"DEBUG: Soy quien adivina, palabra guardada: {self.current_word}")
            
            self.time_left = 60
            self.game_active = True
            self.clear_canvas()
            
            if not self.timer_thread or not self.timer_thread.is_alive():
                self.timer_thread = threading.Thread(target=self.game_timer, daemon=True)
                self.timer_thread.start()
            
            self.add_chat_message("SISTEMA", 
                f"Ronda {self.round_number}: {self.current_drawer} está dibujando")
        
        elif msg_type == "draw":
            # Recibir trazo de dibujo
            if not self.am_i_drawing:
                x1, y1 = message.get("x1"), message.get("y1")
                x2, y2 = message.get("x2"), message.get("y2")
                color = message.get("color")
                size = message.get("size")
                self.canvas.create_line(x1, y1, x2, y2, 
                                       fill=color, width=size, 
                                       capstyle=tk.ROUND, smooth=True)
        
        elif msg_type == "clear":
            # Limpiar canvas
            self.canvas.delete("all")
        
        elif msg_type == "chat":
            # Mensaje de chat (solo se recibe si NO es respuesta correcta)
            name = message.get("name")
            text = message.get("text")
            self.add_chat_message(name, text)
        
        elif msg_type == "correct_guess":
            # Un cliente adivinó correctamente (recibido por el host)
            name = message.get("name")
            received_scores = message.get("scores", {})
            
            print(f"DEBUG: Host recibió correct_guess de {name}")
            print(f"DEBUG: Puntajes recibidos: {received_scores}")
            
            # Actualizar puntajes en el host
            if received_scores:
                self.scores = received_scores
            else:
                if name not in self.scores:
                    self.scores[name] = 0
                self.scores[name] += 10
            
            self.update_players_list()
            
            # Si soy el host
            if self.is_host:
                print(f"DEBUG: Host anunciando que {name} adivinó")
                self.add_chat_message("SISTEMA", f"¡{name} adivinó la palabra!")
                
                # Reenviar a TODOS los clientes para que vean la actualización
                broadcast_msg = {
                    "type": "correct_guess",
                    "name": name,
                    "scores": self.scores
                }
                print(f"DEBUG: Host reenviando: {broadcast_msg}")
                self.broadcast_data(broadcast_msg)
            else:
                # Si soy cliente recibiendo del host
                print(f"DEBUG: Cliente recibiendo correct_guess de {name}")
                if name != self.my_name:
                    self.add_chat_message("SISTEMA", f"¡{name} adivinó la palabra!")
        
        elif msg_type == "end_round":
            # Terminar ronda
            self.game_active = False
            word = message.get("word")
            self.add_chat_message("SISTEMA", f"Ronda terminada. La palabra era: {word}")
            self.word_label.config(text=f"La palabra era: {word}")
    
    def send_data(self, data):
        """Envía datos al servidor (si soy cliente)."""
        if self.peer_socket:
            try:
                message = json.dumps(data) + '\n'
                self.peer_socket.send(message.encode('utf-8'))
            except:
                pass
    
    def send_data_to_peer(self, peer_socket, data):
        """Envía datos a un peer específico."""
        if peer_socket:
            try:
                message = json.dumps(data) + '\n'
                peer_socket.send(message.encode('utf-8'))
            except:
                pass
    
    def broadcast_data(self, data):
        """Transmite datos a todos los peers conectados (host)."""
        if self.is_host:
            message = json.dumps(data) + '\n'
            for peer in self.connected_peers[:]:  # Copia para evitar modificación durante iteración
                try:
                    peer.send(message.encode('utf-8'))
                except:
                    self.connected_peers.remove(peer)
    
    def start_game(self):
        """Inicia una nueva ronda del juego (solo host)."""
        if not self.is_host:
            return
        
        if len(self.scores) < 2:
            messagebox.showwarning("Espera", "Se necesitan al menos 2 jugadores")
            return
        
        self.round_number += 1
        
        # Seleccionar dibujante aleatorio
        players = list(self.scores.keys())
        self.current_drawer = random.choice(players)
        self.am_i_drawing = (self.current_drawer == self.my_name)
        
        # Seleccionar palabra aleatoria
        self.current_word = random.choice(self.word_bank)
        
        print(f"DEBUG start_game (HOST): round={self.round_number}, drawer={self.current_drawer}, word={self.current_word}")
        
        # Enviar información del juego a TODOS (incluyendo al host)
        game_data = {
            "type": "start_game",
            "round": self.round_number,
            "drawer": self.current_drawer,
            "word": self.current_word
        }
        
        print(f"DEBUG: Host enviando start_game a todos: {game_data}")
        
        # Transmitir a todos los clientes
        self.broadcast_data(game_data)
        
        # El host también procesa el mensaje (importante!)
        self.process_message(game_data, None)
    
    def game_timer(self):
        """Hilo del temporizador del juego."""
        while self.game_active and self.time_left > 0:
            self.timer_label.config(text=f"⏱️ {self.time_left}s")
            time.sleep(1)
            self.time_left -= 1
        
        if self.game_active:
            self.game_active = False
            self.timer_label.config(text="⏱️ 0s")
            
            if self.is_host:
                self.broadcast_data({
                    "type": "end_round",
                    "word": self.current_word
                })
                self.add_chat_message("SISTEMA", 
                    f"Tiempo terminado. La palabra era: {self.current_word}")
                self.word_label.config(text=f"La palabra era: {self.current_word}")
    
    def paint(self, event):
        """Maneja el evento de dibujo en el canvas."""
        if not self.am_i_drawing or not self.game_active:
            return
        
        if self.old_x and self.old_y:
            # Dibujar línea localmente
            self.canvas.create_line(self.old_x, self.old_y, event.x, event.y,
                                   fill=self.color, width=self.brush_size,
                                   capstyle=tk.ROUND, smooth=True)
            
            # Enviar coordenadas a otros jugadores
            draw_data = {
                "type": "draw",
                "x1": self.old_x,
                "y1": self.old_y,
                "x2": event.x,
                "y2": event.y,
                "color": self.color,
                "size": self.brush_size
            }
            
            if self.is_host:
                self.broadcast_data(draw_data)
            else:
                self.send_data(draw_data)
        
        self.old_x = event.x
        self.old_y = event.y
    
    def reset(self, event):
        """Resetea las coordenadas de dibujo."""
        self.old_x = None
        self.old_y = None
    
    def choose_color(self):
        """Abre selector de color."""
        if self.am_i_drawing and self.game_active:
            color = colorchooser.askcolor(title="Elige un color")[1]
            if color:
                self.color = color
    
    def change_size(self, value):
        """Cambia el grosor del pincel."""
        self.brush_size = int(value)
    
    def clear_canvas(self):
        """Limpia el canvas de dibujo."""
        if self.am_i_drawing and self.game_active:
            self.canvas.delete("all")
            
            clear_data = {"type": "clear"}
            if self.is_host:
                self.broadcast_data(clear_data)
            else:
                self.send_data(clear_data)
    
    def send_message(self, event=None):
        """Envía un mensaje de chat."""
        message = self.chat_entry.get().strip()
        if not message:
            return
        
        self.chat_entry.delete(0, tk.END)
        
        # Verificar si es la respuesta correcta (solo si no soy el dibujante)
        if self.game_active and not self.am_i_drawing and self.current_word:
            print(f"DEBUG: Verificando '{message}' contra palabra '{self.current_word}'")
            if message.lower() == self.current_word.lower():
                print(f"DEBUG: ¡CORRECTO! Cliente {self.my_name} adivinó")
                # ¡Es correcto! Sumar puntos
                self.scores[self.my_name] = self.scores.get(self.my_name, 0) + 10
                self.update_players_list()
                
                # Mostrar localmente
                self.add_chat_message("SISTEMA", "¡Adivinaste correctamente! 🎉")
                
                # Notificar a otros
                correct_data = {
                    "type": "correct_guess",
                    "name": self.my_name,
                    "scores": self.scores
                }
                
                print(f"DEBUG: Enviando correct_guess: {correct_data}")
                
                if self.is_host:
                    self.broadcast_data(correct_data)
                    self.add_chat_message("SISTEMA", f"¡{self.my_name} adivinó la palabra!")
                else:
                    self.send_data(correct_data)
                
                return  # NO enviar al chat, terminar la función
            else:
                print(f"DEBUG: Incorrecto - '{message.lower()}' != '{self.current_word.lower()}'")
        
        # Si llegamos aquí, es un mensaje normal (no la palabra correcta)
        print(f"DEBUG: Enviando mensaje normal: {message}")
        chat_data = {
            "type": "chat",
            "name": self.my_name,
            "text": message
        }
        
        if self.is_host:
            self.broadcast_data(chat_data)
        else:
            self.send_data(chat_data)
        
        self.add_chat_message(self.my_name, message)
    
    def add_chat_message(self, name, text):
        """Agrega un mensaje al chat."""
        self.chat_display.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M")
        
        if name == "SISTEMA":
            self.chat_display.insert(tk.END, f"[{timestamp}] 🔔 {text}\n", "system")
            self.chat_display.tag_config("system", foreground="#E67E22")
        else:
            self.chat_display.insert(tk.END, f"[{timestamp}] {name}: {text}\n")
        
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
    
    def update_players_list(self):
        """Actualiza la lista de jugadores y puntuaciones."""
        self.players_listbox.delete(0, tk.END)
        
        # Ordenar por puntuación
        sorted_players = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)
        
        for name, score in sorted_players:
            indicator = "🎨" if name == self.current_drawer else "👤"
            self.players_listbox.insert(tk.END, f"{indicator} {name}: {score} pts")
    
    def cleanup(self):
        """Limpia recursos al cerrar la aplicación."""
        self.running = False
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        if self.peer_socket:
            try:
                self.peer_socket.close()
            except:
                pass
        
        for peer in self.connected_peers:
            try:
                peer.close()
            except:
                pass

def main():
    """Función principal para iniciar la aplicación."""
    root = tk.Tk()
    app = Paint3(root)
    
    # Manejar cierre de ventana
    def on_closing():
        if messagebox.askokcancel("Salir", "¿Deseas salir del juego?"):
            app.cleanup()
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()