import { useEffect } from 'react';
import { View, Text, ScrollView, TouchableOpacity, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useQuery } from '@tanstack/react-query';
import apiClient from '../../../lib/apiClient';

export default function ExamResultScreen() {
  const { id } = useLocalSearchParams();
  const router = useRouter();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['exam_status', id],
    queryFn: async () => {
      const response = await apiClient.get(`/exam-attempt/${id}/status/`);
      return response.data;
    },
    // Poll every 5 seconds if status is still 'submitted' (grading in progress)
    refetchInterval: (query) => {
      if (query.state.data?.status === 'submitted') {
        return 5000;
      }
      return false;
    }
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
        <Text className="text-red-400">Failed to load result.</Text>
        <TouchableOpacity onPress={() => router.back()} className="mt-4 bg-brand-blue px-4 py-2 rounded-lg">
          <Text className="text-white">Go Back</Text>
        </TouchableOpacity>
      </SafeAreaView>
    );
  }

  const isGrading = data.status === 'submitted';

  return (
    <SafeAreaView className="flex-1 bg-brand-slate" edges={['top']}>
      <ScrollView className="flex-1 px-4 py-8">
        
        {isGrading ? (
          <View className="items-center justify-center mt-12 mb-10">
            <ActivityIndicator size="large" color="#2563EB" className="mb-6" />
            <Text className="text-white text-2xl font-bold mb-2 text-center">AI is grading your exam...</Text>
            <Text className="text-gray-400 text-center px-4">
              Our AI models are carefully evaluating your answers. This usually takes less than a minute.
            </Text>
          </View>
        ) : (
          <View className="items-center justify-center mt-6 mb-8">
            <View className="w-32 h-32 rounded-full border-4 border-brand-teal items-center justify-center mb-4">
              <Text className="text-white text-4xl font-bold">{data.score}%</Text>
            </View>
            <Text className="text-white text-2xl font-bold mb-1 text-center">Exam Graded!</Text>
            <Text className="text-brand-teal text-lg font-medium capitalize">
              Status: {data.status.replace('_', ' ')}
            </Text>
          </View>
        )}

        {!isGrading && data.feedback && (
          <View className="bg-white/5 p-5 rounded-2xl border border-white/10 mb-8">
            <Text className="text-white font-bold text-lg mb-3">AI Feedback</Text>
            <Text className="text-gray-300 leading-6">{data.feedback}</Text>
          </View>
        )}

        <TouchableOpacity 
          className="bg-brand-slate border border-white/20 p-4 rounded-xl items-center mt-4"
          onPress={() => router.push('/(tabs)/dashboard')}
        >
          <Text className="text-white font-bold text-lg">Back to Dashboard</Text>
        </TouchableOpacity>

      </ScrollView>
    </SafeAreaView>
  );
}
