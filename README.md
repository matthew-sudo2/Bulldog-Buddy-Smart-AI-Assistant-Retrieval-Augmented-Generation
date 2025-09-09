# 🐶 Bulldog Buddy - Smart Campus Assistant

A Streamlit-based chatbot UI for your school project, featuring your school's bulldog mascot!

## Features

- **🐶 Bulldog Branding**: Complete with bulldog avatars and school-themed colors
- **💬 Chat Interface**: Clean, modern chat UI using Streamlit components
- **🔄 Persistent Messages**: Chat history stored in session state
- **📋 Quick Links Sidebar**: Easy access to school website, student portal, and library
- **📱 Responsive Design**: Works on desktop and mobile devices
- **🎨 Customizable**: Easy to modify colors and branding for your school

## Installation

1. Make sure you have Python installed
2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

## Running the App

Run the Streamlit app with:
```
streamlit run ui.py
```

The app will open in your browser at `http://localhost:8501`

## Customization

### School Colors
Edit the CSS in `ui.py` around line 17 to change colors:
- Main color: `#2E4057` (dark blue)
- Accent color: `#1A252F` (darker blue)
- Background: `#F8F9FA` (light gray)

### Quick Links
Update the sidebar links in the `main()` function to point to your actual:
- School website URL
- Student portal URL  
- Library website URL

### Bot Responses
The `get_bot_response()` function contains placeholder responses. Replace this with your actual model integration:

```python
def get_bot_response(user_message):
    # Replace with your model API call
    response = your_model_api_call(user_message)
    return response
```

## Features Included

✅ Streamlit chat interface (`st.chat_message`, `st.chat_input`)  
✅ Bulldog mascot branding (🐶 for bot, 👤 for user)  
✅ School-themed UI with customizable colors  
✅ Sidebar with school logo and quick links  
✅ Persistent chat history in `st.session_state`  
✅ Placeholder bot responses ready for your backend integration  
✅ Mobile-responsive design  
✅ Welcome message and helpful prompts  

## Project Structure

```
Paw-sitive AI/
├── ui.py              # Main Streamlit application
├── requirements.txt   # Python dependencies
└── README.md         # This file
```

## Next Steps

1. **Customize branding**: Update colors and links for your specific school
2. **Integrate your model**: Replace the `get_bot_response()` function with your actual AI model
3. **Add more features**: Consider adding file uploads, voice input, or specialized campus features
4. **Deploy**: Use Streamlit Cloud, Heroku, or your preferred platform to deploy the app

## Support

Built with ❤️ for your school project. Good luck with your assignment! 🐾
