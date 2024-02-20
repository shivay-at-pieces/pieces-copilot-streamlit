import streamlit as st
import json
import websocket
import threading
import time
import pieces_os_client as pos_client

final_answer = ""

pieces_os_version = None
run_in_loop = False # is CLI looping?
asset_ids = {} # Asset ids for any list or search
assets_are_models = False
current_model = {'6f4c2926-c1b3-462e-91c2-20b076c44b58'} # GPT 3.5 Turbo
current_asset = {}
parser = None
application = None
ws = None # Websocket connection to pass to api.py when running
ws_thread = None # Websocket thread to pass to api.py when running
cli_version = None
response_received = None
existing_model_id = ""
query = ""
ws = websocket
loading = False
last_message_time = None
initial_timeout = 10  # seconds
subsequent_timeout = 3  # seconds

configuration = pos_client.Configuration(host="http://localhost:1000")

# Initialize the ApiClient globally
api_client = pos_client.ApiClient(configuration)

###############################################################################
############################## WEBSOCKET FUNCTIONS ############################
###############################################################################

class WebSocketManager:
    def __init__(self):
        self.ws = None
        self.is_connected = False
        self.response_received = None
        self.existing_model_id = ""
        self.query = ""
        self.loading = False
        self.last_message_time = None
        self.initial_timeout = 10  # seconds
        self.subsequent_timeout = 3  # seconds
        self.first_token_received = False
        self.final_answer = ""

    def on_message(self, ws, message):
        self.last_message_time = time.time()
        self.first_token_received = True

        try:
            response = json.loads(message)
            answers = response.get('question', {}).get('answers', {}).get('iterable', [])

            for answer in answers:
                text = answer.get('text')
                if text:
                    print(text, end='')
                    self.final_answer = self.final_answer + " " + text

            # Check if the response is complete and add a newline
            status = response.get('status', '')
            if status == 'COMPLETED':
                print("\n")  # Add a newline after the complete response
                self.loading = False

        except Exception as e:
            print(f"Error processing message: {e}")

    def on_error(self, ws, error):
        print(f"WebSocket error: {error}")
        self.is_connected = False

    def on_close(self, ws, close_status_code, close_msg):
        print("WebSocket closed")
        self.is_connected = False

    def on_open(self, ws):
        print("WebSocket connection opened.")
        self.is_connected = True
        self.send_message()

    def start_websocket_connection(self):
        print("Starting WebSocket connection...")
        self.ws = websocket.WebSocketApp("ws://localhost:1000/qgpt/stream",
                                         on_open=self.on_open,
                                         on_message=self.on_message,
                                         on_error=self.on_error,
                                         on_close=self.on_close)
        return self.ws

    def start_ws(self):
        if self.ws is None or not self.is_connected:
            print("No WebSocket provided or connection is closed, opening a new connection.")
            self.ws = self.start_websocket_connection()
        else:
            print("Using provided WebSocket connection.")

        self.ws.run_forever()

    def send_message(self):
        message = {
            "question": {
                "query": self.query,
                "relevant": {"iterable": []},
                "model": self.existing_model_id
            }
        }

        json_message = json.dumps(message)

        if self.is_connected:
            try:
                self.ws.send(json_message)
                print("Response: ")
            except Exception as e:
                print(f"Error sending message: {e}")
        else:
            print("WebSocket connection is not open, unable to send message.")

    def close_websocket_connection(self):
        if self.ws and self.is_connected:
            print("Closing WebSocket connection...")
            self.ws.close()
            self.is_connected = False

    def ask_question(self, model_id, query, run_in_loop=False):
        self.existing_model_id = model_id
        self.query = query

        if self.ws is None or not self.is_connected:
            ws_thread = threading.Thread(target=self.start_ws)
            ws_thread.start()
        else:
            self.send_message()

        self.wait_for_response(run_in_loop)
        return self.ws, ws_thread if 'ws_thread' in locals() else None

    def wait_for_response(self, run_in_loop):
        self.final_answer = ""
        self.last_message_time = time.time()
        while self.response_received is None:
            current_time = time.time()
            if self.first_token_received:
                if current_time - self.last_message_time > self.subsequent_timeout:
                    break
            else:
                if current_time - self.last_message_time > self.initial_timeout:
                    break
            time.sleep(0.1)

        if not run_in_loop and self.is_connected:
            self.close_websocket_connection()
            # final_answer = ""
        with st.chat_message("assistant"):

                st.markdown(self.final_answer)

            # Storing the User Message
                st.session_state.messages.append(
                    {
                        "role":"user",
                        "content": query
                    }
                )

                # Storing the User Message
                st.session_state.messages.append(
                    {
                        "role":"assistant",
                        "content": self.final_answer
                    }
                )

ws_manager = WebSocketManager()

def ask(query, **kwargs):
    global current_model, ws_manager, run_in_loop

    if current_model:
        model_id = next(iter(current_model))
    else:
        raise ValueError("No model ID available")

    try:
        ws, ws_thread = ws_manager.ask_question(model_id, query, run_in_loop)

    except Exception as e:
        print(f"Error occurred while asking the question: {e}")

###############################################################################
############################## Streamlit Code ############################
###############################################################################
        

st.title("Pieces Copilot Streamlit Bot")
url = "https://images.g2crowd.com/uploads/product/image/social_landscape/social_landscape_43395aae44695b07e11c5cb6aa5bcc60/pieces-for-developers.png"
st.image(url, caption="Pieces Copilot Streamlit Bot", use_column_width=True, width=10)


# Initialize chat history for Streamlit
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role":"assistant",
            "content":"Ask me Anything - Pieces Copilot"
        }
    ]

# Display chat messages from history on Pieces Bot app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Process and store Query and Response
def pieces_copilot_function(query):

    response = ask(query)


    # Displaying the Assistant Message
    
# Accept the user input
query = st.chat_input("Ask a question to the Pieces Copilot")

# Calling the Function when Input is Provided
if query:
    # Displaying the User Message
    with st.chat_message("user"):
        st.markdown(query)

    pieces_copilot_function(query)
