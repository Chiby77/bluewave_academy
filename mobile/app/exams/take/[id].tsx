import { useState, useEffect } from 'react';
import { View, Text, ScrollView, TouchableOpacity, ActivityIndicator, Alert, TextInput } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useQuery, useMutation } from '@tanstack/react-query';
import apiClient from '../../../lib/apiClient';

export default function TakeExamScreen() {
  const { id } = useLocalSearchParams();
  const router = useRouter();
  const [answers, setAnswers] = useState<Record<string, string>>({});

  const { data, isLoading, isError } = useQuery({
    queryKey: ['exam_take', id],
    queryFn: async () => {
      const response = await apiClient.get(`/exam/${id}/take/`);
      return response.data;
    },
  });

  const submitMutation = useMutation({
    mutationFn: async (payload: any) => {
      const response = await apiClient.post(`/exam/${id}/submit/`, payload);
      return response.data;
    },
    onSuccess: (resData) => {
      router.replace(`/exams/result/${resData.attempt_id}`);
    },
    onError: (error: any) => {
      Alert.alert('Submission Failed', error.response?.data?.error || 'Could not submit exam');
    },
  });

  if (isLoading) {
    return (
      <SafeAreaView className="flex-1 bg-brand-slate justify-center items-center">
        <ActivityIndicator size="large" color="#14B8A6" />
      </SafeAreaView>
    );
  }

  if (isError || !data) {
    return (
      <SafeAreaView className="flex-1 bg-brand-slate justify-center items-center">
        <Text className="text-red-400">Failed to load exam. It might be unavailable.</Text>
        <TouchableOpacity onPress={() => router.back()} className="mt-4 bg-brand-blue px-4 py-2 rounded-lg">
          <Text className="text-white">Go Back</Text>
        </TouchableOpacity>
      </SafeAreaView>
    );
  }

  const handleAnswer = (questionId: string, text: string) => {
    setAnswers((prev) => ({ ...prev, [questionId]: text }));
  };

  const handleSubmit = () => {
    Alert.alert(
      'Submit Exam?',
      'Are you sure you want to submit? You cannot change answers after submitting.',
      [
        { text: 'Cancel', style: 'cancel' },
        { 
          text: 'Submit', 
          style: 'destructive',
          onPress: () => {
            submitMutation.mutate({
              attempt_id: data.attempt_id,
              answers: answers
            });
          }
        }
      ]
    );
  };

  return (
    <SafeAreaView className="flex-1 bg-brand-slate" edges={['top']}>
      <View className="flex-row justify-between items-center p-4 border-b border-white/10">
        <Text className="text-white font-bold text-xl flex-1">{data.exam.title}</Text>
        <View className="bg-brand-blue/20 px-3 py-1 rounded-full">
          <Text className="text-brand-blue font-bold">{data.exam.duration_minutes}m</Text>
        </View>
      </View>

      <ScrollView className="flex-1 px-4 py-4">
        {data.questions.map((q: any, idx: number) => (
          <View key={q.id} className="bg-white/5 p-4 rounded-xl border border-white/10 mb-6">
            <Text className="text-white font-semibold text-lg mb-4">
              {idx + 1}. {q.text}
            </Text>

            {q.question_type === 'multiple_choice' ? (
              <View className="space-y-3">
                {q.options.map((opt: string, oIdx: number) => {
                  const isSelected = answers[q.id.toString()] === opt;
                  return (
                    <TouchableOpacity
                      key={oIdx}
                      onPress={() => handleAnswer(q.id.toString(), opt)}
                      className={`p-4 rounded-lg border flex-row items-center mt-2 ${
                        isSelected ? 'bg-brand-teal/20 border-brand-teal' : 'bg-transparent border-white/20'
                      }`}
                    >
                      <View className={`w-5 h-5 rounded-full border-2 mr-3 items-center justify-center ${
                        isSelected ? 'border-brand-teal' : 'border-gray-400'
                      }`}>
                        {isSelected && <View className="w-2.5 h-2.5 rounded-full bg-brand-teal" />}
                      </View>
                      <Text className={isSelected ? 'text-brand-teal font-medium' : 'text-gray-300'}>
                        {opt}
                      </Text>
                    </TouchableOpacity>
                  );
                })}
              </View>
            ) : (
              <TextInput
                className="bg-white/5 text-white p-4 rounded-lg border border-white/20 min-h-[120px]"
                multiline
                textAlignVertical="top"
                placeholder="Type your answer here..."
                placeholderTextColor="#6b7280"
                value={answers[q.id.toString()] || ''}
                onChangeText={(text) => handleAnswer(q.id.toString(), text)}
              />
            )}
          </View>
        ))}

        <TouchableOpacity 
          className="bg-brand-blue p-4 rounded-xl items-center mt-4 mb-10"
          onPress={handleSubmit}
          disabled={submitMutation.isPending}
        >
          {submitMutation.isPending ? (
            <ActivityIndicator color="white" />
          ) : (
            <Text className="text-white font-bold text-lg">Submit Exam</Text>
          )}
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}
