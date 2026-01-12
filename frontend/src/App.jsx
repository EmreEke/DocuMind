import { useState, useRef, useEffect } from 'react';
import { uploadPDF, askQuestion } from './api';
import { FaPaperPlane, FaFileUpload, FaRobot, FaUser, FaFilePdf } from 'react-icons/fa';
import './App.css';

function App() {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  
  const [question, setQuestion] = useState('');
  const [chatHistory, setChatHistory] = useState([
    { type: 'bot', text: 'Merhaba! Ben DocuMind. Bana dokümanlarınızla ilgili sorular sorabilirsiniz.' }
  ]);
  const [loading, setLoading] = useState(false);
  
  const chatEndRef = useRef(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatHistory]);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setUploadStatus(null);
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    try {
      const result = await uploadPDF(file);
      setUploadStatus(`Başarılı! Doküman ${result.chunks_count} parçaya bölündü.`);
    } catch (error) {
      console.error(error);
      setUploadStatus('Hata: Yükleme başarısız oldu.');
    } finally {
      setUploading(false);
    }
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!question.trim()) return;

    const newChat = [...chatHistory, { type: 'user', text: question }];
    setChatHistory(newChat);
    setQuestion('');
    setLoading(true);

    try {
      const result = await askQuestion(question);
      setChatHistory(prev => [...prev, { 
        type: 'bot', 
        text: result.answer,
        sources: result.sources 
      }]);
    } catch (error) {
      setChatHistory(prev => [...prev, { type: 'bot', text: 'Üzgünüm, bir hata oluştu.' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      <div className="sidebar">
        <div className="logo">
          <h2>🧠 DocuMind</h2>
          <p>AI-Powered RAG System</p>
        </div>

        <div className="upload-section">
          <h3>📁 Doküman Yükle</h3>
          <div className="file-input-wrapper">
            <input type="file" accept=".pdf" onChange={handleFileChange} id="file-upload" hidden />
            <label htmlFor="file-upload" className="file-label">
              <FaFilePdf /> {file ? file.name : "PDF Seçin..."}
            </label>
          </div>
          
          <button onClick={handleUpload} disabled={!file || uploading} className="upload-btn">
            {uploading ? 'İşleniyor...' : <><FaFileUpload /> Yükle & Analiz Et</>}
          </button>

          {uploadStatus && (
            <div className={`status-msg ${uploadStatus.includes('Hata') ? 'error' : 'success'}`}>
              {uploadStatus}
            </div>
          )}
        </div>
      </div>

      <div className="chat-container">
        <div className="chat-feed">
          {chatHistory.map((msg, index) => (
            <div key={index} className={`message ${msg.type}`}>
              <div className="avatar">{msg.type === 'bot' ? <FaRobot /> : <FaUser />}</div>
              <div className="bubble">
                <p>{msg.text}</p>
                {msg.sources && msg.sources.length > 0 && (
                  <div className="sources"><small>Kaynak ID: {msg.sources.join(', ')}</small></div>
                )}
              </div>
            </div>
          ))}
          {loading && <div className="message bot"><div className="avatar"><FaRobot/></div><div className="bubble typing">Yazıyor...</div></div>}
          <div ref={chatEndRef} />
        </div>

        <form className="input-area" onSubmit={handleSend}>
          <input type="text" placeholder="Doküman hakkında soru sorun..." value={question} onChange={(e) => setQuestion(e.target.value)} disabled={loading} />
          <button type="submit" disabled={loading || !question.trim()}><FaPaperPlane /></button>
        </form>
      </div>
    </div>
  );
}

export default App;