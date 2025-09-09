# 🐶 Bulldog Buddy - Smart AI Assistant with Retrieval Augmented Generation

An intelligent conversational AI system designed specifically for National University students. This advanced RAG (Retrieval Augmented Generation) chatbot combines the personality of a friendly bulldog mascot with sophisticated AI technology to provide accurate, helpful responses to both university-specific and general knowledge questions.

## ✨ Features

### **🧠 Dual-Model Architecture**
- **General Knowledge Model**: Handles broad academic topics (machine learning, quantum physics, etc.)
- **University-Specific Model**: Processes handbook-based queries with RAG technology
- **User-Selectable Models**: Choose between Gemma 3 Latest and Llama 3.2 Latest

### **� Comprehensive Knowledge Base**
- **Student Handbook Integration**: Complete 34-section university handbook with structured CSV data
- **6 Knowledge Categories**: Academic, Admissions, Financial, Policies, Student Life, and General
- **Real-Time Information Retrieval**: Tuition fees, admission requirements, academic policies, and more

### **� Advanced Conversation Features**
- **10-Message Memory**: Remembers conversation history for intelligent follow-up responses
- **Context-Aware Responses**: Understands pronouns and references to previous topics
- **Streaming Typewriter Effect**: Real-time response display like ChatGPT
- **Bulldog Personality**: Friendly, encouraging responses with natural "Woof!" expressions

### **🎯 Intelligent Query Routing**
- **Smart Classification**: Automatically determines if questions are university-specific or general knowledge
- **Confidence Scoring**: Provides response confidence metrics
- **Source Attribution**: Shows relevant handbook sections for university queries
- **Fallback Handling**: Graceful error recovery with helpful alternatives

## 🛠️ Technology Stack

- **AI Framework**: LangChain + Ollama
- **Models**: Gemma 3, Llama 3.2, EmbeddingGemma
- **Vector Database**: ChromaDB
- **UI**: Streamlit
- **Data Format**: Structured CSV

## 🚀 Installation & Setup

### **Prerequisites**
1. **Install Ollama** and pull the required models:
   ```bash
   # Install Ollama from https://ollama.ai/
   ollama pull gemma3:latest
   ollama pull llama3.2:latest
   ollama pull embeddinggemma:latest
   ```

### **Project Setup**
2. **Clone and setup the project:**
   ```bash
   git clone https://github.com/matthew-sudo2/Bulldog-Buddy-Smart-AI-Assistant-Retrieval-Augmented-Generation.git
   cd Bulldog-Buddy-Smart-AI-Assistant-Retrieval-Augmented-Generation
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   streamlit run ui.py
   ```
   
   The app will open in your browser at `http://localhost:8501`

## 🏛️ University Knowledge Coverage

### **📋 Academic Information**
- Grading system (4.0 scale) with detailed breakdowns
- Academic load limits and semester requirements  
- Course substitution and petition procedures
- Graduation requirements and academic honors
- Cross-enrollment policies

### **🎓 Admissions & Registration**
- Required documents for freshman and transfer students
- GPA requirements (2.5 regular, 2.0 conditional, 1.75+ scholarship)
- Registration periods and deadlines
- Program shifting procedures

### **💰 Financial Information**
- **Undergraduate Tuition**: ₱2,800 per unit
- **Graduate Tuition**: ₱3,200 (Masters), ₱3,500 (Doctoral)
- Flexible payment options (full, 2-installment, 3-installment)
- Multiple payment channels (online banking, GCash, PayMaya)
- Scholarship opportunities and financial aid

### **👕 Student Life & Policies**
- Uniform requirements and dress code
- Attendance policies (80% minimum requirement)
- Student conduct and academic integrity rules
- ID replacement procedures (₱500)

## 🎯 Usage Examples

### **University-Specific Questions**
- "What are the tuition fees for undergraduate programs?"
- "How do I register for classes next semester?"
- "What's the minimum GPA requirement for graduation?"
- "What payment options are available?"
- "What documents do I need for admission?"

### **General Knowledge Questions**
- "Explain machine learning"
- "What is quantum physics?"
- "How does artificial intelligence work?"
- "Explain the difference between AI and machine learning"

## 📁 Project Structure

```
Bulldog-Buddy-AI/
├── ui.py                           # Main Streamlit application
├── requirements.txt                # Python dependencies
├── README.md                      # This file
├── .gitignore                     # Git ignore rules
├── models/
│   ├── __init__.py
│   └── enhanced_rag_system.py     # Core RAG system implementation
├── data/
│   ├── student-handbook-structured.csv  # Main knowledge base
│   ├── student-handbook.csv       # Additional handbook data
│   └── student-handbook.txt       # Text format backup
├── demo_models.py                 # Model comparison demo
└── test_model_switching.py        # Testing framework
```

## 📊 System Performance

- **Response Accuracy**: 90%+ confidence for financial queries
- **Knowledge Coverage**: 34 handbook sections across 6 categories
- **Conversation Memory**: 10-exchange context retention
- **Response Speed**: Real-time streaming with typewriter effect
- **Model Flexibility**: Dual model selection for optimal performance

## 🎨 Customization

### **Model Configuration**
The system supports easy model switching through the UI dropdown. Available models:
- **Gemma 3 Latest**: Optimized for detailed explanations (temperature: 0.3)
- **Llama 3.2 Latest**: Balanced performance for various queries (temperature: 0.2)

### **Knowledge Base Updates**
Update the CSV files in the `data/` directory to modify the knowledge base:
- `student-handbook-structured.csv`: Main structured knowledge
- Add new sections following the existing format

### **UI Customization**
- Modify colors and branding in `ui.py`
- Update sidebar links and school-specific information
- Customize the bulldog personality responses

## 🔒 Privacy & Security

- **Local Processing**: All data processed locally via Ollama
- **No External APIs**: Complete data privacy and security
- **Session-Based Memory**: Conversation history cleared between sessions
- **Secure File Handling**: Encrypted CSV data processing

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🐾 Support

Built with ❤️ for National University students. For support, please open an issue on GitHub or contact the development team.

---

**Bulldog Buddy**: Your friendly AI campus companion! 🐶📚✨
