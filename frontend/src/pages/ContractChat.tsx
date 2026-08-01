import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Send, Bot, User, Sparkles } from 'lucide-react'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'
import type { ChatMessage } from '@/types'

const SUGGESTED_QUESTIONS = [
  'Can I terminate this contract early?',
  'What happens if I miss a payment?',
  'What are my main obligations?',
  'Are there any non-compete restrictions?',
  'What penalties exist in this contract?',
]

export function ContractChat() {
  const { id } = useParams<{ id: string }>()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!id) return
    api.getChatHistory(id).then(r => setMessages(r.messages))
  }, [id])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async (text?: string) => {
    const message = text ?? input
    if (!message.trim() || !id) return

    setInput('')
    setSending(true)

    // Optimistic user message
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: message,
      citations: null,
      created_at: new Date().toISOString(),
    }
    setMessages(prev => [...prev, userMsg])

    try {
      const response = await api.sendMessage(id, message)
      setMessages(prev => [...prev, response])
    } catch {
      setMessages(prev => [...prev, {
        id: crypto.randomUUID(), role: 'assistant',
        content: 'Sorry, something went wrong. Please try again.',
        citations: null, created_at: new Date().toISOString(),
      }])
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      <div className="mb-4">
        <h1 className="text-2xl font-bold text-gray-900">Contract Chat</h1>
        <p className="text-gray-500 text-sm">Ask questions about your contract in plain language</p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 pb-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Sparkles className="w-12 h-12 text-brand-300 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Ask anything about your contract</h3>
            <p className="text-gray-500 mb-6 max-w-md">
              I'll answer based only on what's in your document — no guessing, no hallucination.
            </p>
            <div className="flex flex-wrap gap-2 justify-center max-w-lg">
              {SUGGESTED_QUESTIONS.map(q => (
                <button
                  key={q}
                  onClick={() => sendMessage(q)}
                  className="px-3 py-1.5 bg-brand-50 text-brand-700 rounded-full text-sm hover:bg-brand-100 transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map(msg => (
          <div key={msg.id} className={cn('flex gap-3', msg.role === 'user' ? 'justify-end' : 'justify-start')}>
            {msg.role === 'assistant' && (
              <div className="w-8 h-8 bg-brand-100 rounded-full flex items-center justify-center flex-shrink-0">
                <Bot className="w-4 h-4 text-brand-600" />
              </div>
            )}
            <div className={cn(
              'max-w-[70%] rounded-2xl px-4 py-3',
              msg.role === 'user'
                ? 'bg-brand-600 text-white rounded-br-md'
                : 'bg-white border border-gray-200 text-gray-800 rounded-bl-md'
            )}>
              <p className="text-sm whitespace-pre-wrap leading-relaxed">{msg.content}</p>
            </div>
            {msg.role === 'user' && (
              <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center flex-shrink-0">
                <User className="w-4 h-4 text-gray-600" />
              </div>
            )}
          </div>
        ))}

        {sending && (
          <div className="flex gap-3">
            <div className="w-8 h-8 bg-brand-100 rounded-full flex items-center justify-center">
              <Bot className="w-4 h-4 text-brand-600" />
            </div>
            <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-md px-4 py-3">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0.1s]" />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0.2s]" />
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 pt-4">
        <form onSubmit={e => { e.preventDefault(); sendMessage() }} className="flex gap-3">
          <input
            type="text" value={input} onChange={e => setInput(e.target.value)}
            className="input flex-1" placeholder="Ask about your contract..."
            disabled={sending}
          />
          <button type="submit" disabled={!input.trim() || sending} className="btn-primary px-4">
            <Send className="w-4 h-4" />
          </button>
        </form>
        <p className="text-xs text-gray-400 mt-2 text-center">
          Answers are based only on your uploaded document. This is not legal advice.
        </p>
      </div>
    </div>
  )
}
