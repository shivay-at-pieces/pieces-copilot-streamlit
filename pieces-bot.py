import streamlit as st
import pieces_os_client as pos_client
import websocket
from api import *
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

ws_manager = WebSocketManager()

        

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
    if ws_manager.loading:
        with st.beta_expander("An error has occurred", expanded=True):
            st.write(f"Details: {e}")
        return
    try:
        final_answer = ws_manager.ask_question(model_id, query)
    except Exception as e:
        print(f"Error occurred while asking the question: {e}")
    with st.chat_message("assistant"):

        st.markdown(final_answer)

        # Storing the User Message
        st.session_state.messages.append(
            {
                "role": "user",
                "content": query
            }
        )

        # Storing the User Message
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": final_answer
            }
        )

    # Displaying the Assistant Message
    
# Accept the user input
query = st.chat_input("Ask a question to the Pieces Copilot")

# Calling the Function when Input is Provided
if query:
    # Displaying the User Message
    with st.chat_message("user"):
        st.markdown(query)

    pieces_copilot_function(query)
