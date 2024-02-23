import streamlit as st
import json
import websocket
import threading
import time
import pieces_os_client as pos_client
final_answer = ""

pieces_os_version = None
asset_ids = {} # Asset ids for any list or search
assets_are_models = False
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
subsequent_timeout = 5  # seconds

configuration = pos_client.Configuration(host="http://localhost:1000")

# Initialize the ApiClient globally
api_client = pos_client.ApiClient(configuration)



api_instance = pos_client.ModelsApi(api_client)

api_response = api_instance.models_snapshot()
models = {model.name: model.id for model in api_response.iterable if model.cloud or model.downloading} # getting the models that are available in the cloud or is downloaded

default_model_name = "GPT-3.5-turbo Chat Model"
model_id = models[default_model_name] # default model id
models_name = [*models] # used in the option list
default_model_index = models_name.index(default_model_name) # used in the option list

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
        self.is_responding = False # to avoid multiple questions to be asked at once

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
            print(self.is_connected)
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

    def ask_question(self, model_id, query):
        if self.is_responding:
            return
        self.is_responding = True
        self.existing_model_id = model_id
        self.query = query
        self.response_received = None  # Reset response received flag

        # Check if WebSocket connection exists and is connected
        if self.ws is None or not self.is_connected:
            # If no connection or not connected, start a new WebSocket connection in a new thread
                    ws_thread = threading.Thread(target=self.start_ws)
                    ws_thread.start()
        else:
            # If already connected, just send the message
            self.send_message()

        self.wait_for_response()
        return self.ws, ws_thread if 'ws_thread' in locals() else None

    def wait_for_response(self):
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
        self.is_responding = False
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
    global ws_manager,model_id
    try:
        ws, ws_thread = ws_manager.ask_question(model_id, query)
    except Exception as e:
        print(f"Error occurred while asking the question: {e}")

###############################################################################
############################## Streamlit Code ############################
###############################################################################
        

st.title("Pieces Copilot Streamlit Bot")
url = "https://images.g2crowd.com/uploads/product/image/social_landscape/social_landscape_43395aae44695b07e11c5cb6aa5bcc60/pieces-for-developers.png"
st.image(url, caption="Pieces Copilot Streamlit Bot", use_column_width=True, width=10)



selected_model = st.selectbox("Choose a model", index=default_model_index,options=models_name, key="dropdown")
model_id = models[selected_model]

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
