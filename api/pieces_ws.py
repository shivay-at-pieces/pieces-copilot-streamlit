import json
import websocket
import time
import threading
WEBSOCKET_URL = "ws://localhost:1000/qgpt/stream"
TIMEOUT = 60  # seconds



class WebSocketManager:
    def __init__(self):
        self.ws = None
        self.is_connected = False
        self.response_received = None
        self.model_id = ""
        self.query = ""
        self.loading = False
        self.last_message_time = None
        self.final_answer = ""
        self.open_event = threading.Event()  # wait for opening event
        self.conversation = None
        #self.QGPTRelevanceInput = pieces_os_client.QGPTRelevanceInput(seeds=)
        self.message_compeleted = threading.Event()
        threading.Thread(target=self._start_ws).start()
        self.open_event.wait()
        

    def on_message(self,ws, message):
        """Handle incoming websocket messages."""
        self.last_message_time = time.time()

        try:
            response = json.loads(message)
            
            answers = response.get('question', {}).get('answers', {}).get('iterable', [])

            for answer in answers:
                text = answer.get('text')
                if text:
                    print(text, end='')
                    self.final_answer += " " + text

            if response.get('status', '') == 'COMPLETED':
                print("\n")
                self.conversation = response.get('conversation',None)
                self.loading = False
                self.message_compeleted.set()
                

        except json.JSONDecodeError as e:
            print(f"Error processing message: {e}")

    def on_error(self, ws, error):
        """Handle websocket errors."""
        print(f"WebSocket error: {error}")
        self.is_connected = False

    def on_close(self, ws, close_status_code, close_msg):
        """Handle websocket closure."""
        print("WebSocket closed")
        self.is_connected = False

    def on_open(self, ws):
        """Handle websocket opening."""
        print("WebSocket connection opened.")
        self.is_connected = True
        self.open_event.set()

    def _start_ws(self):
        """Start a new websocket connection."""
        print("Starting WebSocket connection...")
        ws =  websocket.WebSocketApp(WEBSOCKET_URL,
                                         on_open=self.on_open,
                                         on_message=self.on_message,
                                         on_error=self.on_error,
                                         on_close=self.on_close)
        self.ws = ws
        ws.run_forever()
        

    def send_message(self):
        """Send a message over the websocket."""
        message = {
            "question": {
                "query": self.query,
                "relevant": {"iterable": []},
                "model": self.model_id
            },
            "conversation": self.conversation
        }
        json_message = json.dumps(message)

        if self.is_connected:
            try:
                self.ws.send(json_message)
                print("Response: ")
            except websocket.WebSocketException as e:
                print(f"Error sending message: {e}")
        else:
            raise ConnectionError("WebSocket connection is not open, unable to send message.")

    def close_websocket_connection(self):
        """Close the websocket connection."""
        if self.ws and self.is_connected:
            self.ws.close()
            self.is_connected = False

    def ask_question(self, model_id, query):
        """Ask a question using the websocket."""
        if self.loading:
            return
        self.loading = True
        self.model_id = model_id
        self.query = query
        self.response_received = None

        self.send_message()

        self.message_compeleted.wait(TIMEOUT)
        self.message_compeleted = threading.Event() # creat new instance for another question
        return self.final_answer

# for testing purposes
if __name__ == "__main__":
    ws_m = WebSocketManager()
    ws_m.ask_question("b3994dde-9458-4f02-a045-cdcb48bc3f0c", "What is the purpose of the Python programming language?")
    print("=======================================================")
    ws_m.ask_question("b3994dde-9458-4f02-a045-cdcb48bc3f0c", "What can python programming language do?")
    ws_m.close_websocket_connection()
