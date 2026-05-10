import { useState, useRef, useEffect } from 'react';
import { Send } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { sendChatMessage } from '../api';

export default function ChatPanel({ onPlanCreated, className }) {
  const [messages, setMessages] = useState(() => {
    const saved = localStorage.getItem('rockbot_chat');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        return parsed.map(m => ({ ...m, time: new Date(m.time) }));
      } catch (e) {
        console.error('Error parsing chat history', e);
      }
    }
    return [
      {
        role: 'bot',
        text: '¡Hola escalador! 🧗 Soy **RockBot**, tu guía de escalada. Puedo ayudarte a buscar vías, consultar el clima y crear planes de escalada. ¿Qué necesitas?',
        time: new Date(),
      },
    ];
  });
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEnd = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' });
    localStorage.setItem('rockbot_chat', JSON.stringify(messages));
  }, [messages, loading]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg = { role: 'user', text, time: new Date() };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    if (textareaRef.current) textareaRef.current.style.height = '44px';

    try {
      const response = await sendChatMessage(text);
      setMessages((prev) => [
        ...prev,
        { role: 'bot', text: response, time: new Date() },
      ]);
      // Notify parent to refresh plans (a plan might have been created)
      onPlanCreated?.();
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: 'bot',
          text: '⚠️ Error de conexión. Asegúrate de que el servidor esté en ejecución.',
          time: new Date(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleTextareaInput = (e) => {
    setInput(e.target.value);
    e.target.style.height = '44px';
    e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
  };

  const formatTime = (d) =>
    d.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });

  return (
    <div className={`chat-panel ${className || ''}`}>
      <div className="chat-header">
        <div className="chat-header-icon">🧗</div>
        <div className="chat-header-info">
          <h3>RockBot</h3>
          <p>Guía de escalada inteligente</p>
        </div>
      </div>

      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`chat-message ${msg.role}`}>
            <div className="chat-bubble">
              <ReactMarkdown>{msg.text}</ReactMarkdown>
            </div>
            <div className="chat-time">{formatTime(msg.time)}</div>
          </div>
        ))}
        {loading && (
          <div className="typing-indicator">
            <span /><span /><span />
          </div>
        )}
        <div ref={messagesEnd} />
      </div>

      <div className="chat-input-area">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={handleTextareaInput}
          onKeyDown={handleKeyDown}
          placeholder="Escribe tu mensaje..."
          rows={1}
        />
        <button
          className="btn-send"
          onClick={handleSend}
          disabled={loading || !input.trim()}
          title="Enviar"
        >
          <Send size={18} />
        </button>
      </div>
    </div>
  );
}
