import { useEffect, useState } from 'react';

import api from '@/api';
import ChatInput from '@/components/ChatInput';
import ChatMessages from '@/components/ChatMessages';

function Chatbot() {
  const [messages, setMessages] = useState([]);
  const [historyItems, setHistoryItems] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [userId, setUserId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isHistoryLoading, setIsHistoryLoading] = useState(true);

  useEffect(() => {
    async function loadInitialHistory() {
      setIsHistoryLoading(true);
      try {
        const data = await api.listHistory();
        setHistoryItems(data);

        if (data.length > 0) {
          const conversation = await api.getHistory(data[0].user_id);
          setUserId(conversation.user_id);
          setMessages(conversation.messages);
        }
      } catch (error) {
        console.error('Error loading history:', error);
      } finally {
        setIsHistoryLoading(false);
      }
    }

    loadInitialHistory();
  }, []);

  async function loadHistory(activeUserId = userId) {
    setIsHistoryLoading(true);
    try {
      const data = await api.listHistory();
      setHistoryItems(data);

      if (!activeUserId && data.length > 0) {
        await loadConversation(data[0].user_id);
      }
    } catch (error) {
      console.error('Error loading history:', error);
    } finally {
      setIsHistoryLoading(false);
    }
  }

  async function loadConversation(targetUserId) {
    setIsLoading(true);
    try {
      const conversation = await api.getHistory(targetUserId);
      setUserId(conversation.user_id);
      setMessages(conversation.messages);
    } catch (error) {
      console.error('Error loading conversation:', error);
    } finally {
      setIsLoading(false);
    }
  }

  function startFreshConversation() {
    setUserId(null);
    setMessages([]);
    setNewMessage('');
  }

  async function renameConversation(targetUserId, currentTitle) {
    const title = window.prompt('Rename this conversation', currentTitle);
    if (!title || title.trim() === currentTitle) return;

    try {
      await api.updateHistory(targetUserId, title.trim());
      await loadHistory(targetUserId);
    } catch (error) {
      console.error('Error renaming conversation:', error);
    }
  }

  async function deleteConversation(targetUserId) {
    const shouldDelete = window.confirm('Delete this conversation history?');
    if (!shouldDelete) return;

    try {
      await api.deleteHistory(targetUserId);
      if (targetUserId === userId) {
        startFreshConversation();
      }
      await loadHistory(targetUserId === userId ? null : userId);
    } catch (error) {
      console.error('Error deleting conversation:', error);
    }
  }

  async function submitNewMessage() {
    const trimmedMessage = newMessage.trim();
    if (!trimmedMessage || isLoading) return;

    setMessages(prevMessages => [
      ...prevMessages,
      { role: 'user', content: trimmedMessage },
      { role: 'assistant', content: '', loading: true },
    ]);

    setNewMessage('');
    setIsLoading(true);

    try {
      const response = userId
        ? await api.continuePipeline(trimmedMessage, userId)
        : await api.startPipeline(trimmedMessage);
      const nextUserId = response.user_id || userId;
      setUserId(nextUserId);

      setMessages(prevMessages => {
        const nextMessages = [...prevMessages];
        nextMessages[nextMessages.length - 1] = {
          role: 'assistant',
          content: response.message || 'Sorry, I could not get a response.',
          loading: false,
        };
        return nextMessages;
      });

      await loadHistory(nextUserId);
    } catch (error) {
      console.error('Error communicating with API:', error);
      setMessages(prevMessages => {
        const nextMessages = [...prevMessages];
        nextMessages[nextMessages.length - 1] = {
          role: 'assistant',
          content: error.message || 'Something went wrong while processing your query.',
          loading: false,
          error: true,
        };
        return nextMessages;
      });
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className='grid grow gap-6 lg:grid-cols-[280px_minmax(0,1fr)]'>
      <aside className='rounded-3xl border border-white/10 bg-black/20 p-4 backdrop-blur'>
        <div className='flex items-center justify-between gap-3'>
          <div>
            <p className='font-urbanist text-xl font-semibold text-white'>History</p>
            <p className='text-sm text-gray-400'>Saved conversations</p>
          </div>
          <button
            className='rounded-full bg-[#92B3CA] px-4 py-2 text-sm font-semibold text-black transition hover:bg-[#a8c5d8]'
            onClick={startFreshConversation}
          >
            New
          </button>
        </div>

        <div className='mt-4 space-y-3'>
          {isHistoryLoading ? (
            <p className='text-sm text-gray-400'>Loading history...</p>
          ) : historyItems.length === 0 ? (
            <p className='text-sm text-gray-400'>No conversations yet.</p>
          ) : (
            historyItems.map(item => (
              <div
                key={item.user_id}
                className={`rounded-2xl border p-3 transition ${
                  item.user_id === userId
                    ? 'border-[#92B3CA] bg-white/10'
                    : 'border-white/10 bg-white/5 hover:bg-white/10'
                }`}
              >
                <button className='w-full text-left' onClick={() => loadConversation(item.user_id)}>
                  <p className='truncate font-semibold text-white'>{item.title}</p>
                  <p className='mt-1 text-xs text-gray-400'>{item.message_count} messages</p>
                </button>
                <div className='mt-3 flex gap-2'>
                  <button
                    className='rounded-full border border-white/15 px-3 py-1 text-xs text-gray-200 hover:bg-white/10'
                    onClick={() => renameConversation(item.user_id, item.title)}
                  >
                    Rename
                  </button>
                  <button
                    className='rounded-full border border-red-400/30 px-3 py-1 text-xs text-red-200 hover:bg-red-500/10'
                    onClick={() => deleteConversation(item.user_id)}
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </aside>

      <div className='relative flex min-h-[70vh] flex-col rounded-3xl border border-white/10 bg-black/20 p-4 backdrop-blur'>
        {messages.length === 0 && (
          <div className='absolute inset-0 flex items-center justify-center pointer-events-none px-6'>
            <div className='max-w-2xl text-center'>
              <p className='font-urbanist text-5xl font-semibold tracking-tight text-white'>
                Scheme Navigator
              </p>
              <p className='mt-3 text-lg text-gray-300'>
                Ask about Karnataka agriculture schemes and reopen earlier conversations anytime.
              </p>
            </div>
          </div>
        )}
        <ChatMessages messages={messages} isLoading={isLoading} />
        <ChatInput
          newMessage={newMessage}
          isLoading={isLoading}
          setNewMessage={setNewMessage}
          submitNewMessage={submitNewMessage}
        />
      </div>
    </div>
  );
}

export default Chatbot;
