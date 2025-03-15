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

user_text = st.chat_input("Or type your question here...")
if user_text:
    # Process text input
    response = st.session_state.chatbot.process_text_input(user_text)
    audio_path = st.session_state.chatbot.speech_processor.text_to_speech(response)
    st.session_state.conversation.append(("user", user_text, None))  # None for no audio
    st.session_state.conversation.append(("bot", response, audio_path))

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
    if entry[0] == "user":                              # Check if the entry was made by the user
        col = st.chat_message("user")
        col.markdown(f"**You:** {entry[1]}")
        if entry[2]:  # Show microphone icon for voice inputs
            col.audio(entry[2])
            col.caption("🎤 Voice input")

    elif entry[0] == "bot":                             # Check if the entry was made by the bot
        col = st.chat_message("assistant")
        col.markdown(f"**AI:** {entry[1]}")
        if entry[2]:  # Only show audio for voice responses
            col.audio(entry[2])         # Display a caption, at the buttom, with the audio file path
