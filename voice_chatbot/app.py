import streamlit as st
from modules.chatbot import Chatbot

st.title("AI Voice Chatbot")
chatbot = Chatbot()

if st.button("Start Chatbot"):
    chatbot.chat()
