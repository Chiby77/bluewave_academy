import { useState, useRef, useEffect } from 'react';
import { View, Text, TextInput, TouchableOpacity, ScrollView, ActivityIndicator, KeyboardAvoidingView, Platform, Keyboard } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Send, Bot, User } from 'lucide-react-native';
import apiClient from '../../lib/apiClient';

type Message = {
  id: number | string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
};

export default function TutorTab() {
  const queryClient = useQueryClient();
  const [inputText, setInputText] = useState('');
  const scrollViewRef = useRef<any>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['tutor_conversation'],
    queryFn: async () => {
      const response = await apiClient.get('/tutor/conversation/');
      return response.data;
    },
  });

  const sendMessageMutation = useMutation({
    mutationFn: async (message: string) => {
      const response = await apiClient.post('/tutor/send-message/', { message });
      return response.data;
    },
    onMutate: async (newMessage) => {
      // Cancel any outgoing refetches so they don't overwrite our optimistic update
      await queryClient.cancelQueries({ queryKey: ['tutor_conversation'] });

      // Snapshot the previous value
      const previousData = queryClient.getQueryData(['tutor_conversation']) as any;

      // Optimistically update to the new value
      const optimisticMessage: Message = {
        id: Date.now().toString(),
        role: 'user',
        content: newMessage,
        timestamp: new Date().toISOString(),
      };
      
      if (previousData) {
        queryClient.setQueryData(['tutor_conversation'], {
          ...previousData,
          messages: [...previousData.messages, optimisticMessage],
        });
      }

      return { previousData };
    },
    onError: (err, newMessage, context) => {
      // Rollback on error
      if (context?.previousData) {
        queryClient.setQueryData(['tutor_conversation'], context.previousData);
      }
    },
    onSuccess: (responseData) => {
      // Update with the actual AI response
      queryClient.setQueryData(['tutor_conversation'], (oldData: any) => {
        if (!oldData) return oldData;
        // Replace optimistic message and add AI message
        const filteredMessages = oldData.messages.filter((m: any) => typeof m.id !== 'string'); // remove optimistic ones
        return {
          ...oldData,
          messages: [...filteredMessages, responseData.user_message, responseData.ai_message],
        };
      });
    },
    onSettled: () => {
      // queryClient.invalidateQueries({ queryKey: ['tutor_conversation'] });
    },
  });

  const handleSend = () => {
    const text = inputText.trim();
    if (!text) return;
    
    setInputText('');
    sendMessageMutation.mutate(text);
  };

  useEffect(() => {
    // Auto-scroll to bottom when data changes
    if (data?.messages) {
      setTimeout(() => {
        scrollViewRef.current?.scrollToEnd({ animated: true });
      }, 100);
    }
  }, [data?.messages]);

  if (isLoading) {
    return (
      <SafeAreaView className="flex-1 bg-brand-slate justify-center items-center">
        <ActivityIndicator size="large" color="#14B8A6" />
        <Text className="text-gray-400 mt-4">Connecting to AI Tutor...</Text>
      </SafeAreaView>
    );
  }

  if (isError || !data) {
    return (
      <SafeAreaView className="flex-1 bg-brand-slate justify-center items-center">
        <Text className="text-red-400">Failed to load conversation.</Text>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView className="flex-1 bg-brand-slate" edges={['top']}>
      <KeyboardAvoidingView 
        style={{ flex: 1 }} 
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        {/* Header */}
        <View className="px-4 py-3 border-b border-white/10 flex-row items-center">
          <View className="w-10 h-10 rounded-full bg-brand-teal/20 items-center justify-center mr-3">
            <Bot size={24} color="#14B8A6" />
          </View>
          <View>
            <Text className="text-white font-bold text-lg">Zuri</Text>
            <Text className="text-brand-teal text-sm">AI Tutor • Online</Text>
          </View>
        </View>

        {/* Chat Messages */}
        <ScrollView 
          ref={scrollViewRef}
          className="flex-1 px-4 py-4"
          contentContainerStyle={{ paddingBottom: 20 }}
          onContentSizeChange={() => scrollViewRef.current?.scrollToEnd({ animated: true })}
        >
          {data.messages.length === 0 && (
            <View className="items-center justify-center mt-20">
              <Bot size={48} color="#14B8A6" opacity={0.5} className="mb-4" />
              <Text className="text-gray-400 text-center px-6 leading-6">
                Hi! I'm Zuri, your AI Tutor. Feel free to ask me anything about your courses, homework, or general knowledge.
              </Text>
            </View>
          )}

          {data.messages.map((msg: Message, index: number) => {
            const isUser = msg.role === 'user';
            return (
              <View 
                key={msg.id} 
                className={`mb-4 flex-row ${isUser ? 'justify-end' : 'justify-start'}`}
              >
                {!isUser && (
                  <View className="w-8 h-8 rounded-full bg-brand-teal/20 items-center justify-center mr-2 mt-auto mb-1">
                    <Bot size={16} color="#14B8A6" />
                  </View>
                )}
                
                <View 
                  className={`max-w-[80%] rounded-2xl p-4 ${
                    isUser 
                      ? 'bg-brand-blue rounded-br-sm' 
                      : 'bg-white/10 border border-white/5 rounded-bl-sm'
                  }`}
                >
                  <Text className="text-white text-[15px] leading-6">{msg.content}</Text>
                </View>

                {isUser && (
                  <View className="w-8 h-8 rounded-full bg-brand-blue/20 items-center justify-center ml-2 mt-auto mb-1">
                    <User size={16} color="#3B82F6" />
                  </View>
                )}
              </View>
            );
          })}

          {/* Typing Indicator */}
          {sendMessageMutation.isPending && (
            <View className="mb-4 flex-row justify-start items-center">
              <View className="w-8 h-8 rounded-full bg-brand-teal/20 items-center justify-center mr-2">
                <Bot size={16} color="#14B8A6" />
              </View>
              <View className="bg-white/10 border border-white/5 rounded-2xl rounded-bl-sm p-4 w-20 flex-row justify-center space-x-1">
                <ActivityIndicator size="small" color="#14B8A6" />
              </View>
            </View>
          )}
        </ScrollView>

        {/* Input Area */}
        <View className="p-4 border-t border-white/10 bg-brand-slate">
          <View className="flex-row items-center bg-white/5 border border-white/10 rounded-full px-4 py-2">
            <TextInput
              className="flex-1 text-white text-[15px] max-h-32"
              placeholder="Ask Zuri a question..."
              placeholderTextColor="#64748B"
              multiline
              value={inputText}
              onChangeText={setInputText}
              onSubmitEditing={handleSend}
            />
            <TouchableOpacity 
              className={`w-10 h-10 rounded-full items-center justify-center ml-2 ${
                inputText.trim() ? 'bg-brand-teal' : 'bg-gray-700'
              }`}
              onPress={handleSend}
              disabled={!inputText.trim() || sendMessageMutation.isPending}
            >
              <Send size={18} color="white" style={{ marginLeft: -2 }} />
            </TouchableOpacity>
          </View>
        </View>

      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
