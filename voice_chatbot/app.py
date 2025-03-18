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
    st.session_state.show_history = False

# Add history controls to sidebar
with st.sidebar:
    st.markdown("### Conversation History Controls")
    
    # Delete all history button with confirmation
    if st.button("Delete All History"):
        if st.session_state.get('confirm_delete_all', False):
            if st.session_state.chatbot.history_manager.delete_all_history():
                st.success("All history deleted successfully!")
                st.session_state.conversation = []  # Clear current conversation
            else:
                st.error("Failed to delete history")
            st.session_state.confirm_delete_all = False
        else:
            st.session_state.confirm_delete_all = True
            st.warning("Are you sure? Click again to confirm.")
    
    # Show history toggle
    show_history = st.checkbox("Show Conversation History")

with st.sidebar:
    st.markdown("### Performance Metrics")
    if 'chatbot' in st.session_state:
        stats = st.session_state.chatbot.timing_stats
        
        # Startup time
        st.text(f"Startup Time: {stats.format_time(stats.startup_time)}")
        
        # Latest timing metrics
        if stats.last_response_time is not None:
            st.markdown("**Latest Request:**")
            st.text(f"Response Generation: {stats.format_time(stats.last_response_time)}")
            if stats.last_audio_time is not None:
                st.text(f"Audio Generation: {stats.format_time(stats.last_audio_time)}")
            if stats.last_total_time is not None:
                st.text(f"Total Time: {stats.format_time(stats.last_total_time)}")

if show_history:
    st.sidebar.markdown("### Past Conversations")
    # Get all conversations
    history = st.session_state.chatbot.history_manager.get_all_conversations()
    
    for conv in history:
        with st.sidebar.expander(f"Conversation from {conv['timestamp'][:16]}"):
            # Add delete button for this conversation
            if st.button("Delete This Conversation", key=f"del_{conv['timestamp']}"):
                if st.session_state.chatbot.history_manager.delete_conversation(conv['timestamp']):
                    st.success("Conversation deleted!")
                    st.rerun()  # Refresh the page
                else:
                    st.error("Failed to delete conversation")
            
            # Display conversation contents
            for msg in conv['messages']:
                role_icon = "🧑" if msg['role'] == "user" else "🤖"
                st.markdown(f"{role_icon} **{msg['role'].title()}:** {msg['content']}")
                if msg['audio_file']:
                    st.audio(msg['audio_file'])

user_text = st.chat_input("Or type your question here...")
if user_text:
    response, response_time, audio_path = st.session_state.chatbot.process_text_input(user_text)
    # Show total processing time
    total_time = st.session_state.chatbot.timing_stats.last_total_time
    if total_time is not None:
        st.info(f"Total processing time: {st.session_state.chatbot.timing_stats.format_time(total_time)}")
    else:
        st.info(f"Processing time: {st.session_state.chatbot.timing_stats.format_time(response_time)}")
    
    # Show message when no audio is generated
    if response.startswith("Rate limit") or response.startswith("I specialize"):
        st.warning("No audio response generated for this message.")
    
    current_conversation = [
        ("user", user_text, None),
        ("bot", response, audio_path)  # Use the returned audio_path
    ]
    st.session_state.conversation.extend(current_conversation)

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
