/**
 * Settings modal for user profile and model preferences
 */

'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface ModelConfig {
  id: string;
  name: string;
  provider: 'openai' | 'anthropic';
  description: string;
  speed: 'fast' | 'medium' | 'slow';
  cost: 'low' | 'medium' | 'high';
}

const AVAILABLE_MODELS: ModelConfig[] = [
  {
    id: 'anthropic:claude-4-5-haiku-20251022',
    name: 'Claude 4.5 Haiku',
    provider: 'anthropic',
    description: 'Fastest, best for real-time chat',
    speed: 'fast',
    cost: 'low',
  },
  {
    id: 'anthropic:claude-4-5-sonnet-20250101',
    name: 'Claude 4.5 Sonnet',
    provider: 'anthropic',
    description: 'Balanced, great for complex tasks',
    speed: 'medium',
    cost: 'medium',
  },
  {
    id: 'openai:gpt-4o-mini',
    name: 'GPT-4o Mini',
    provider: 'openai',
    description: 'Fast and affordable',
    speed: 'fast',
    cost: 'low',
  },
  {
    id: 'openai:gpt-4o',
    name: 'GPT-4o',
    provider: 'openai',
    description: 'Most capable OpenAI model',
    speed: 'medium',
    cost: 'high',
  },
];

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const [selectedModel, setSelectedModel] = useState(AVAILABLE_MODELS[0].id);
  const [userName, setUserName] = useState('');
  const [userEmail, setUserEmail] = useState('');

  useEffect(() => {
    // Load from localStorage
    const savedModel = localStorage.getItem('episteme_chat_model');
    const savedName = localStorage.getItem('episteme_user_name');
    const savedEmail = localStorage.getItem('episteme_user_email');
    
    if (savedModel) setSelectedModel(savedModel);
    if (savedName) setUserName(savedName);
    if (savedEmail) setUserEmail(savedEmail);
  }, []);

  const handleSave = () => {
    // Save to localStorage
    localStorage.setItem('episteme_chat_model', selectedModel);
    localStorage.setItem('episteme_user_name', userName);
    localStorage.setItem('episteme_user_email', userEmail);
    
    // TODO: Save to backend when we have user preferences API
    onClose();
  };

  if (!isOpen) return null;

  const selectedModelConfig = AVAILABLE_MODELS.find(m => m.id === selectedModel);

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">Settings</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Close"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-6 space-y-8">
          {/* User Profile Section */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-4">Profile</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Name
                </label>
                <input
                  type="text"
                  value={userName}
                  onChange={(e) => setUserName(e.target.value)}
                  placeholder="Your name"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email
                </label>
                <input
                  type="email"
                  value={userEmail}
                  onChange={(e) => setUserEmail(e.target.value)}
                  placeholder="your.email@example.com"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>

          {/* Model Selection Section */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Chat Model</h3>
            <p className="text-sm text-gray-600 mb-4">
              Choose the AI model for conversations. You can change this anytime.
            </p>
            
            <div className="space-y-3">
              {AVAILABLE_MODELS.map((model) => (
                <label
                  key={model.id}
                  className={`block p-4 border-2 rounded-lg cursor-pointer transition-all ${
                    selectedModel === model.id
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="flex items-start">
                    <input
                      type="radio"
                      name="model"
                      value={model.id}
                      checked={selectedModel === model.id}
                      onChange={(e) => setSelectedModel(e.target.value)}
                      className="mt-1 mr-3"
                    />
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-medium text-gray-900">{model.name}</span>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          model.provider === 'anthropic' 
                            ? 'bg-purple-100 text-purple-700'
                            : 'bg-green-100 text-green-700'
                        }`}>
                          {model.provider}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 mb-2">{model.description}</p>
                      <div className="flex gap-4 text-xs text-gray-500">
                        <span className="flex items-center gap-1">
                          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
                          </svg>
                          Speed: {model.speed}
                        </span>
                        <span className="flex items-center gap-1">
                          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M8.433 7.418c.155-.103.346-.196.567-.267v1.698a2.305 2.305 0 01-.567-.267C8.07 8.34 8 8.114 8 8c0-.114.07-.34.433-.582zM11 12.849v-1.698c.22.071.412.164.567.267.364.243.433.468.433.582 0 .114-.07.34-.433.582a2.305 2.305 0 01-.567.267z" />
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-13a1 1 0 10-2 0v.092a4.535 4.535 0 00-1.676.662C6.602 6.234 6 7.009 6 8c0 .99.602 1.765 1.324 2.246.48.32 1.054.545 1.676.662v1.941c-.391-.127-.68-.317-.843-.504a1 1 0 10-1.51 1.31c.562.649 1.413 1.076 2.353 1.253V15a1 1 0 102 0v-.092a4.535 4.535 0 001.676-.662C13.398 13.766 14 12.991 14 12c0-.99-.602-1.765-1.324-2.246A4.535 4.535 0 0011 9.092V7.151c.391.127.68.317.843.504a1 1 0 101.511-1.31c-.563-.649-1.413-1.076-2.354-1.253V5z" clipRule="evenodd" />
                          </svg>
                          Cost: {model.cost}
                        </span>
                      </div>
                    </div>
                  </div>
                </label>
              ))}
            </div>

            {selectedModelConfig && (
              <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-sm text-blue-800">
                  <span className="font-medium">Selected:</span> {selectedModelConfig.name} will be used for all new conversations.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200 bg-gray-50">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSave}>
            Save Changes
          </Button>
        </div>
      </div>
    </div>
  );
}
