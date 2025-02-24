import streamlit as st
from modules.chatbot import Chatbot

st.title("AI Voice Chatbot") # Title

# Check if the session state has a key 'chatbot'
# If it doesn't, it will be created and initialized with a Chatbot object
# This is so that the chatbot only needs to be initialized once
if 'chatbot' not in st.session_state:
    # Initialize the chatbot
    st.session_state.chatbot = Chatbot()
    # Set the chat_active flag to False, indicating the chat is not active
    st.session_state.chat_active = False

# Split the screen into two columns
col1, col2 = st.columns(2)

# The first column
with col1:
    # If the chat is not active, show a button to start the chat
    # The button is disabled if the chat is already active
    if st.button("Start Chat", disabled=st.session_state.chat_active):
        # If the button is pressed, set the chat_active flag to True
        st.session_state.chat_active = True
        # Start the chat
        st.session_state.chatbot.chat()

# Use the second column
with col2:
    # If the chat is active, show a button to stop the chat
    # The button is disabled if the chat is not active
    if st.button("Stop Chat", disabled=not st.session_state.chat_active):
        # If the button is pressed, call the stop_chat method
        st.session_state.chatbot.stop_chat()

# Display conversation history 
st.markdown("### Conversation History")
for entry in st.session_state.get('conversation', []):  # Iterate over each entry in the conversation history stored in session state
    if entry[0] == "user":                      # Check if the entry was made by the user
        st.markdown(f"**You:** {entry[1]}")     # Display the user's input

    elif entry[0] == "bot":                     # Check if the entry was made by the bot
        st.markdown(f"**AI:** {entry[1]}")      # Display the bot's response
        st.audio(entry[2])                      # Play the audio file associated with the bot's response
        st.caption(f"Audio file: {entry[2]}")   # Display a caption, at the buttom, with the audio file path
